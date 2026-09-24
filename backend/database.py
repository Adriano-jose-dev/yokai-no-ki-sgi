"""
Camada de acesso ao banco — SGI-YKR.

Concentra o engine, a fábrica de sessões, a `Base` declarativa e a dependência
`get_db`. Isolado aqui para que models, routers e testes compartilhem a mesma
configuração sem duplicação.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

import config

# String de conexão vinda da configuração de ambiente (fallback SQLite local).
DATABASE_URL = config.DATABASE_URL

# `check_same_thread=False` só faz sentido (e só é aceito) no SQLite. Para
# PostgreSQL e outros bancos, não passamos esse argumento.
_connect_args = {"check_same_thread": False} if config.is_sqlite() else {}

engine = create_engine(DATABASE_URL, connect_args=_connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """Dependência FastAPI: abre uma sessão por request e a fecha no fim."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
