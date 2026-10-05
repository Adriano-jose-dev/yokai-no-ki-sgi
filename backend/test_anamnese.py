"""
Testes do domínio Anamnese versionada + card de alerta crítico (Fase 3).

Cobre as regras do steering (Fase 3):
- versionamento: nova versão desativa a anterior; histórico preservado;
- cálculo de validade (6 e 12 meses) e status (ok / vence_em_breve / vencida);
- card de alerta extraído das condições críticas (asma, cardíaco, etc.);
- contatos de emergência herdados da ficha quando omitidos;
- sincronização da string legada `restricao_medica`;
- validade_meses inválida recusada; exigência de admin.
"""

from datetime import date, timedelta

from main import Aluno, Contrato, Anamnese
from business import anamnese as svc


def _aluno(db, id_mat="YNK0001", nome="Bianca"):
    db.add(
        Aluno(
            id_matricula=id_mat,
            nome=nome,
            contato_emergencia_nome="Mãe da Bianca",
            contato_emergencia_parentesco="Mãe",
            contato_emergencia_telefone="11999990000",
        )
    )
    db.add(Contrato(id_aluno=id_mat))
    db.commit()


# --- Unidade: business puro ---

def test_calcular_validade_12_meses():
    assert svc.calcular_validade(date(2026, 3, 15), 12) == date(2027, 3, 15)


def test_calcular_validade_6_meses_mes_curto():
    # 31/08 + 6 meses cai em fevereiro (mês curto) -> último dia.
    assert svc.calcular_validade(date(2026, 8, 31), 6) == date(2027, 2, 28)


def test_status_validade():
    hoje = date(2026, 9, 24)
    assert svc.status_validade(date(2026, 9, 1), hoje)["status"] == "vencida"
    assert svc.status_validade(date(2026, 10, 10), hoje)["status"] == "vence_em_breve"
    assert svc.status_validade(date(2027, 6, 1), hoje)["status"] == "ok"


def test_extrair_condicoes_criticas_filtra_nao_criticas():
    respostas = {"asma": "sim", "cirurgias": "sim", "diabetes": "nao"}
    criticas = svc.extrair_condicoes_criticas(respostas)
    assert "asma" in criticas       # crítica
    assert "cirurgias" not in criticas  # marcada mas NÃO crítica
    assert "diabetes" not in criticas   # crítica, mas resposta 'nao'


def test_serializar_restricao_legada():
    s = svc.serializar_restricao_legada({"asma": "sim", "diabetes": "sim"}, "usa bombinha")
    assert s == "Condições: asma, diabetes. Obs: usa bombinha"
    assert svc.serializar_restricao_legada({}, None) is None


# --- API: versionamento ---

def test_primeira_versao(client, db_session):
    _aluno(db_session)
    r = client.post(
        "/anamnese/YNK0001",
        json={"respostas": {"asma": "sim"}, "observacao": "leve", "validade_meses": 12},
    )
    assert r.status_code == 200
    assert r.json()["versao"] == 1
    assert r.json()["card_alerta"]["tem_alerta"] is True


def test_nova_versao_desativa_anterior(client, db_session):
    _aluno(db_session)
    client.post("/anamnese/YNK0001", json={"respostas": {"asma": "sim"}})
    client.post("/anamnese/YNK0001", json={"respostas": {"diabetes": "sim"}})

    ativas = (
        db_session.query(Anamnese)
        .filter(Anamnese.id_aluno == "YNK0001", Anamnese.ativa == True)  # noqa: E712
        .all()
    )
    assert len(ativas) == 1
    assert ativas[0].versao == 2

    historico = client.get("/anamnese/YNK0001/historico").json()
    assert len(historico) == 2  # histórico preservado
    assert historico[0]["versao"] == 2 and historico[1]["versao"] == 1


def test_card_alerta_lista_condicoes_criticas(client, db_session):
    _aluno(db_session)
    client.post(
        "/anamnese/YNK0001",
        json={"respostas": {"problemas_cardiacos": "sim", "cirurgias": "sim"}},
    )
    card = client.get("/anamnese/YNK0001").json()["card_alerta"]
    chaves = [c["chave"] for c in card["condicoes"]]
    assert "problemas_cardiacos" in chaves
    assert "cirurgias" not in chaves  # não é crítica
    assert card["tem_alerta"] is True


def test_card_sem_condicoes_nao_alerta(client, db_session):
    _aluno(db_session)
    client.post("/anamnese/YNK0001", json={"respostas": {"asma": "nao"}})
    card = client.get("/anamnese/YNK0001").json()["card_alerta"]
    assert card["tem_alerta"] is False
    assert card["condicoes"] == []


def test_contato_emergencia_herdado_da_ficha(client, db_session):
    _aluno(db_session)
    client.post("/anamnese/YNK0001", json={"respostas": {"asma": "sim"}})
    card = client.get("/anamnese/YNK0001").json()["card_alerta"]
    assert card["contato_emergencia"]["nome"] == "Mãe da Bianca"
    assert card["contato_emergencia"]["telefone"] == "11999990000"


def test_sincroniza_restricao_legada(client, db_session):
    _aluno(db_session)
    client.post(
        "/anamnese/YNK0001",
        json={"respostas": {"asma": "sim"}, "observacao": "usa bombinha"},
    )
    aluno = db_session.query(Aluno).filter(Aluno.id_matricula == "YNK0001").first()
    assert aluno.restricao_medica == "Condições: asma. Obs: usa bombinha"


def test_validade_meses_invalida_400(client, db_session):
    _aluno(db_session)
    r = client.post("/anamnese/YNK0001", json={"respostas": {}, "validade_meses": 9})
    assert r.status_code == 400


def test_anamnese_aluno_inexistente_404(client, db_session):
    assert client.get("/anamnese/NAOEXISTE").status_code == 404


def test_sem_anamnese_card_null(client, db_session):
    _aluno(db_session)
    resp = client.get("/anamnese/YNK0001").json()
    assert resp["ativa"] is None
    assert resp["card_alerta"] is None


def test_anamnese_exige_autenticacao(client_sem_auth, db_session):
    assert client_sem_auth.get("/anamnese/YNK0001").status_code == 401
