"""
Configuração por ambiente — SGI-YKR (Fase A / Requisito 8).

Lê variáveis de ambiente (opcionalmente de um arquivo `.env` via python-dotenv)
e as expõe como constantes tipadas para o resto da aplicação. Nada de segredos
ou strings de conexão escritos no código-fonte.

Variáveis suportadas:
- DATABASE_URL   : string de conexão do banco. Sem ela, cai em SQLite local.
- JWT_SECRET     : segredo para assinar os tokens JWT (Fase A / Requisito 6).
- JWT_EXPIRE_MIN : expiração do token em minutos.
- CORS_ORIGINS   : origens permitidas, separadas por vírgula (Requisito 7).
"""

import os

from dotenv import load_dotenv

# Carrega o .env se existir (em produção as variáveis vêm do ambiente).
load_dotenv()

# --- Banco de dados ---
# Fallback para SQLite local: assim o ambiente de desenvolvimento funciona sem
# nenhuma configuração extra.
DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./yokai.db")

# --- Autenticação (JWT) ---
# Em produção, JWT_SECRET DEVE ser definido no ambiente. O valor abaixo é apenas
# um padrão de desenvolvimento e nunca deve ser usado em produção.
PADRAO_INSEGURO_JWT = "dev-secret-inseguro-trocar-em-producao"
JWT_SECRET: str = os.getenv("JWT_SECRET", PADRAO_INSEGURO_JWT)
JWT_EXPIRE_MIN: int = int(os.getenv("JWT_EXPIRE_MIN", "60"))

# --- CORS ---
# Lista separada por vírgula. Em dev, a origem local do Angular é o padrão.
_cors_raw: str = os.getenv("CORS_ORIGINS", "http://localhost:4200")
CORS_ORIGINS: list[str] = [
    origem.strip() for origem in _cors_raw.split(",") if origem.strip()
]


def is_sqlite() -> bool:
    """Indica se a URL de conexão aponta para um banco SQLite."""
    return DATABASE_URL.startswith("sqlite")


def validar_seguranca_producao() -> None:
    """Fail-safe (S1): impede subir em produção com segredo inseguro.

    Em produção (banco NÃO-SQLite, i.e. PostgreSQL), um `JWT_SECRET` igual ao
    padrão de desenvolvimento permitiria a QUALQUER UM forjar tokens admin
    válidos. Para evitar esse vazamento por descuido de configuração, a
    aplicação **recusa iniciar** nesse cenário, com uma mensagem clara de como
    corrigir.

    Em desenvolvimento (SQLite) o padrão é tolerado — só emite nada e segue.
    Chamada no startup da aplicação (lifespan do `main.py`).
    """
    if is_sqlite():
        return  # dev local: padrão tolerado por conveniência
    if JWT_SECRET == PADRAO_INSEGURO_JWT or not JWT_SECRET:
        raise RuntimeError(
            "JWT_SECRET inseguro em produção. Defina a variável de ambiente "
            "JWT_SECRET com um valor forte e aleatório (ex.: "
            '`python -c "import secrets; print(secrets.token_hex(32))"`) '
            "antes de iniciar a aplicação."
        )
