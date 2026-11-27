"""Extrator por regras, VERSÃO 1 (mantida apenas para a comparação v1 × v2 da monografia).

A versão em uso é app/extractor.py. Este módulo contém só as regras da v1; a normalização
da saída é a mesma do módulo atual.
"""
from __future__ import annotations

import re
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


from app.extractor import normalize  # noqa: E402  (mesma normalização da versão atual)
