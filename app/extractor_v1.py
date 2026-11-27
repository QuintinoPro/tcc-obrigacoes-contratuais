"""Extração de obrigações contratuais.

Dois provedores atrás da mesma interface (RNF06):
- "llm": usa a API da Anthropic quando ANTHROPIC_API_KEY está definida;
- "regras": extrator determinístico por padrões textuais, usado como fallback
  e como linha de base para comparação nos testes.

A saída é sempre uma SUGESTÃO, que precisa de revisão humana (RNF02).
"""
from __future__ import annotations

import json
import os
import re
import urllib.request
from datetime import date, timedelta

PARTY = r"(CONTRATANTE|CONTRATADA)"
OBLIG_VERB = re.compile(
    r"\b(dever[áa]|obriga-se a|compromete-se a|ficar[áa] respons[áa]vel por|se responsabiliza por)\b",
    re.IGNORECASE,
)
DATE_RE = re.compile(r"\b(\d{1,2})/(\d{1,2})/(\d{4})\b")
RELATIVE_RE = re.compile(r"em at[ée] (\d+) \(?[a-z ]*\)? ?dias[^.]{0,40}assinatura", re.IGNORECASE)
ITEM_SPLIT = re.compile(r"(?:^|\s)(\d{1,2}\.\d{1,2})\s+(?=[A-ZÀ-Ú])")
EVIDENCE_RE = re.compile(r"(?:mediante|comprovad[ao] (?:por meio de|por|atrav[ée]s de)|com envio de)\s+([^.;]+)", re.IGNORECASE)


def _iso(d: str, m: str, y: str) -> str | None:
    try:
        return date(int(y), int(m), int(d)).isoformat()
    except ValueError:
        return None


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _find_party(text: str, label: str) -> str:
    m = re.search(rf"{label}\s*:\s*([^,;\n]+?)(?:,| inscrita| CNPJ|\n|$)", text, re.IGNORECASE)
    return _clean(m.group(1)) if m else ""


def _signature_date(text: str) -> date | None:
    m = re.search(r"(?:assinad[oa]|firmad[oa]|data de assinatura)[^0-9]{0,40}(\d{1,2})/(\d{1,2})/(\d{4})", text, re.IGNORECASE)
    if not m:
        return None
    iso = _iso(*m.groups())
    return date.fromisoformat(iso) if iso else None


def extract_rules(text: str) -> dict:
    flat = _clean(text)
    signed = _signature_date(flat)
    parts = ITEM_SPLIT.split(flat)
    # parts = [preâmbulo, num, corpo, num, corpo, ...]
    items = [(parts[i], parts[i + 1]) for i in range(1, len(parts) - 1, 2)]
    if not items:
        items = [(str(i + 1), s) for i, s in enumerate(re.split(r"(?<=\.)\s+", flat))]

    obligations = []
    for clause, body in items:
        body = re.split(r"\s+CL[ÁA]USULA\s+\d+", body)[0]
        verb = OBLIG_VERB.search(body)
        if not verb:
            continue
        before = body[: verb.start()]
        resp = re.findall(PARTY, before, re.IGNORECASE)
        responsavel = resp[-1].upper() if resp else ""

        prazo = None
        dm = DATE_RE.search(body)
        if dm:
            prazo = _iso(*dm.groups())
        elif signed and (rm := RELATIVE_RE.search(body)):
            prazo = (signed + timedelta(days=int(rm.group(1)))).isoformat()

        after = body[verb.end():]
        entregavel = re.split(r", | at[ée] | em at[ée] | no prazo| mediante| conforme|\.(?:\s|$)", after, maxsplit=1)[0]
        ev = EVIDENCE_RE.search(body)

        score = 0.4 + 0.3 * bool(responsavel) + 0.3 * bool(prazo)
        obligations.append(
            {
                "clausula": clause,
                "descricao": body.rstrip(". ").strip() + ".",
                "responsavel": responsavel,
                "entregavel": _clean(entregavel)[:160],
                "prazo": prazo,
                "evidencia_esperada": _clean(ev.group(1)) if ev else "",
                "confianca": round(score, 2),
            }
        )

    return {
        "provedor": "regras",
        "contratante": _find_party(flat, "CONTRATANTE"),
        "contratada": _find_party(flat, "CONTRATADA"),
        "data_assinatura": signed.isoformat() if signed else None,
        "obrigacoes": obligations,
    }


LLM_PROMPT = """Você extrai obrigações de contratos de prestação de serviços.
Responda APENAS com um JSON válido, sem texto antes ou depois, no formato:
{"contratante": str, "contratada": str, "data_assinatura": "AAAA-MM-DD"|null,
 "obrigacoes": [{"clausula": str, "descricao": str, "responsavel": "CONTRATANTE"|"CONTRATADA",
   "entregavel": str, "prazo": "AAAA-MM-DD"|null, "evidencia_esperada": str, "confianca": número 0-1}]}
Regras: prazos relativos ("em até N dias") devem ser convertidos a partir da data de assinatura.
Não invente informações ausentes; use "" ou null.

CONTRATO:
"""


def extract_llm(text: str) -> dict:
    body = json.dumps(
        {
            "model": os.getenv("LLM_MODEL", "claude-sonnet-5-5"),
            "max_tokens": 4000,
            "messages": [{"role": "user", "content": LLM_PROMPT + text[:60000]}],
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
