"""
Testes do hardening de segurança — S1 (fail-safe de segredo), S2 (política de
senha + troca) e S3 (rate limiting no login).
"""

import importlib

import pytest

import config
from main import Usuario
from business.auth import hash_senha, validar_forca_senha
from business import ratelimit


def _criar_usuario(db, username="admin", senha="SenhaForte1!", precisa_trocar=False):
    db.add(
        Usuario(
            username=username,
            senha_hash=hash_senha(senha),
            role="admin",
            ativo=True,
            precisa_trocar_senha=precisa_trocar,
        )
    )
    db.commit()


# --- S2: validador de força de senha (unidade) ---

def test_forca_senha_rejeita_curta():
    ok, _ = validar_forca_senha("abc123")
    assert ok is False


def test_forca_senha_rejeita_so_digitos():
    ok, _ = validar_forca_senha("1234567890")
    assert ok is False


def test_forca_senha_rejeita_so_letras():
    ok, _ = validar_forca_senha("abcdefghij")
    assert ok is False


def test_forca_senha_aceita_mista():
    ok, motivo = validar_forca_senha("SenhaForte1!")
    assert ok is True and motivo == ""


# --- S1: fail-safe de produção ---

def test_failsafe_sqlite_nao_barra(monkeypatch):
    # Em SQLite (dev), mesmo com secret padrão, não deve levantar.
    monkeypatch.setattr(config, "DATABASE_URL", "sqlite:///./yokai.db")
    monkeypatch.setattr(config, "JWT_SECRET", config.PADRAO_INSEGURO_JWT)
    config.validar_seguranca_producao()  # não deve lançar


def test_failsafe_producao_barra_secret_padrao(monkeypatch):
    # Em produção (não-SQLite) com secret padrão, deve abortar.
    monkeypatch.setattr(
        config, "DATABASE_URL", "postgresql+psycopg2://u:p@host:5432/db"
    )
    monkeypatch.setattr(config, "JWT_SECRET", config.PADRAO_INSEGURO_JWT)
    with pytest.raises(RuntimeError):
        config.validar_seguranca_producao()


def test_failsafe_producao_ok_com_secret_forte(monkeypatch):
    monkeypatch.setattr(
        config, "DATABASE_URL", "postgresql+psycopg2://u:p@host:5432/db"
    )
    monkeypatch.setattr(config, "JWT_SECRET", "a" * 64)
    config.validar_seguranca_producao()  # não deve lançar


# --- S2: fluxo de troca de senha via API ---

def test_login_sinaliza_precisa_trocar(client_sem_auth, db_session):
    _criar_usuario(db_session, senha="SenhaForte1!", precisa_trocar=True)
    resp = client_sem_auth.post(
        "/auth/login", data={"username": "admin", "password": "SenhaForte1!"}
    )
    assert resp.status_code == 200
    assert resp.json()["precisa_trocar_senha"] is True


def test_trocar_senha_sucesso_limpa_flag(client_sem_auth, db_session):
    _criar_usuario(db_session, senha="SenhaForte1!", precisa_trocar=True)
    login = client_sem_auth.post(
        "/auth/login", data={"username": "admin", "password": "SenhaForte1!"}
    )
    token = login.json()["access_token"]

    resp = client_sem_auth.post(
        "/auth/trocar-senha",
        json={"senha_atual": "SenhaForte1!", "nova_senha": "OutraForte2@"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200

    # Novo login reflete a flag limpa e a nova senha.
    relogin = client_sem_auth.post(
        "/auth/login", data={"username": "admin", "password": "OutraForte2@"}
    )
    assert relogin.status_code == 200
    assert relogin.json()["precisa_trocar_senha"] is False


def test_trocar_senha_atual_errada_400(client_sem_auth, db_session):
    _criar_usuario(db_session, senha="SenhaForte1!")
    login = client_sem_auth.post(
        "/auth/login", data={"username": "admin", "password": "SenhaForte1!"}
    )
    token = login.json()["access_token"]
    resp = client_sem_auth.post(
        "/auth/trocar-senha",
        json={"senha_atual": "errada", "nova_senha": "OutraForte2@"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 400


def test_trocar_senha_nova_fraca_400(client_sem_auth, db_session):
    _criar_usuario(db_session, senha="SenhaForte1!")
    login = client_sem_auth.post(
        "/auth/login", data={"username": "admin", "password": "SenhaForte1!"}
    )
    token = login.json()["access_token"]
    resp = client_sem_auth.post(
        "/auth/trocar-senha",
        json={"senha_atual": "SenhaForte1!", "nova_senha": "123"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 400


# --- S3: rate limiting no login ---

def test_rate_limit_bloqueia_apos_tentativas(client_sem_auth, db_session):
    _criar_usuario(db_session, senha="SenhaForte1!")
    # MAX_TENTATIVAS falhas seguidas devem acabar bloqueando (429).
    for _ in range(ratelimit.MAX_TENTATIVAS):
        r = client_sem_auth.post(
            "/auth/login", data={"username": "admin", "password": "errada"}
        )
        assert r.status_code == 401
    # A próxima (mesmo com senha certa) deve vir 429 por bloqueio.
    r = client_sem_auth.post(
        "/auth/login", data={"username": "admin", "password": "SenhaForte1!"}
    )
    assert r.status_code == 429


def test_rate_limit_unidade():
    ratelimit.resetar()
    for i in range(ratelimit.MAX_TENTATIVAS - 1):
        assert ratelimit.registrar_falha("u", "1.1.1.1") is False
    # A última atinge o limite.
    assert ratelimit.registrar_falha("u", "1.1.1.1") is True
    assert ratelimit.esta_bloqueado("u", "1.1.1.1") > 0
    # Sucesso limpa.
    ratelimit.registrar_sucesso("u", "1.1.1.1")
    assert ratelimit.esta_bloqueado("u", "1.1.1.1") == 0
