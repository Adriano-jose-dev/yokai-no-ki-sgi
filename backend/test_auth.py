"""
Testes de autenticação JWT — Tarefa 10.5 / Requisito 6.

Cobre:
- login com credenciais válidas -> 200 + access_token;
- login com senha errada / usuário inexistente / inativo -> 401;
- rota protegida sem token -> 401;
- rota protegida com token válido -> 200.

Usa a fixture `client_sem_auth` (sem override de auth) para exercitar o fluxo
real de segurança.
"""

from main import Usuario
from business.auth import hash_senha


def _criar_usuario(db, username="admin", senha="segredo123", role="admin", ativo=True):
    db.add(
        Usuario(
            username=username,
            senha_hash=hash_senha(senha),
            role=role,
            ativo=ativo,
        )
    )
    db.commit()


def test_login_valido_retorna_token(client_sem_auth, db_session):
    _criar_usuario(db_session, username="admin", senha="segredo123")

    resp = client_sem_auth.post(
        "/auth/login", data={"username": "admin", "password": "segredo123"}
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["token_type"] == "bearer"
    assert isinstance(body["access_token"], str) and body["access_token"]


def test_login_senha_errada_401(client_sem_auth, db_session):
    _criar_usuario(db_session, username="admin", senha="segredo123")

    resp = client_sem_auth.post(
        "/auth/login", data={"username": "admin", "password": "errada"}
    )
    assert resp.status_code == 401


def test_login_usuario_inexistente_401(client_sem_auth, db_session):
    resp = client_sem_auth.post(
        "/auth/login", data={"username": "ninguem", "password": "x"}
    )
    assert resp.status_code == 401


def test_login_usuario_inativo_401(client_sem_auth, db_session):
    _criar_usuario(db_session, username="antigo", senha="segredo123", ativo=False)

    resp = client_sem_auth.post(
        "/auth/login", data={"username": "antigo", "password": "segredo123"}
    )
    assert resp.status_code == 401


def test_rota_protegida_sem_token_401(client_sem_auth, db_session):
    # /alunos é protegida por requer_papel("admin"); sem token deve dar 401.
    resp = client_sem_auth.get("/alunos")
    assert resp.status_code == 401


def test_rota_protegida_com_token_valido_200(client_sem_auth, db_session):
    _criar_usuario(db_session, username="admin", senha="segredo123")

    login = client_sem_auth.post(
        "/auth/login", data={"username": "admin", "password": "segredo123"}
    )
    token = login.json()["access_token"]

    resp = client_sem_auth.get(
        "/alunos", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 200
    assert resp.json() == []


def test_rota_protegida_token_invalido_401(client_sem_auth, db_session):
    resp = client_sem_auth.get(
        "/alunos", headers={"Authorization": "Bearer token-falso"}
    )
    assert resp.status_code == 401
