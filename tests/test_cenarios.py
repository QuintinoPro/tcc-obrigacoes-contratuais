"""Cenários de teste do protótipo (etapa 6 da monografia).

C1 — Extração: o extrator encontra as obrigações do contrato fictício e acerta responsável e prazo.
C2 — Ciclo completo: entrega rejeitada, reexecução, aprovação e conclusão; estado off-chain = on-chain.
C3 — Máquina de estados: transições inválidas são barradas na API e no smart contract.
C4 — Permissões: só o responsável executa e só a outra parte aprova.
C5 — Integridade: arquivo idêntico é reconhecido; arquivo alterado em 1 byte é detectado.
C6 — Auditoria: cada ação gera evento off-chain com tx correspondente on-chain.
C7 — Adulteração off-chain: alterar o banco por fora é detectado pelo hash registrado on-chain.
C8 — Evidência: o hash da evidência é encontrado na blockchain (não no banco).
C9 — Entradas inválidas: não-PDF, prazo inválido, responsável inválido e evidência ausente são recusados.
C10 — Extração (regressão): o extrator v2 mantém 100% no conjunto de desenvolvimento.
C11 — Revisão humana: sugestões só viram obrigações após confirmação; correções e descartes prevalecem.
C12 — Atraso: obrigação vencida e não aprovada é marcada como atrasada; as demais não.
"""
import io

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from samples.gerar_contrato_exemplo import GABARITO, SAMPLE_PATH


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    app = create_app(tmp_path_factory.mktemp("data"))
    return TestClient(app)


@pytest.fixture(scope="module")
def contrato(client):
    r = client.post("/api/contracts/exemplo")
    assert r.status_code == 200
    return r.json()


def confirmar(client, contrato):
    sug = contrato["sugestao"]
    body = {"usuario": "revisor", "contratante": sug["contratante"], "contratada": sug["contratada"], "obrigacoes": sug["obrigacoes"]}
    r = client.post(f"/api/contracts/{contrato['id']}/confirmar", json=body)
    assert r.status_code == 200, r.text
    return r.json()


def mover(client, oid, para, papel, usuario="u", evid=None, **extra):
    files = {"evidencia": ("entrega.pdf", evid, "application/pdf")} if evid else None
    return client.post(f"/api/obligations/{oid}/transicao", data={"para": para, "papel": papel, "usuario": usuario, **extra}, files=files)


def test_c1_extracao(contrato):
    sug = contrato["sugestao"]
    assert sug["contratante"].startswith("Alfa Comércio")
    assert sug["contratada"].startswith("Beta Serviços")
    by_clause = {o["clausula"]: o for o in sug["obrigacoes"]}
    acertos_resp = sum(by_clause.get(g["clausula"], {}).get("responsavel") == g["responsavel"] for g in GABARITO)
    acertos_prazo = sum(by_clause.get(g["clausula"], {}).get("prazo") == g["prazo"] for g in GABARITO)
    print(f"\n[C1] obrigações: {len(by_clause)}/{len(GABARITO)} · responsável {acertos_resp}/{len(GABARITO)} · prazo {acertos_prazo}/{len(GABARITO)}")
    assert set(by_clause) == {g["clausula"] for g in GABARITO}
    assert acertos_resp == len(GABARITO)
    assert acertos_prazo == len(GABARITO)


def test_c2_ciclo_completo(client, contrato):
    det = confirmar(client, contrato)
    assert len(det["obrigacoes"]) == len(GABARITO)
    o = next(x for x in det["obrigacoes"] if x["clausula"] == "2.2")  # responsável: CONTRATADA
    oid = o["id"]
    assert o["status"] == o["onchain_status"] == "PENDENTE"

    passos = [
        ("EM_EXECUCAO", "CONTRATADA", None),
        ("ENTREGUE", "CONTRATADA", b"pecas v1"),
        ("EM_ANALISE", "CONTRATANTE", None),
        ("REJEITADO", "CONTRATANTE", None),
        ("EM_EXECUCAO", "CONTRATADA", None),
        ("ENTREGUE", "CONTRATADA", b"pecas v2"),
        ("EM_ANALISE", "CONTRATANTE", None),
        ("APROVADO", "CONTRATANTE", None),
        ("CONCLUIDO", "CONTRATANTE", None),
    ]
    for para, papel, evid in passos:
        r = mover(client, oid, para, papel, evid=evid)
        assert r.status_code == 200, r.text
        assert r.json()["status"] == r.json()["onchain_status"] == para

    hist = client.get(f"/api/obligations/{oid}/onchain").json()
    assert [e["to"] for e in hist["eventos"]] == [p[0] for p in passos]
    assert len(r.json()["evidencias"]) == 2
    assert all(x["dados_integros"] for x in client.get(f"/api/contracts/{contrato['id']}").json()["obrigacoes"])


def test_c3_transicoes_invalidas(client, contrato):
    det = client.get(f"/api/contracts/{contrato['id']}").json()
    o = next(x for x in det["obrigacoes"] if x["clausula"] == "2.1")
    assert mover(client, o["id"], "APROVADO", "CONTRATANTE").status_code == 409   # PENDENTE → APROVADO
    assert mover(client, o["id"], "CONCLUIDO", "CONTRATANTE").status_code == 409
    chain = client.app.state.chain
    assert chain.is_valid_transition("PENDENTE", "EM_EXECUCAO")
    assert not chain.is_valid_transition("PENDENTE", "APROVADO")
    with pytest.raises(Exception):  # o contrato reverte mesmo se a API for contornada
        chain.transition(o["id"], "APROVADO", None, "00" * 32)
    assert chain.obligation_status(o["id"]) == "PENDENTE"


def test_c4_permissoes(client, contrato):
    det = client.get(f"/api/contracts/{contrato['id']}").json()
    o = next(x for x in det["obrigacoes"] if x["clausula"] == "2.4")  # CONTRATADA executa
    assert mover(client, o["id"], "EM_EXECUCAO", "CONTRATANTE").status_code == 403
    assert mover(client, o["id"], "EM_EXECUCAO", "CONTRATADA").status_code == 200
    assert mover(client, o["id"], "ENTREGUE", "CONTRATADA").status_code == 400  # sem evidência
    assert mover(client, o["id"], "ENTREGUE", "CONTRATADA", evid=b"relatorio").status_code == 200
    assert mover(client, o["id"], "EM_ANALISE", "CONTRATADA").status_code == 403  # não aprova a própria entrega


def test_c5_integridade(client):
    original = SAMPLE_PATH.read_bytes()
    r = client.post("/api/verificar", files={"arquivo": ("c.pdf", io.BytesIO(original))}).json()
    assert r["integro"] and r["tipo"] == "contrato"
    alterado = bytearray(original)
    alterado[len(alterado) // 2] ^= 0x01
    r = client.post("/api/verificar", files={"arquivo": ("c.pdf", io.BytesIO(bytes(alterado)))}).json()
    assert not r["integro"]


def test_c6_auditoria(client, contrato):
    det = client.get(f"/api/contracts/{contrato['id']}").json()
    eventos = det["eventos"]
    mudancas = [e for e in eventos if e["tipo"] == "MUDANCA_DE_ESTADO"]
    assert mudancas and all(e["tx"] and e["bloco"] for e in mudancas)
    assert all(e["tx"] for e in eventos if e["tipo"] in ("OBRIGACAO_CRIADA", "CONTRATO_CADASTRADO"))
    assert len({e["tx"] for e in eventos if e["tx"]}) == len([e for e in eventos if e["tx"]])  # 1 tx por evento


def test_c7_adulteracao_do_banco(client, contrato):
    det = client.get(f"/api/contracts/{contrato['id']}").json()
    o = next(x for x in det["obrigacoes"] if x["clausula"] == "3.3")
    assert o["dados_integros"]
    db = client.app.state.db
    db.execute("UPDATE obligations SET prazo='2027-06-30' WHERE id=?", (o["id"],))  # alguém adia o prazo direto no banco
    db.commit()
    det = client.get(f"/api/contracts/{contrato['id']}").json()
    o2 = next(x for x in det["obrigacoes"] if x["id"] == o["id"])
    assert not o2["dados_integros"]
    assert all(x["dados_integros"] for x in det["obrigacoes"] if x["id"] != o["id"])


def test_c8_evidencia_verificada_na_chain(client, contrato):
    det = client.get(f"/api/contracts/{contrato['id']}").json()
    o = next(x for x in det["obrigacoes"] if x["clausula"] == "3.1")  # CONTRATANTE executa
    assert mover(client, o["id"], "EM_EXECUCAO", "CONTRATANTE").status_code == 200
    assert mover(client, o["id"], "ENTREGUE", "CONTRATANTE", evid=b"acesso concedido").status_code == 200
    client.app.state.db.execute("DELETE FROM evidences")  # mesmo apagando o registro off-chain...
    client.app.state.db.commit()
    r = client.post("/api/verificar", files={"arquivo": ("e.txt", io.BytesIO(b"acesso concedido"))}).json()
    assert r["integro"] and r["tipo"] == "evidência" and r["obrigacao_id"] == o["id"]  # ...a chain prova


def test_c9_entradas_invalidas(client, contrato):
    assert client.post("/api/contracts", files={"arquivo": ("x.pdf", io.BytesIO(b"<html>nao sou pdf</html>"))}).status_code == 415
    novo = client.post("/api/contracts/exemplo").json()
    base = {"usuario": "r", "contratante": "A", "contratada": "B"}
    ob = {"descricao": "x", "responsavel": "CONTRATADA"}
    url = f"/api/contracts/{novo['id']}/confirmar"
    assert client.post(url, json={**base, "obrigacoes": [{**ob, "prazo": "2026-13-40"}]}).status_code == 422
    assert client.post(url, json={**base, "obrigacoes": [{**ob, "responsavel": "ADMIN"}]}).status_code == 422
    assert client.post(url, json={**base, "obrigacoes": []}).status_code == 422
    assert client.get(f"/api/contracts/{novo['id']}").json()["status"] == "EM_REVISAO"  # nada foi gravado
    assert mover(client, 999999, "EM_EXECUCAO", "CONTRATADA").status_code == 404
    assert mover(client, 1, "HACKEADO", "CONTRATADA").status_code == 400


def test_c10_regressao_extracao():
    from scripts.avaliar_extracao import VERSOES, avaliar
    from samples.corpus import CORPUS
    res = [avaliar(i, VERSOES["v2"]) for i in CORPUS]
    assert sum(r["detectadas"] for r in res) == sum(r["gabarito"] for r in res)
    assert all(r["falsos_positivos"] == 0 for r in res)


def test_c11_revisao_corrige_e_descarta(client):
    """RF04 e RNF02: nada vira obrigação sem confirmação; correções e descartes do revisor prevalecem."""
    novo = client.post("/api/contracts/exemplo").json()
    det = client.get(f"/api/contracts/{novo['id']}").json()
    assert det["status"] == "EM_REVISAO" and det["obrigacoes"] == []  # sugestão ainda não é obrigação
    sug = novo["sugestao"]["obrigacoes"]
    mantidas = [o for o in sug if o["clausula"] != "3.2"]  # revisor descarta a 3.2
    corrigida = next(o for o in mantidas if o["clausula"] == "2.4")
    corrigida.update(prazo="2027-01-08", editada=True)  # revisor corrige o prazo
    body = {"usuario": "revisor", "contratante": "A", "contratada": "B", "obrigacoes": mantidas}
    det = client.post(f"/api/contracts/{novo['id']}/confirmar", json=body).json()
    assert len(det["obrigacoes"]) == len(sug) - 1
    assert "3.2" not in {o["clausula"] for o in det["obrigacoes"]}
    o24 = next(o for o in det["obrigacoes"] if o["clausula"] == "2.4")
    assert o24["prazo"] == "2027-01-08" and o24["editada"] == 1 and o24["dados_integros"]
    assert det["extracao"]["obrigacoes"][3]["prazo"] == "2027-01-05"  # a sugestão original fica guardada para auditoria
    assert any("corrigida na revisão" in (e["observacao"] or "") for e in det["eventos"])


def test_c12_obrigacoes_em_atraso(client):
    """RF10: atrasada = prazo vencido e obrigação ainda não aprovada."""
    novo = client.post("/api/contracts/exemplo").json()
    obs = [
        {"clausula": "A", "descricao": "vencida e pendente", "responsavel": "CONTRATADA", "prazo": "2000-01-01"},
        {"clausula": "B", "descricao": "vencida e aprovada", "responsavel": "CONTRATADA", "prazo": "2000-01-01"},
        {"clausula": "C", "descricao": "no futuro", "responsavel": "CONTRATADA", "prazo": "2999-01-01"},
        {"clausula": "D", "descricao": "sem prazo", "responsavel": "CONTRATADA", "prazo": None},
    ]
    det = client.post(f"/api/contracts/{novo['id']}/confirmar",
                      json={"usuario": "r", "contratante": "A", "contratada": "B", "obrigacoes": obs}).json()
    b = next(o for o in det["obrigacoes"] if o["clausula"] == "B")
    for para, papel, ev in [("EM_EXECUCAO", "CONTRATADA", None), ("ENTREGUE", "CONTRATADA", b"x"),
                            ("EM_ANALISE", "CONTRATANTE", None), ("APROVADO", "CONTRATANTE", None)]:
        assert mover(client, b["id"], para, papel, evid=ev).status_code == 200
    det = client.get(f"/api/contracts/{novo['id']}").json()
    atraso = {o["clausula"]: o["atrasada"] for o in det["obrigacoes"]}
    assert atraso == {"A": True, "B": False, "C": False, "D": False}
