"""
Testes da rota de atualização de valor base — Tarefa 4 / Requisito 3.

Contrato de rota (deve casar com o que o admin-detail já invoca):
    PUT /alunos/{id_matricula}/valor-base
    corpo: { "valor_base": number }

Cobre: sucesso (persistência) e 404 para aluno/contrato inexistente.
"""

from main import Aluno, Contrato


def _criar_aluno_com_contrato(db, id_matricula="YNK0001", valor_base=20.0):
    db.add(Aluno(id_matricula=id_matricula, nome="Aluno VB"))
    db.add(Contrato(id_aluno=id_matricula, valor_base=valor_base))
    db.commit()


def test_valor_base_atualiza_com_sucesso(client, db_session):
    _criar_aluno_com_contrato(db_session, valor_base=20.0)

    resp = client.put("/alunos/YNK0001/valor-base", json={"valor_base": 45.5})

    assert resp.status_code == 200
    assert resp.json()["valor_base"] == 45.5

    contrato = (
        db_session.query(Contrato).filter(Contrato.id_aluno == "YNK0001").first()
    )
    assert contrato.valor_base == 45.5


def test_valor_base_aluno_inexistente_404(client, db_session):
    resp = client.put("/alunos/NAO_EXISTE/valor-base", json={"valor_base": 30.0})
    assert resp.status_code == 404


def test_valor_base_sem_contrato_404(client, db_session):
    # Aluno existe, mas sem contrato associado.
    db_session.add(Aluno(id_matricula="YNK0002", nome="Sem Contrato"))
    db_session.commit()

    resp = client.put("/alunos/YNK0002/valor-base", json={"valor_base": 30.0})
    assert resp.status_code == 404
