"""Avalia o extrator no corpus fictício e grava a tabela de resultados.

Uso: .venv/bin/python -m scripts.avaliar_extracao   (na pasta prototipo/)

Métricas por contrato:
- detecção: obrigações do gabarito encontradas (recall) e extraídas que não existem no gabarito (precisão);
- responsável e prazo: acerto sobre as obrigações detectadas.
Uma obrigação extraída "casa" com o gabarito quando a chave aparece na descrição extraída.
Se uma única extração contém várias chaves (cláusula com alíneas), ela casa só com a primeira.
"""
import io
import json
from pathlib import Path

from pypdf import PdfReader

from app import extractor, extractor_v1
from samples.corpus import ADVERSARIAL, CORPUS, HOLDOUT
from samples.gerar_contrato_exemplo import gerar

ROOT = Path(__file__).resolve().parent.parent
OUT_PDF = ROOT / "samples" / "corpus"
OUT_DOC = ROOT.parent / "docs"


VERSOES = {"v1": lambda t: extractor.normalize(extractor_v1.extract_rules(t)),
           "v2": lambda t: extractor.normalize(extractor.extract_rules(t))}


def avaliar(item: dict, extract) -> dict:
    OUT_PDF.mkdir(parents=True, exist_ok=True)
    pdf = OUT_PDF / f"{item['id']}.pdf"
    gerar(pdf, item["texto"])
    texto = "\n".join(p.extract_text() for p in PdfReader(io.BytesIO(pdf.read_bytes())).pages)
    sug = extract(texto)
    extraidas = sug["obrigacoes"]
    usadas, detectadas, resp_ok, prazo_ok, erros = set(), 0, 0, 0, []
    for g in item["gabarito"]:
        idx = next((i for i, o in enumerate(extraidas) if i not in usadas and g["chave"].lower() in o["descricao"].lower()), None)
        if idx is None:
            erros.append(f"não detectada: {g['chave']}")
            continue
        usadas.add(idx)
        detectadas += 1
        o = extraidas[idx]
        if o["responsavel"] == g["responsavel"]:
            resp_ok += 1
        else:
            erros.append(f"responsável errado em '{g['chave']}': {o['responsavel'] or '—'}")
        if o["prazo"] == g["prazo"]:
            prazo_ok += 1
        else:
            erros.append(f"prazo errado em '{g['chave']}': {o['prazo']} (esperado {g['prazo']})")
    total = len(item["gabarito"])
    falsos = len(extraidas) - len(usadas)
    return {
        "id": item["id"], "estilo": item["estilo"], "gabarito": total, "extraidas": len(extraidas),
        "detectadas": detectadas, "falsos_positivos": falsos, "responsavel_ok": resp_ok, "prazo_ok": prazo_ok,
        "provedor": sug["provedor"], "erros": erros,
    }


def pct(a, b):
    return f"{100 * a / b:.0f}%" if b else "—"


def tabela(res: list[dict]) -> tuple[str, dict]:
    tot = {k: sum(r[k] for r in res) for k in ("gabarito", "extraidas", "detectadas", "falsos_positivos", "responsavel_ok", "prazo_ok")}
    linhas = ["| Contrato | Estilo de redação | Recall | Precisão | Responsável | Prazo |", "|---|---|---|---|---|---|"]
    for r in res:
        den = r["detectadas"] + r["falsos_positivos"]
        linhas.append(f"| {r['id']} | {r['estilo']} | {r['detectadas']}/{r['gabarito']} | {pct(r['detectadas'], den)} | "
                      f"{r['responsavel_ok']}/{r['detectadas']} | {r['prazo_ok']}/{r['detectadas']} |")
    den = tot["detectadas"] + tot["falsos_positivos"]
    linhas.append(f"| **Total** | | **{tot['detectadas']}/{tot['gabarito']} ({pct(tot['detectadas'], tot['gabarito'])})** | "
                  f"**{pct(tot['detectadas'], den)}** | **{tot['responsavel_ok']}/{tot['detectadas']} ({pct(tot['responsavel_ok'], tot['detectadas'])})** | "
                  f"**{tot['prazo_ok']}/{tot['detectadas']} ({pct(tot['prazo_ok'], tot['detectadas'])})** |")
    return "\n".join(linhas), tot


def main():
    OUT_PDF.mkdir(exist_ok=True)
    conjuntos = {"desenvolvimento": CORPUS, "validação": HOLDOUT, "robustez (injeção)": ADVERSARIAL}
    md, dump, resumo = [], {}, ["| Versão | Conjunto | Obrigações | Recall | Precisão | Responsável | Prazo |", "|---|---|---|---|---|---|---|"]
    for nome_c, conj in conjuntos.items():
        for v, fn in VERSOES.items():
            res = [avaliar(i, fn) for i in conj]
            tab, tot = tabela(res)
            den = tot["detectadas"] + tot["falsos_positivos"]
            resumo.append(f"| {v} | {nome_c} | {tot['gabarito']} | {pct(tot['detectadas'], tot['gabarito'])} | {pct(tot['detectadas'], den)} | "
                          f"{pct(tot['responsavel_ok'], tot['detectadas'])} | {pct(tot['prazo_ok'], tot['detectadas'])} |")
            erros = [f"- {r['id']}: {e}" for r in res for e in r["erros"]] or ["- nenhum"]
            md.append(f"## Extrator {v} — conjunto de {nome_c}\n\n{tab}\n\nErros:\n\n" + "\n".join(erros))
            dump[f"{v}-{nome_c}"] = {"total": tot, "contratos": res}
    out = "# Avaliação da extração por regras\n\n## Resumo\n\n" + "\n".join(resumo) + "\n\n" + "\n\n".join(md) + "\n"
    OUT_DOC.mkdir(exist_ok=True)
    (OUT_DOC / "resultados-extracao.md").write_text(out)
    (OUT_DOC / "resultados-extracao.json").write_text(json.dumps(dump, ensure_ascii=False, indent=2))
    print(out)


if __name__ == "__main__":
    main()
