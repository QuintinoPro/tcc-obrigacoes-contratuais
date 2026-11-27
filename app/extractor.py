"""Extração de obrigações contratuais.

Dois provedores atrás da mesma interface (RNF06):
- "llm": usa a API da Anthropic quando ANTHROPIC_API_KEY está definida;
- "regras-v2": extrator determinístico por padrões textuais, usado como fallback
  e como linha de base para comparação com o LLM. A versão 1 está em extractor_v1.py
  e é mantida para a comparação descrita na monografia.

A saída é sempre uma SUGESTÃO, que precisa de revisão humana (RNF02).
"""
from __future__ import annotations

import json
import os
import re
import urllib.request
from datetime import date, timedelta

CANON = ("CONTRATANTE", "CONTRATADA")
OBLIG_VERB = re.compile(
    r"\b(dever[áa]o?|obriga-se a|se obriga a|compromete-se a|se compromete a|fica obrigad[ao] a|"
    r"ficar[áa] respons[áa]vel por|se responsabiliza por|caber[áa] (?:à|ao)|compete (?:à|ao)|cabe (?:à|ao)|"
    r"ser[áa]o? (?:entregue|realizad|enviad|apresentad|fornecid|executad|pag)\w* pel[ao]s?)",
    re.IGNORECASE,
)
DATE_RE = re.compile(r"\b(\d{1,2})/(\d{1,2})/(\d{4})\b")
MESES = {m: i for i, m in enumerate(["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto",
                                     "setembro", "outubro", "novembro", "dezembro"], 1)}
DATE_EXT_RE = re.compile(r"\b(\d{1,2})º? de (" + "|".join(MESES) + r") de (\d{4})\b", re.IGNORECASE)
RELATIVE_RE = re.compile(
    r"(?:em at[ée]|no prazo de|dentro de) (\d+) \(?[a-zà-ú ]*\)? ?dias(?: corridos)?[^.;]{0,40}(?:assinatura|celebra[çc][ãa]o)",
    re.IGNORECASE)
ITEM_SPLIT = re.compile(r"(?:^|\s)(\d{1,2}\.\d{1,2})\s+(?=[A-ZÀ-Ú])")
ALINEA_SPLIT = re.compile(r"(?:^|[\s;:])([a-z])\)\s+")
SENT_SPLIT = re.compile(r"(?<=\.)\s+(?=(?:A|O|As|Os)\s+[A-ZÀ-Ú]{4,})")
CAPUT_RE = re.compile(r"obriga[çc][õo]es d[ao]s? (\w+)\s*:", re.IGNORECASE)
EVIDENCE_RE = re.compile(r"(?:mediante|comprovad[ao] (?:por meio de|por|atrav[ée]s de)|com envio de)\s+([^.;]+)", re.IGNORECASE)


def _iso(d: str, m: str, y: str) -> str | None:
    try:
        return date(int(y), int(m), int(d)).isoformat()
    except ValueError:
        return None


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _aliases(text: str) -> dict[str, str]:
    """Mapa de apelidos das partes: 'PRESTADORA: ..., doravante denominada CONTRATADA' → PRESTADORA→CONTRATADA."""
    amap = {c: c for c in CANON}
    for label, canon in re.findall(r"\b([A-ZÀ-Ú]{4,})\s*:[^:]{0,200}?doravante denominad[ao] (?:simplesmente )?(CONTRATANTE|CONTRATADA)", text):
        amap[label] = canon
    for label, canon in re.findall(r"(CONTRATANTE|CONTRATADA)\s*:[^:]{0,120}?doravante denominad[ao] (?:simplesmente )?([A-ZÀ-Ú]{4,})", text):
        amap[canon] = label
    return amap


def _find_party(text: str, canon: str, amap: dict[str, str]) -> str:
    for label in [canon] + [a for a, c in amap.items() if c == canon and a != canon]:
        m = re.search(rf"\b{label}\s*:\s*([^,;\n]+?)(?:,| inscrita| CNPJ|\n|$)", text)
        if m:
            return _clean(m.group(1))
    return ""


def _signature_date(text: str) -> date | None:
    m = re.search(r"(?:assinad[oa]|firmad[oa]|celebrad[oa]|data de assinatura)[^0-9]{0,40}(\d{1,2})/(\d{1,2})/(\d{4})", text, re.IGNORECASE)
    iso = _iso(*m.groups()) if m else None
    return date.fromisoformat(iso) if iso else None


def _deadline(body: str, signed: date | None) -> str | None:
    if dm := DATE_RE.search(body):
        return _iso(*dm.groups())
    if em := DATE_EXT_RE.search(body):
        return _iso(em.group(1), str(MESES[em.group(2).lower()]), em.group(3))
    if signed and (rm := RELATIVE_RE.search(body)):
        return (signed + timedelta(days=int(rm.group(1)))).isoformat()
    return None


def _segments(flat: str):
    """Gera (cláusula, texto, responsável herdado). Divide itens numerados, alíneas e frases."""
    parts = ITEM_SPLIT.split(flat)
    items = [(parts[i], parts[i + 1]) for i in range(1, len(parts) - 1, 2)]
    if not items:
        items = [(str(i + 1), s) for i, s in enumerate(re.split(r"(?<=\.)\s+", flat))]
    for clause, body in items:
        body = re.split(r"\s+CL[ÁA]USULA\s+\d+", body)[0]
        caput = CAPUT_RE.search(body)
        alineas = ALINEA_SPLIT.split(body)
        if caput and len(alineas) > 2:
            inherited = caput.group(1).upper()
            for j in range(1, len(alineas) - 1, 2):
                yield f"{clause}.{alineas[j]}", alineas[j + 1].strip(" ;."), inherited
            continue
        sentences = SENT_SPLIT.split(body)
        if len(sentences) == 1:
            yield clause, body, None
        else:
            for k, s in enumerate(sentences, 1):
                yield f"{clause} ({k})", s, None


def extract_rules(text: str) -> dict:
    flat = _clean(text)
    signed = _signature_date(flat)
    amap = _aliases(flat)
    party_re = re.compile(r"\b(" + "|".join(sorted(amap, key=len, reverse=True)) + r")\b")

    obligations = []
    for clause, body, inherited in _segments(flat):
        verb = OBLIG_VERB.search(body)
        if not verb and not inherited:
            continue
        if verb:
            before = party_re.findall(body[: verb.end()] if verb.group(0).lower().startswith(("cab", "comp", "ser")) else body[: verb.start()])
            after = party_re.findall(body[verb.end():verb.end() + 40])
            if verb.group(0).lower().startswith(("cab", "comp", "ser")):
                found = after[:1] or before[-1:]
            else:
                found = before[-1:] or after[:1]
        else:
            found = []
        responsavel = amap.get(found[0], "") if found else amap.get(inherited or "", "")

        prazo = _deadline(body, signed)
        passive = bool(verb) and verb.group(0).lower().startswith("ser")
        rest = body[verb.end():] if verb and not passive else (body[: verb.start()] if passive else body)
        rest = party_re.sub("", rest, count=1) if verb and verb.group(0).lower().startswith(("cab", "comp")) else rest
        entregavel = re.split(r", | at[ée] | em at[ée] | no prazo| mediante| conforme|\.(?:\s|$)", rest, maxsplit=1)[0]
        ev = EVIDENCE_RE.search(body)

        score = 0.4 + 0.3 * bool(responsavel) + 0.3 * bool(prazo)
        obligations.append({
            "clausula": clause,
            "descricao": body.rstrip(". ").strip() + ".",
            "responsavel": responsavel,
            "entregavel": _clean(entregavel)[:160],
            "prazo": prazo,
            "evidencia_esperada": _clean(ev.group(1)) if ev else "",
            "confianca": round(score, 2),
        })

    return {
        "provedor": "regras-v2",
        "contratante": _find_party(flat, "CONTRATANTE", amap),
        "contratada": _find_party(flat, "CONTRATADA", amap),
        "data_assinatura": signed.isoformat() if signed else None,
        "obrigacoes": obligations,
    }


LLM_PROMPT = """Você extrai obrigações de contratos de prestação de serviços entre duas empresas.
Responda APENAS com um JSON válido, sem texto antes ou depois, no formato:
{"contratante": str, "contratada": str, "data_assinatura": "AAAA-MM-DD"|null,
 "obrigacoes": [{"clausula": str, "descricao": str, "responsavel": "CONTRATANTE"|"CONTRATADA",
   "entregavel": str, "prazo": "AAAA-MM-DD"|null, "evidencia_esperada": str, "confianca": número 0-1}]}
Regras:
1. Uma obrigação é um compromisso de uma das partes de fazer, entregar, fornecer ou pagar algo.
   Não inclua cláusulas de objeto, valor, foro, propriedade intelectual ou rescisão que não criem dever para uma parte.
2. Liste cada obrigação separadamente, inclusive quando várias estiverem na mesma cláusula ou em alíneas.
3. "descricao" deve transcrever literalmente o trecho do contrato que contém a obrigação.
4. "responsavel" é sempre CONTRATANTE ou CONTRATADA, mesmo que o contrato use outros nomes para as partes.
5. "prazo" é a data limite no formato AAAA-MM-DD. Converta prazos relativos à assinatura a partir da data
   de assinatura. Use null quando o prazo depender de um evento futuro ou não estiver definido.
6. Não invente informações ausentes; use "" ou null.
"""


def extract_llm(text: str) -> dict:
    body = json.dumps(
        {
            "model": os.getenv("LLM_MODEL", "claude-sonnet-5-5"),
            "max_tokens": 4000,
            "system": LLM_PROMPT,
            "messages": [{"role": "user", "content": "CONTRATO:\n" + text[:60000]}],
        }
    ).encode()
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=body,
        headers={
            "x-api-key": os.environ["ANTHROPIC_API_KEY"],
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=120) as r:
        out = json.load(r)
    raw = "".join(b.get("text", "") for b in out["content"])
    data = json.loads(raw[raw.find("{"): raw.rfind("}") + 1])
    data["provedor"] = "llm:" + out.get("model", "")
    return data


def _str(v, n: int) -> str:
    return str(v)[:n] if v is not None else ""


def _date_or_none(v) -> str | None:
    try:
        return date.fromisoformat(str(v)).isoformat() if v else None
    except ValueError:
        return None


def normalize(data: dict) -> dict:
    """A saída do LLM é entrada não confiável (OWASP LLM05): força o schema esperado."""
    obs = data.get("obrigacoes") if isinstance(data.get("obrigacoes"), list) else []
    clean = []
    for o in obs[:100]:
        if not isinstance(o, dict):
            continue
        resp = _str(o.get("responsavel"), 20).upper()
        try:
            conf = min(max(float(o.get("confianca", 0.5)), 0.0), 1.0)
        except (TypeError, ValueError):
            conf = 0.5
        clean.append({
            "clausula": _str(o.get("clausula"), 20),
            "descricao": _str(o.get("descricao"), 2000),
            "responsavel": resp if resp in ("CONTRATANTE", "CONTRATADA") else "",
            "entregavel": _str(o.get("entregavel"), 300),
            "prazo": _date_or_none(o.get("prazo")),
            "evidencia_esperada": _str(o.get("evidencia_esperada"), 300),
            "confianca": round(conf, 2),
        })
    return {
        "provedor": _str(data.get("provedor"), 80),
        "contratante": _str(data.get("contratante"), 200),
        "contratada": _str(data.get("contratada"), 200),
        "data_assinatura": _date_or_none(data.get("data_assinatura")),
        "obrigacoes": clean,
        **({"aviso": _str(data["aviso"], 300)} if data.get("aviso") else {}),
    }


def extract(text: str) -> dict:
    return normalize(_extract(text))


def _extract(text: str) -> dict:
    if os.getenv("ANTHROPIC_API_KEY"):
        try:
            return extract_llm(text)
        except Exception as e:  # falha de rede/parse → fallback documentado
            res = extract_rules(text)
            res["aviso"] = f"LLM indisponível ({type(e).__name__}); usado extrator por regras."
            return res
    return extract_rules(text)
