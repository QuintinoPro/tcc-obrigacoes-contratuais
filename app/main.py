"""API do protótipo: contratos, extração, revisão humana, obrigações, evidências e auditoria."""
from __future__ import annotations

import hashlib
import io
import json
import logging
import os
import shutil
import sqlite3
import threading
from contextlib import contextmanager
from datetime import date, datetime
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator
from pypdf import PdfReader

from .chain import STATUSES, Chain
from .extractor import extract

ROOT = Path(__file__).resolve().parent.parent
DATA = Path(os.getenv("DATA_DIR", ROOT / "data"))
SAMPLE = ROOT / "samples" / "contrato-exemplo.pdf"

MAX_UPLOAD = int(os.getenv("MAX_UPLOAD_MB", "10")) * 1024 * 1024
MAX_CONTRATOS = int(os.getenv("MAX_CONTRATOS", "200"))
MAX_PAGINAS = 60

# Quem pode disparar cada transição: o responsável executa, a outra parte aprova.
EXECUTOR_MOVES = {("PENDENTE", "EM_EXECUCAO"), ("EM_EXECUCAO", "ENTREGUE"), ("REJEITADO", "EM_EXECUCAO")}
APPROVER_MOVES = {("ENTREGUE", "EM_ANALISE"), ("EM_ANALISE", "APROVADO"), ("EM_ANALISE", "REJEITADO"), ("APROVADO", "CONCLUIDO")}
PARTIES = ("CONTRATANTE", "CONTRATADA")
Party = Literal["CONTRATANTE", "CONTRATADA"]

# Campos da obrigação cobertos pelo dataHash registrado on-chain.
HASHED_FIELDS = ("clausula", "descricao", "responsavel", "entregavel", "prazo", "evidencia_esperada")

SCHEMA = """
CREATE TABLE contracts (
  id INTEGER PRIMARY KEY, titulo TEXT, arquivo TEXT, sha256 TEXT, contratante TEXT, contratada TEXT,
  status TEXT, extracao_json TEXT, criado_em TEXT, tx TEXT);
CREATE TABLE obligations (
  id INTEGER PRIMARY KEY, contract_id INTEGER, clausula TEXT, descricao TEXT, responsavel TEXT,
  entregavel TEXT, prazo TEXT, evidencia_esperada TEXT, status TEXT, confianca REAL,
  editada INTEGER, data_sha256 TEXT, validada_por TEXT, validada_em TEXT);
CREATE TABLE evidences (
  id INTEGER PRIMARY KEY, obligation_id INTEGER, arquivo TEXT, nome_original TEXT, sha256 TEXT,
  enviado_por TEXT, enviado_em TEXT);
CREATE TABLE audit_events (
  id INTEGER PRIMARY KEY, entidade TEXT, entidade_id INTEGER, contract_id INTEGER, tipo TEXT,
  usuario TEXT, papel TEXT, timestamp TEXT, estado_anterior TEXT, estado_posterior TEXT,
  hash_relacionado TEXT, observacao TEXT, tx TEXT, bloco INTEGER);
"""


class ObrigacaoRevisada(BaseModel):
    clausula: str = Field("", max_length=20)
    descricao: str = Field(..., min_length=1, max_length=2000)
    responsavel: Party
    entregavel: str = Field("", max_length=300)
    prazo: date | None = None
    evidencia_esperada: str = Field("", max_length=300)
    confianca: float | None = Field(None, ge=0, le=1)
    editada: bool = False

    @field_validator("prazo", mode="before")
    @classmethod
    def vazio_vira_none(cls, v):
        return v or None


class Revisao(BaseModel):
    usuario: str = Field(..., min_length=1, max_length=60)
    contratante: str = Field(..., max_length=200)
    contratada: str = Field(..., max_length=200)
    obrigacoes: list[ObrigacaoRevisada] = Field(..., min_length=1, max_length=100)


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def obligation_data_hash(fields: dict) -> str:
    """Hash canônico dos dados validados de uma obrigação (o mesmo que vai on-chain)."""
    payload = {k: (str(fields[k]) if fields.get(k) is not None else None) for k in HASHED_FIELDS}
    return sha256_bytes(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode())


def now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def read_upload(up: UploadFile) -> bytes:
    content = up.file.read(MAX_UPLOAD + 1)
    if len(content) > MAX_UPLOAD:
        raise HTTPException(413, f"Arquivo maior que {MAX_UPLOAD // 1024 // 1024} MB")
    if not content:
        raise HTTPException(400, "Arquivo vazio")
    return content


def clip(s: str | None, n: int) -> str:
    return (s or "")[:n]


def create_app(data_dir: Path | None = None) -> FastAPI:
    data = Path(data_dir) if data_dir else DATA
    files = data / "arquivos"
    # Com a chain em memória o estado on-chain some ao reiniciar; por coerência,
    # a base off-chain também recomeça. Com CHAIN_RPC_URL os dados persistem.
    if not os.getenv("CHAIN_RPC_URL") and (data / "tcc.db").exists():
        shutil.rmtree(data)
    files.mkdir(parents=True, exist_ok=True)

    db = sqlite3.connect(data / "tcc.db", check_same_thread=False)
    db.row_factory = sqlite3.Row
    if not db.execute("SELECT name FROM sqlite_master WHERE name='contracts'").fetchone():
        db.executescript(SCHEMA)
    chain = Chain()
    lock = threading.RLock()  # serializa chain (eth-tester) e SQLite entre threads

    app = FastAPI(title="Protótipo TCC — Obrigações Contratuais com IA e Blockchain")
    app.state.db, app.state.chain = db, chain

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        resp = await call_next(request)
        resp.headers.update({
            "Content-Security-Policy": "default-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; "
                                       "object-src 'none'; frame-ancestors 'self'; base-uri 'none'",
            "X-Content-Type-Options": "nosniff",
            "Referrer-Policy": "no-referrer",
            "X-Frame-Options": "SAMEORIGIN",
        })
        return resp

    @contextmanager
    def tx():
        """Uma transação por operação: tudo ou nada no SQLite."""
        with lock:
            try:
                yield
                db.commit()
            except BaseException:
                db.rollback()
                raise

    def audit(entidade, entidade_id, contract_id, tipo, usuario, papel="SISTEMA", antes=None, depois=None,
              hash_rel=None, obs=None, onchain=None):
        db.execute(
            "INSERT INTO audit_events (entidade, entidade_id, contract_id, tipo, usuario, papel, timestamp,"
            " estado_anterior, estado_posterior, hash_relacionado, observacao, tx, bloco)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (entidade, entidade_id, contract_id, tipo, usuario, papel, now(), antes, depois, hash_rel, obs,
             onchain and onchain["tx"], onchain and onchain["block"]),
        )

    def get_contract(cid: int) -> sqlite3.Row:
        row = db.execute("SELECT * FROM contracts WHERE id=?", (cid,)).fetchone()
        if not row:
            raise HTTPException(404, "Contrato não encontrado")
        return row

    def obligation_view(o: sqlite3.Row) -> dict:
        d = dict(o)
        d["atrasada"] = bool(
            d["prazo"] and d["status"] not in ("APROVADO", "CONCLUIDO") and date.fromisoformat(d["prazo"]) < date.today()
        )
        onchain = chain.obligation(d["id"])
        d["onchain_status"] = onchain and onchain["status"]
        # Detecção de adulteração off-chain: recalcula o hash dos dados e compara com o on-chain.
        d["dados_integros"] = bool(onchain) and obligation_data_hash(d) == onchain["data_sha256"]
        d["evidencias"] = [dict(e) for e in db.execute("SELECT * FROM evidences WHERE obligation_id=?", (d["id"],))]
        return d

    # --- contratos --------------------------------------------------------
    def ingest(content: bytes, nome: str, titulo: str, usuario: str) -> dict:
        if not content.startswith(b"%PDF-"):
            raise HTTPException(415, "Envie um arquivo PDF")
        try:
            reader = PdfReader(io.BytesIO(content))
            if len(reader.pages) > MAX_PAGINAS:
                raise HTTPException(413, f"PDF com mais de {MAX_PAGINAS} páginas")
            text = "\n".join(p.extract_text() or "" for p in reader.pages)
        except HTTPException:
            raise
        except Exception as e:
            logging.getLogger("tcc").warning("PDF ilegível: %s: %s", type(e).__name__, e)
            raise HTTPException(400, "Não foi possível ler o PDF. Verifique se o arquivo não está corrompido ou protegido por senha.")
        if not text.strip():
            raise HTTPException(422, "O PDF não tem texto extraível (PDF escaneado não é suportado)")
        sugestao = extract(text)
        digest = sha256_bytes(content)
        with tx():
            if db.execute("SELECT COUNT(*) FROM contracts").fetchone()[0] >= MAX_CONTRATOS:
                raise HTTPException(429, "Limite de contratos da demonstração atingido")
            (files / f"{digest}.pdf").write_bytes(content)
            onchain = chain.register_contract(digest)
            cur = db.execute(
                "INSERT INTO contracts (titulo, arquivo, sha256, contratante, contratada, status, extracao_json, criado_em, tx)"
                " VALUES (?,?,?,?,?,?,?,?,?)",
                (clip(titulo or nome, 150), clip(nome, 150), digest, sugestao.get("contratante"), sugestao.get("contratada"),
                 "EM_REVISAO", json.dumps(sugestao, ensure_ascii=False), now(), onchain and onchain["tx"]),
            )
            cid = cur.lastrowid
            audit("contrato", cid, cid, "CONTRATO_CADASTRADO", usuario, hash_rel=digest,
                  obs="Hash já registrado on-chain anteriormente" if onchain is None else None, onchain=onchain)
            audit("contrato", cid, cid, "EXTRACAO_SUGERIDA", "IA",
                  obs=f"{len(sugestao['obrigacoes'])} obrigações sugeridas ({sugestao['provedor']})")
        return {"id": cid, "sha256": digest, "sugestao": sugestao}

    @app.post("/api/contracts")
    def upload_contract(arquivo: UploadFile = File(...), titulo: str = Form("", max_length=150),
                        usuario: str = Form("operador", max_length=60)):
        return ingest(read_upload(arquivo), arquivo.filename or "contrato.pdf", titulo, usuario)

    @app.post("/api/contracts/exemplo")
    def upload_sample():
        if not SAMPLE.exists():
            from samples.gerar_contrato_exemplo import gerar
            gerar(SAMPLE)
        return ingest(SAMPLE.read_bytes(), SAMPLE.name, "Contrato 014/2026 — Marketing Digital (fictício)", "operador")

    @app.get("/api/contracts")
    def list_contracts():
        with lock:
            rows = db.execute("SELECT id, titulo, contratante, contratada, status, criado_em, sha256 FROM contracts ORDER BY id DESC")
            return [dict(r) for r in rows]

    @app.get("/api/contracts/{cid}")
    def contract_detail(cid: int):
        with lock:
            c = dict(get_contract(cid))
            c["extracao"] = json.loads(c.pop("extracao_json"))
            c["registrado_onchain_em"] = chain.contract_registered_at(c["sha256"])
            c["obrigacoes"] = [obligation_view(o) for o in db.execute("SELECT * FROM obligations WHERE contract_id=? ORDER BY id", (cid,))]
            c["eventos"] = [dict(e) for e in db.execute("SELECT * FROM audit_events WHERE contract_id=? ORDER BY id DESC", (cid,))]
            return c

    @app.get("/api/contracts/{cid}/pdf")
    def contract_pdf(cid: int):
        c = get_contract(cid)
        return FileResponse(files / f"{c['sha256']}.pdf", media_type="application/pdf")

    # --- revisão humana -----------------------------------------------------
    @app.post("/api/contracts/{cid}/confirmar")
    def confirm(cid: int, rev: Revisao):
        with tx():
            c = get_contract(cid)
            if c["status"] != "EM_REVISAO":
                raise HTTPException(409, "Contrato já confirmado")
            db.execute("UPDATE contracts SET contratante=?, contratada=?, status='ATIVO' WHERE id=?",
                       (rev.contratante, rev.contratada, cid))
            for o in rev.obrigacoes:
                fields = o.model_dump()
                data_sha = obligation_data_hash(fields)
                cur = db.execute(
                    "INSERT INTO obligations (contract_id, clausula, descricao, responsavel, entregavel, prazo,"
                    " evidencia_esperada, status, confianca, editada, data_sha256, validada_por, validada_em)"
                    " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (cid, o.clausula, o.descricao, o.responsavel, o.entregavel, o.prazo and o.prazo.isoformat(),
                     o.evidencia_esperada, "PENDENTE", o.confianca, int(o.editada), data_sha, rev.usuario, now()),
                )
                oid = cur.lastrowid
                onchain = chain.create_obligation(oid, c["sha256"], data_sha)
                audit("obrigacao", oid, cid, "OBRIGACAO_CRIADA", rev.usuario, "REVISOR", None, "PENDENTE", data_sha,
                      f"Cláusula {o.clausula}" + (" (corrigida na revisão)" if o.editada else ""), onchain)
        return contract_detail(cid)

    # --- ciclo de vida da obrigação ------------------------------------------
    @app.post("/api/obligations/{oid}/transicao")
    def transition(oid: int, para: str = Form(...), usuario: str = Form(..., min_length=1, max_length=60),
                   papel: str = Form(...), observacao: str = Form("", max_length=500),
                   evidencia: UploadFile | None = File(None)):
        if para not in STATUSES or papel not in PARTIES:
            raise HTTPException(400, "Estado ou papel inválido")
        content = read_upload(evidencia) if para == "ENTREGUE" and evidencia is not None and evidencia.filename else None
        with tx():
            o = db.execute("SELECT * FROM obligations WHERE id=?", (oid,)).fetchone()
            if not o:
                raise HTTPException(404, "Obrigação não encontrada")
            move = (o["status"], para)
            if move not in EXECUTOR_MOVES | APPROVER_MOVES:
                raise HTTPException(409, f"Transição inválida: {o['status']} → {para}")
            is_executor = papel == o["responsavel"]
            if (move in EXECUTOR_MOVES and not is_executor) or (move in APPROVER_MOVES and is_executor):
                quem = "o responsável pela obrigação" if move in EXECUTOR_MOVES else "a outra parte"
                raise HTTPException(403, f"Só {quem} pode fazer {o['status']} → {para}")

            ev_sha = None
            if para == "ENTREGUE":
                if content is None:
                    raise HTTPException(400, "A entrega exige um arquivo de evidência")
                ev_sha = sha256_bytes(content)
                (files / f"{ev_sha}.bin").write_bytes(content)  # nunca servido; nome derivado do hash
                db.execute("INSERT INTO evidences (obligation_id, arquivo, nome_original, sha256, enviado_por, enviado_em)"
                           " VALUES (?,?,?,?,?,?)", (oid, f"{ev_sha}.bin", clip(evidencia.filename, 150), ev_sha, usuario, now()))

            actor_sha = sha256_bytes(f"{papel}:{usuario}".encode())
            onchain = chain.transition(oid, para, ev_sha, actor_sha)
            db.execute("UPDATE obligations SET status=? WHERE id=?", (para, oid))
            audit("obrigacao", oid, o["contract_id"], "MUDANCA_DE_ESTADO", usuario, papel, o["status"], para, ev_sha,
                  observacao or None, onchain)
            return obligation_view(db.execute("SELECT * FROM obligations WHERE id=?", (oid,)).fetchone())

    @app.get("/api/obligations/{oid}/onchain")
    def onchain_history(oid: int):
        with lock:
            ob = chain.obligation(oid)
            if not ob:
                raise HTTPException(404, "Obrigação não registrada on-chain")
            return {**ob, "eventos": chain.status_events(oid)}

    # --- integridade (consulta sempre a blockchain, não o banco) -------------
    @app.post("/api/verificar")
    def verify(arquivo: UploadFile = File(...)):
        digest = sha256_bytes(read_upload(arquivo))
        with lock:
            registered = chain.contract_registered_at(digest)
            ev = None if registered else chain.find_evidence(digest)
            c = db.execute("SELECT id, titulo FROM contracts WHERE sha256=?", (digest,)).fetchone()
        ok = bool(registered or ev)
        when = registered or (ev and ev["timestamp"])
        return {
            "sha256": digest,
            "integro": ok,
            "tipo": "contrato" if registered else ("evidência" if ev else None),
            "contrato": dict(c) if c else None,
            "obrigacao_id": ev and ev["obligation_id"],
            "tx": ev and ev["tx"],
            "registrado_em": datetime.fromtimestamp(when).isoformat() if when else None,
            "mensagem": "Hash encontrado na blockchain: arquivo idêntico ao registrado." if ok
                        else "Hash não encontrado na blockchain: o arquivo foi alterado ou nunca foi registrado.",
        }

    @app.get("/api/chain")
    def chain_info():
        with lock:
            return chain.info()

    app.mount("/", StaticFiles(directory=ROOT / "app" / "static", html=True), name="static")
    return app
