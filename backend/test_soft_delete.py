"""
Testes do Soft Delete — Tarefa 5 / Requisito 4.

Cobre:
- PUT /alunos/{id}/desativar muda status para Inativo (nunca remove do banco).
- Desativar encerra sessão de tatame aberta.
- Histórico (sessões, pagamentos, presenças) é preservado após desativar.
- Aluno Inativo some das listas operacionais (/tatame/ativos e /presenca/diaria).
- 404 ao desativar aluno inexistente.
"""

from datetime import date, datetime, timedelta

from main import Aluno, Contrato, Sessao, Pagamento, Presenca


def _criar_aluno(db, id_matricula="YNK0001", nome="Aluno SD", status="Ativo"):
    db.add(Aluno(id_matricula=id_matricula, nome=nome, status_atividade=status))
    db.add(Contrato(id_aluno=id_matricula, modelo_plano="Horas Livres"))
    db.commit()


def test_desativar_muda_status_para_inativo(client, db_session):
    _criar_aluno(db_session)

    resp = client.put("/alunos/YNK0001/desativar")

    assert resp.status_code == 200
    aluno = db_session.query(Aluno).filter(Aluno.id_matricula == "YNK0001").first()
    # O registro continua existindo (soft delete), apenas muda de status.
    assert aluno is not None
    assert aluno.status_atividade == "Inativo"


def test_desativar_encerra_sessao_aberta(client, db_session):
    _criar_aluno(db_session)
    db_session.add(
        Sessao(
            id_aluno="YNK0001",
            hora_entrada=datetime.now() - timedelta(hours=1),
            hora_saida=None,
        )
    )
    db_session.commit()

    client.put("/alunos/YNK0001/desativar")

    sessao = db_session.query(Sessao).filter(Sessao.id_aluno == "YNK0001").first()
    assert sessao.hora_saida is not None
    assert "[SISTEMA]" in (sessao.diario_sensei or "")


def test_desativar_preserva_historico(client, db_session):
    _criar_aluno(db_session)
    db_session.add(
        Sessao(
            id_aluno="YNK0001",
            hora_entrada=datetime.now() - timedelta(hours=2),
            hora_saida=datetime.now() - timedelta(hours=1),
            valor_apurado=40.0,
        )
    )
    db_session.add(Pagamento(id_aluno="YNK0001", valor=40.0, metodo="Pix"))
    db_session.add(Presenca(id_aluno="YNK0001", data=date.today(), status="Presente"))
    db_session.commit()

    client.put("/alunos/YNK0001/desativar")

    # Histórico intacto após a desativação.
    assert (
        db_session.query(Sessao).filter(Sessao.id_aluno == "YNK0001").count() == 1
    )
    assert (
        db_session.query(Pagamento).filter(Pagamento.id_aluno == "YNK0001").count()
        == 1
    )
    assert (
        db_session.query(Presenca).filter(Presenca.id_aluno == "YNK0001").count()
        == 1
    )


def test_inativo_some_do_tatame(client, db_session):
    _criar_aluno(db_session, id_matricula="YNK0001", nome="Ativo Um", status="Ativo")
    _criar_aluno(
        db_session, id_matricula="YNK0002", nome="Inativo Dois", status="Inativo"
    )

    ids = [a["id_matricula"] for a in client.get("/tatame/ativos").json()]
    assert "YNK0001" in ids
    assert "YNK0002" not in ids


def test_inativo_some_da_presenca_diaria(client, db_session):
    _criar_aluno(db_session, id_matricula="YNK0001", nome="Ativo Um", status="Ativo")
    _criar_aluno(
        db_session, id_matricula="YNK0002", nome="Inativo Dois", status="Inativo"
    )

    hoje = date.today().isoformat()
    ids = [a["id_matricula"] for a in client.get(f"/presenca/diaria/{hoje}").json()]
    assert "YNK0001" in ids
    assert "YNK0002" not in ids


def test_desativar_inexistente_404(client, db_session):
    resp = client.put("/alunos/NAO_EXISTE/desativar")
    assert resp.status_code == 404
