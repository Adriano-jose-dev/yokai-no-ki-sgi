"""
Testes de Ocorrências de Aula / Calendário — Fase 1b.

Cobre:
- geração a partir da RRULE (todo sábado; 1ª e 3ª terça do mês);
- idempotência (não duplica ao gerar de novo);
- listagem por período e detalhe do dia (com participantes);
- criação avulsa, edição/mover, cancelamento e exclusão;
- duração prevista calculada de hora_inicio/fim;
- exigência de admin.
"""

from datetime import date

from main import Turma, OcorrenciaAula, Aluno, Contrato, TurmaMatricula
from business.ocorrencias import expandir_datas


def _turma(client, nome="No Mori", rrule="FREQ=WEEKLY;BYDAY=SA",
           hi="19:00", hf="21:00", tipo="Mensalidade"):
    return client.post(
        "/turmas",
        json={
            "nome": nome,
            "tipo_pagamento": tipo,
            "classe": "Dojo",
            "valor_base": 30.0,
            "recorrencia_rrule": rrule,
            "hora_inicio": hi,
            "hora_fim": hf,
        },
    ).json()


# --- Expansão da RRULE (unidade, sem HTTP) ---

def test_expandir_todo_sabado():
    # Outubro/2026: sábados = 3, 10, 17, 24, 31.
    datas = expandir_datas("FREQ=WEEKLY;BYDAY=SA", date(2026, 10, 1), date(2026, 10, 31))
    assert date(2026, 10, 3) in datas
    assert date(2026, 10, 31) in datas
    assert len(datas) == 5
    # Nenhum dia útil no meio da semana.
    assert all(d.weekday() == 5 for d in datas)  # 5 = sábado


def test_expandir_primeira_e_terceira_terca():
    # 1ª e 3ª terça de out/2026: 6 e 20.
    datas = expandir_datas(
        "FREQ=MONTHLY;BYDAY=+1TU,+3TU", date(2026, 10, 1), date(2026, 10, 31)
    )
    assert date(2026, 10, 6) in datas
    assert date(2026, 10, 20) in datas
    assert len(datas) == 2


# --- Geração via API ---

def test_gerar_ocorrencias(client, db_session):
    t = _turma(client)
    r = client.post(
        f"/turmas/{t['id']}/ocorrencias/gerar",
        json={"data_inicio": "2026-10-01", "data_fim": "2026-10-31"},
    )
    assert r.status_code == 200
    assert r.json()["geradas"] == 5

    ocs = client.get("/ocorrencias?inicio=2026-10-01&fim=2026-10-31").json()
    assert len(ocs) == 5
    assert all(o["estado"] == "prevista" for o in ocs)
    assert all(o["origem"] == "recorrencia" for o in ocs)
    # Duração prevista 19:00-21:00 = 2h.
    assert ocs[0]["duracao_prevista_horas"] == 2.0


def test_gerar_e_idempotente(client, db_session):
    t = _turma(client)
    client.post(f"/turmas/{t['id']}/ocorrencias/gerar",
                json={"data_inicio": "2026-10-01", "data_fim": "2026-10-31"})
    # Segunda geração não deve duplicar.
    r2 = client.post(f"/turmas/{t['id']}/ocorrencias/gerar",
                     json={"data_inicio": "2026-10-01", "data_fim": "2026-10-31"})
    assert r2.json()["geradas"] == 0
    ocs = client.get("/ocorrencias?inicio=2026-10-01&fim=2026-10-31").json()
    assert len(ocs) == 5


def test_detalhe_do_dia_com_participantes(client, db_session):
    db_session.add(Aluno(id_matricula="YNK0001", nome="Bianca"))
    db_session.add(Contrato(id_aluno="YNK0001"))
    db_session.commit()
    t = _turma(client)
    client.post(f"/turmas/{t['id']}/alunos", json={"id_aluno": "YNK0001", "papel": "matriculado"})
    client.post(f"/turmas/{t['id']}/ocorrencias/gerar",
                json={"data_inicio": "2026-10-01", "data_fim": "2026-10-10"})

    dia = client.get("/calendario/dia/2026-10-03").json()
    assert len(dia) == 1
    assert dia[0]["turma_nome"] == "No Mori"
    ids = [p["id_aluno"] for p in dia[0]["participantes"]]
    assert "YNK0001" in ids


def test_criar_avulsa(client, db_session):
    t = _turma(client, tipo="Hora-Aula")
    r = client.post(
        "/ocorrencias/avulsa",
        json={"id_turma": t["id"], "data": "2026-10-15", "hora_inicio": "20:00", "hora_fim": "23:00", "observacao": "Remarcacao"},
    )
    assert r.status_code == 200
    assert r.json()["origem"] == "avulsa"
    assert r.json()["duracao_prevista_horas"] == 3.0


def test_mover_ocorrencia(client, db_session):
    t = _turma(client)
    client.post(f"/turmas/{t['id']}/ocorrencias/gerar",
                json={"data_inicio": "2026-10-01", "data_fim": "2026-10-10"})
    oc = client.get("/ocorrencias?inicio=2026-10-01&fim=2026-10-10").json()[0]

    r = client.put(f"/ocorrencias/{oc['id']}", json={"data": "2026-10-05"})
    assert r.status_code == 200
    assert r.json()["data"] == "2026-10-05"


def test_cancelar_ocorrencia(client, db_session):
    t = _turma(client)
    client.post(f"/turmas/{t['id']}/ocorrencias/gerar",
                json={"data_inicio": "2026-10-01", "data_fim": "2026-10-10"})
    oc = client.get("/ocorrencias?inicio=2026-10-01&fim=2026-10-10").json()[0]

    r = client.post(f"/ocorrencias/{oc['id']}/cancelar")
    assert r.status_code == 200
    atual = db_session.query(OcorrenciaAula).filter(OcorrenciaAula.id == oc["id"]).first()
    assert atual.estado == "cancelada"


def test_excluir_ocorrencia(client, db_session):
    t = _turma(client)
    client.post(f"/turmas/{t['id']}/ocorrencias/gerar",
                json={"data_inicio": "2026-10-01", "data_fim": "2026-10-10"})
    oc = client.get("/ocorrencias?inicio=2026-10-01&fim=2026-10-10").json()[0]

    r = client.delete(f"/ocorrencias/{oc['id']}")
    assert r.status_code == 200
    assert db_session.query(OcorrenciaAula).filter(OcorrenciaAula.id == oc["id"]).first() is None


def test_estado_invalido_400(client, db_session):
    t = _turma(client)
    client.post(f"/turmas/{t['id']}/ocorrencias/gerar",
                json={"data_inicio": "2026-10-01", "data_fim": "2026-10-10"})
    oc = client.get("/ocorrencias?inicio=2026-10-01&fim=2026-10-10").json()[0]
    r = client.put(f"/ocorrencias/{oc['id']}", json={"estado": "qualquer"})
    assert r.status_code == 400


def test_marcar_presenca_mensalista(client, db_session):
    from main import Presenca
    db_session.add(Aluno(id_matricula="YNK0001", nome="Bianca"))
    db_session.add(Contrato(id_aluno="YNK0001"))
    db_session.commit()
    t = _turma(client)  # Mensalidade
    client.post(f"/turmas/{t['id']}/alunos", json={"id_aluno": "YNK0001", "papel": "matriculado"})
    client.post(f"/turmas/{t['id']}/ocorrencias/gerar",
                json={"data_inicio": "2026-10-01", "data_fim": "2026-10-10"})
    oc = client.get("/ocorrencias?inicio=2026-10-01&fim=2026-10-10").json()[0]

    r = client.post(f"/ocorrencias/{oc['id']}/presenca", json={"id_aluno": "YNK0001", "presente": True})
    assert r.status_code == 200
    # Presença gravada e ocorrência marcada como realizada.
    pres = db_session.query(Presenca).filter(Presenca.id_aluno == "YNK0001").first()
    assert pres.status == "Presente"
    atual = db_session.query(OcorrenciaAula).filter(OcorrenciaAula.id == oc["id"]).first()
    assert atual.estado == "realizada"


def test_marcar_ausencia_atualiza_registro(client, db_session):
    from main import Presenca
    db_session.add(Aluno(id_matricula="YNK0002", nome="Ricardo"))
    db_session.add(Contrato(id_aluno="YNK0002"))
    db_session.commit()
    t = _turma(client)
    client.post(f"/turmas/{t['id']}/alunos", json={"id_aluno": "YNK0002", "papel": "matriculado"})
    client.post(f"/turmas/{t['id']}/ocorrencias/gerar",
                json={"data_inicio": "2026-10-01", "data_fim": "2026-10-10"})
    oc = client.get("/ocorrencias?inicio=2026-10-01&fim=2026-10-10").json()[0]

    client.post(f"/ocorrencias/{oc['id']}/presenca", json={"id_aluno": "YNK0002", "presente": True})
    client.post(f"/ocorrencias/{oc['id']}/presenca", json={"id_aluno": "YNK0002", "presente": False})
    pres = db_session.query(Presenca).filter(Presenca.id_aluno == "YNK0002").all()
    assert len(pres) == 1  # upsert, não duplica
    assert pres[0].status == "Ausente"


def test_registrar_duracao_real(client, db_session):
    t = _turma(client)
    client.post(f"/turmas/{t['id']}/ocorrencias/gerar",
                json={"data_inicio": "2026-10-01", "data_fim": "2026-10-10"})
    oc = client.get("/ocorrencias?inicio=2026-10-01&fim=2026-10-10").json()[0]

    r = client.put(f"/ocorrencias/{oc['id']}/duracao", json={"duracao_real_min": 118})
    assert r.status_code == 200
    atual = db_session.query(OcorrenciaAula).filter(OcorrenciaAula.id == oc["id"]).first()
    assert atual.duracao_real_min == 118
    assert atual.estado == "realizada"


def test_ocorrencias_exige_autenticacao(client_sem_auth, db_session):
    assert client_sem_auth.get("/ocorrencias?inicio=2026-10-01&fim=2026-10-31").status_code == 401
