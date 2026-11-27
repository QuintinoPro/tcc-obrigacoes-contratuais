"""Avalia a extração por LLM no mesmo corpus e com o mesmo critério do extrator por regras.

Uso (na pasta prototipo/):
    .venv/bin/python -m scripts.avaliar_llm --repeticoes 3 [--modelo claude-sonnet-5-5]

O modelo é chamado pelo Claude Code CLI em modo não interativo, com o prompt de sistema
do extrator (app/extractor.py, LLM_PROMPT) no lugar do prompt padrão, sem ferramentas,
sem servidores MCP, sem configurações do usuário e sem persistir a sessão. Cada resposta
bruta fica gravada em docs/llm-runs/ com modelo, data, versão do CLI e hash do prompt,
para que o experimento possa ser repetido e auditado.
"""
import argparse
import hashlib
import io
import json
import os
import statistics
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

from pypdf import PdfReader

from app.extractor import LLM_PROMPT, normalize
from samples.corpus import CORPUS, HOLDOUT
from samples.gerar_contrato_exemplo import gerar
from scripts.avaliar_extracao import OUT_DOC, OUT_PDF, avaliar

CLAUDE = os.getenv("CLAUDE_BIN", "claude")  # caminho do Claude Code CLI
RUNS = OUT_DOC / "llm-runs"


def texto_pdf(item):
    pdf = OUT_PDF / f"{item['id']}.pdf"
    if not pdf.exists():
        OUT_PDF.mkdir(parents=True, exist_ok=True)
        gerar(pdf, item["texto"])
    return "\n".join(p.extract_text() for p in PdfReader(io.BytesIO(pdf.read_bytes())).pages)


def chamar(texto: str, modelo: str) -> dict:
    cmd = [CLAUDE, "-p", "--model", modelo, "--system-prompt", LLM_PROMPT, "--tools", "",
           "--strict-mcp-config", "--setting-sources", "", "--no-session-persistence", "--output-format", "json"]
    t0 = time.time()
    r = subprocess.run(cmd, input="CONTRATO:\n" + texto, capture_output=True, text=True, timeout=600)
    if r.returncode != 0:
        raise RuntimeError(r.stderr[-500:] or r.stdout[-500:])
    out = json.loads(r.stdout)
    out["_segundos"] = round(time.time() - t0, 1)
    return out


def rodar(item, k, modelo, versao):
    destino = RUNS / modelo / f"{item['id']}-r{k}.json"
    if destino.exists():
        return json.loads(destino.read_text())
    texto = texto_pdf(item)
    bruto = chamar(texto, modelo)
    resposta = bruto.get("result", "")
    try:
        dados = json.loads(resposta[resposta.find("{"): resposta.rfind("}") + 1])
        erro = None
    except ValueError as e:
        dados, erro = {"obrigacoes": []}, f"JSON inválido: {e}"
    registro = {
        "contrato": item["id"], "repeticao": k, "modelo_solicitado": modelo,
        "modelos_usados": list((bruto.get("modelUsage") or {}).keys()),
        "data_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "cli": versao, "prompt_sha256": hashlib.sha256(LLM_PROMPT.encode()).hexdigest(),
        "segundos": bruto["_segundos"], "custo_informado_usd": bruto.get("total_cost_usd"),
        "uso": bruto.get("usage"), "erro_parse": erro, "resposta_bruta": resposta,
        "extracao": normalize({**dados, "provedor": "llm:" + modelo}),
    }
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(json.dumps(registro, ensure_ascii=False, indent=2))
    return registro


def resumo_conjunto(regs_por_rep):
    """regs_por_rep: lista (uma por repetição) de listas de resultados por contrato."""
    linhas = []
    for res in regs_por_rep:
        tot = {k: sum(r[k] for r in res) for k in ("gabarito", "detectadas", "falsos_positivos", "responsavel_ok", "prazo_ok")}
        den = tot["detectadas"] + tot["falsos_positivos"]
        linhas.append({
            "revocacao": tot["detectadas"] / tot["gabarito"],
            "precisao": tot["detectadas"] / den if den else 0,
            "responsavel": tot["responsavel_ok"] / tot["detectadas"] if tot["detectadas"] else 0,
            "prazo": tot["prazo_ok"] / tot["detectadas"] if tot["detectadas"] else 0,
            **tot,
        })
    return linhas


def fmt(vals):
    m = statistics.mean(vals)
    return f"{100 * m:.0f}% ({100 * min(vals):.0f}–{100 * max(vals):.0f}%)" if len(vals) > 1 else f"{100 * m:.0f}%"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repeticoes", type=int, default=3)
    ap.add_argument("--modelo", default="claude-sonnet-5-5")
    ap.add_argument("--paralelo", type=int, default=4)
    a = ap.parse_args()
    versao = subprocess.run([CLAUDE, "--version"], capture_output=True, text=True).stdout.strip()
    conjuntos = {"desenvolvimento": CORPUS, "validação": HOLDOUT}
    jobs = [(item, k) for conj in conjuntos.values() for item in conj for k in range(1, a.repeticoes + 1)]
    with ThreadPoolExecutor(a.paralelo) as ex:
        regs = list(ex.map(lambda j: rodar(j[0], j[1], a.modelo, versao), jobs))
    idx = {(r["contrato"], r["repeticao"]): r for r in regs}

    md = [f"# Avaliação da extração por LLM\n",
          f"- Modelo solicitado: `{a.modelo}`; modelos registrados nas respostas: "
          f"{sorted({m for r in regs for m in r['modelos_usados']})}",
          f"- Acesso: {versao}, modo não interativo, prompt de sistema próprio, sem ferramentas",
          f"- Datas (UTC): {min(r['data_utc'] for r in regs)} a {max(r['data_utc'] for r in regs)}",
          f"- Repetições por contrato: {a.repeticoes}; hash do prompt: `{regs[0]['prompt_sha256'][:16]}…`",
          f"- Respostas com JSON inválido: {sum(1 for r in regs if r['erro_parse'])} de {len(regs)}",
          f"- Tempo por contrato (mediana): {statistics.median(r['segundos'] for r in regs):.1f} s\n",
          "| Conjunto | Obrigações | Revocação | Precisão | Responsável | Prazo |", "|---|---|---|---|---|---|"]
    dump, detalhes = {}, []
    for nome, conj in conjuntos.items():
        por_rep = []
        for k in range(1, a.repeticoes + 1):
            res = []
            for item in conj:
                ext = idx[(item["id"], k)]["extracao"]
                r = avaliar(item, lambda _t, e=ext: e)
                r["repeticao"] = k
                res.append(r)
                detalhes += [f"- {nome} · r{k} · {r['id']}: {e}" for e in r["erros"]]
            por_rep.append(res)
        lin = resumo_conjunto(por_rep)
        dump[nome] = {"repeticoes": lin, "contratos": por_rep}
        md.append(f"| {nome} | {lin[0]['gabarito']} | {fmt([l['revocacao'] for l in lin])} | {fmt([l['precisao'] for l in lin])} | "
                  f"{fmt([l['responsavel'] for l in lin])} | {fmt([l['prazo'] for l in lin])} |")
    md.append("\nValores: média das repetições (mínimo–máximo).\n\nErros por repetição:\n")
    md += detalhes or ["- nenhum"]
    (OUT_DOC / "resultados-llm.md").write_text("\n".join(md) + "\n")
    (OUT_DOC / "resultados-llm.json").write_text(json.dumps(dump, ensure_ascii=False, indent=2))
    print("\n".join(md))


if __name__ == "__main__":
    main()
