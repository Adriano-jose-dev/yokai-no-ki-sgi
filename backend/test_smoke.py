"""
Teste de sanidade (smoke test) da infraestrutura de testes.

Valida que o TestClient sobe, que a dependência get_db aponta para o banco em
memória e que o esquema é criado limpo a cada teste.
"""


def test_listar_alunos_vazio(client):
    """Num banco recém-criado, a listagem de alunos deve vir vazia."""
    resp = client.get("/alunos")
    assert resp.status_code == 200
    assert resp.json() == []


def test_matricula_e_listagem(client):
    """Fluxo mínimo: matricular um aluno e vê-lo aparecer na listagem."""
    payload = {"nome": "Aluno Teste"}
    resp = client.post("/alunos/matricula", json=payload)
    assert resp.status_code == 200
    dados = resp.json()
    assert dados["nome"] == "Aluno Teste"
    assert dados["id_matricula"].startswith("YNK")

    lista = client.get("/alunos").json()
    assert len(lista) == 1
    assert lista[0]["nome"] == "Aluno Teste"
