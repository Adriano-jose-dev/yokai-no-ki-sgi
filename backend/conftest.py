"""
Configuração de testes do back-end SGI-YKR.

Fornece um banco SQLite em memória isolado por teste e um TestClient do FastAPI
com a dependência get_db sobrescrita para apontar para esse banco. Assim os
testes não tocam o banco real (yokai.db) e cada teste começa com o esquema limpo.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

import main
from main import app, Base, get_db, Usuario
from business.auth import get_usuario_atual


@pytest.fixture()
def db_session():
    """Cria um banco SQLite em memória isolado e devolve uma sessão.

    Usa StaticPool para que todas as conexões compartilhem a mesma base em
    memória dentro do teste.
    """
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(
        autocommit=False, autoflush=False, bind=engine
    )
    # O esquema de teste é criado a partir de Base.metadata (mesma fonte que as
    # migrations do Alembic espelham). Optamos por create_all aqui, e não por
    # rodar o Alembic contra o :memory:, porque cada banco em memória é isolado
    # por conexão e o create_all é rápido, determinístico e equivalente ao
    # esquema versionado. A validade da cadeia de migrations é verificada
    # separadamente aplicando `alembic upgrade head` num banco em arquivo.
    Base.metadata.create_all(bind=engine)

    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client(db_session):
    """TestClient autenticado como admin.

    Sobrescreve `get_db` (banco em memória) e também `get_usuario_atual`, para
    que os testes de domínio (que exercitam a regra de negócio, não a auth)
    rodem como se um admin estivesse logado. Os testes de autenticação usam a
    fixture `client_sem_auth`, que NÃO sobrescreve a dependência de auth.
    """

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    def override_usuario_admin():
        return Usuario(username="admin_teste", senha_hash="x", role="admin", ativo=True)

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_usuario_atual] = override_usuario_admin
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def client_sem_auth(db_session):
    """TestClient SEM override de autenticação (só o banco em memória).

    Usado nos testes de auth para exercitar o fluxo real: login, 401 sem token,
    200 com token válido.
    """

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
