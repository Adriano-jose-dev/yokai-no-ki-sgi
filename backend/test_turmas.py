"""
Testes de Turmas — Fase 1a do roadmap de evolução.

Cobre:
- criar turma (com e sem alunos) e detalhar;
- listar turmas ativas; desativar (soft);
- vincular/desvincular aluno (matriculado/ocorrente);
- regra: um aluno só pode ter UMA matrícula principal;
- gratuidade automática de ocorrente Legado em turma Dojo;
- validações de tipo_pagamento/classe;
- exigência de autenticação admin.
"""

from main import Aluno, Contrato, Turma, TurmaMatricula


def _criar_aluno(db, id_matricula="YNK0001", nome="Aluno Turma", status="Ativo"):
    db.add(Aluno(id_matricula=id_matricula, nome=nome, status_atividade=status))
    db.add(Contrato(id_aluno=id_matricula, modelo_plano="Horas Livres"))
    db.commit()


def test_criar_turma_simples(client, db_session):
    resp = client.post(
        "/turmas",
        json={
            "nome": "No Mori",
            "tipo_pagamento": "Mensalidade",
            "classe": "Dojo",
            "valor_base": 30.0,
            "recorrencia_rrule": "FREQ=WEEKLY;BYDAY=SA",
            "recorrencia_descricao": "Todo sábado 19h-21h",
            "hora_inicio": "19:00",
            "hora_fim": "21:00",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["nome"] == "No Mori"
    assert body["tipo_pagamento"] == "Mensalidade"
    assert body["valor_base"] == 30.0
    assert body["alunos"] == []


def test_criar_turma_com_alunos(client, db_session):
    _criar_aluno(db_session, "YNK0001", "Bianca")
    _criar_aluno(db_session, "YNK0002", "Francisco")

    resp = client.post(
        "/turmas",
        json={
            "nome": "No Mori",
            "tipo_pagamento": "Mensalidade",
            "classe": "Dojo",
            "valor_base": 30.0,
            "alunos": [
                {"id_aluno": "YNK0001", "papel": "matriculado"},
                {"id_aluno": "YNK0002", "papel": "matriculado"},
            ],
        },
    )
    assert resp.status_code == 200
    ids = [a["id_aluno"] for a in resp.json()["alunos"]]
    assert "YNK0001" in ids and "YNK0002" in ids


def test_listar_e_detalhar(client, db_session):
    client.post("/turmas", json={"nome": "Kirin", "tipo_pagamento": "Hora-Aula", "classe": "Legado", "valor_base": 50.0})
    lista = client.get("/turmas").json()
    assert len(lista) == 1
    tid = lista[0]["id"]
    det = client.get(f"/turmas/{tid}").json()
    assert det["nome"] == "Kirin"


def test_tipo_pagamento_invalido_400(client, db_session):
    resp = client.post("/turmas", json={"nome": "X", "tipo_pagamento": "Boleto", "classe": "Dojo"})
    assert resp.status_code == 400


def test_classe_invalida_400(client, db_session):
    resp = client.post("/turmas", json={"nome": "X", "tipo_pagamento": "Mensalidade", "classe": "Outra"})
    assert resp.status_code == 400


def test_aluno_so_pode_ter_uma_matricula(client, db_session):
    _criar_aluno(db_session, "YNK0001", "Lucas")
    t1 = client.post("/turmas", json={"nome": "T1", "tipo_pagamento": "Mensalidade", "classe": "Dojo"}).json()
    t2 = client.post("/turmas", json={"nome": "T2", "tipo_pagamento": "Mensalidade", "classe": "Dojo"}).json()

    r1 = client.post(f"/turmas/{t1['id']}/alunos", json={"id_aluno": "YNK0001", "papel": "matriculado"})
    assert r1.status_code == 200

    # Segunda matrícula principal em outra turma deve falhar.
    r2 = client.post(f"/turmas/{t2['id']}/alunos", json={"id_aluno": "YNK0001", "papel": "matriculado"})
    assert r2.status_code == 400


def test_ocorrente_legado_em_dojo_e_gratuito(client, db_session):
    _criar_aluno(db_session, "YNK0001", "Emmanuel")
    # Matriculado numa turma Legado.
    legado = client.post("/turmas", json={"nome": "Kirin", "tipo_pagamento": "Hora-Aula", "classe": "Legado", "valor_base": 50.0}).json()
    client.post(f"/turmas/{legado['id']}/alunos", json={"id_aluno": "YNK0001", "papel": "matriculado"})

    # Ocorrente numa turma Dojo -> deve ficar gratuito automaticamente.
    dojo = client.post("/turmas", json={"nome": "Rio Bossa Nova", "tipo_pagamento": "Hora-Aula", "classe": "Dojo", "valor_base": 40.0}).json()
    r = client.post(f"/turmas/{dojo['id']}/alunos", json={"id_aluno": "YNK0001", "papel": "ocorrente"})
    assert r.status_code == 200
    vinc = next(a for a in r.json()["alunos"] if a["id_aluno"] == "YNK0001")
    assert vinc["papel"] == "ocorrente"
    assert vinc["gratuito"] is True


def test_desvincular_aluno(client, db_session):
    _criar_aluno(db_session, "YNK0001", "Ricardo")
    t = client.post("/turmas", json={"nome": "T", "tipo_pagamento": "Mensalidade", "classe": "Dojo"}).json()
    client.post(f"/turmas/{t['id']}/alunos", json={"id_aluno": "YNK0001", "papel": "matriculado"})

    r = client.delete(f"/turmas/{t['id']}/alunos/YNK0001")
    assert r.status_code == 200
    assert client.get(f"/turmas/{t['id']}").json()["alunos"] == []


def test_desativar_turma_some_da_lista(client, db_session):
    t = client.post("/turmas", json={"nome": "Some", "tipo_pagamento": "Mensalidade", "classe": "Dojo"}).json()
    client.delete(f"/turmas/{t['id']}")
    assert client.get("/turmas").json() == []


def test_editar_turma(client, db_session):
    t = client.post("/turmas", json={"nome": "Antiga", "tipo_pagamento": "Mensalidade", "classe": "Dojo", "valor_base": 20.0}).json()
    r = client.put(f"/turmas/{t['id']}", json={"nome": "Nova", "valor_base": 35.0})
    assert r.status_code == 200
    assert r.json()["nome"] == "Nova"
    assert r.json()["valor_base"] == 35.0


def test_vincular_aluno_inexistente_404(client, db_session):
    t = client.post("/turmas", json={"nome": "T", "tipo_pagamento": "Mensalidade", "classe": "Dojo"}).json()
    r = client.post(f"/turmas/{t['id']}/alunos", json={"id_aluno": "NAO_EXISTE", "papel": "matriculado"})
    assert r.status_code == 404


def test_turmas_exige_autenticacao(client_sem_auth, db_session):
    assert client_sem_auth.get("/turmas").status_code == 401
