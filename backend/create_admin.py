"""
Script de carga inicial de usuários — SGI-YKR (Fase A / Requisito 6.4).

Cria os usuários fixos da diretoria do Dojo para o primeiro acesso do MVP,
ambos com papel `admin`.

⚠️ ATENÇÃO (segurança): as credenciais abaixo estão chumbadas no código apenas
por decisão explícita para o MVP. Troque estas senhas após o primeiro acesso e,
para produção real, prefira criação via variáveis de ambiente / gestor de
segredos, evitando senhas versionadas no repositório.

Uso (na pasta YnkBD/, com o venv ativo):

    python create_admin.py

É idempotente: usuários já existentes não são recriados.
"""

import os

from database import SessionLocal, Base, engine
from models import Usuario
from business.auth import hash_senha, validar_forca_senha


def _usuario_env(indice: int, user_padrao: str, senha_padrao: str) -> dict:
    """Monta um usuário inicial lendo credenciais do ambiente (S1/S2).

    Em produção, defina `YNK_ADMIN{indice}_USER` e `YNK_ADMIN{indice}_PASS`.
    Em dev, caímos nos valores padrão do MVP (apenas conveniência local).
    """
    return {
        "username": os.getenv(f"YNK_ADMIN{indice}_USER", user_padrao),
        "senha": os.getenv(f"YNK_ADMIN{indice}_PASS", senha_padrao),
        "role": "admin",
    }


# Diretoria do Dojo. As credenciais vêm de variáveis de ambiente em produção;
# os valores padrão abaixo são apenas o fallback de desenvolvimento (MVP).
USUARIOS_INICIAIS = [
    _usuario_env(1, "sawayama.naryu", "Yokai2026*"),
    _usuario_env(2, "sumiyoshi.kaito", "Yokai2026*"),
]


def criar_usuarios_iniciais() -> None:
    # Garante que a tabela exista (útil em banco novo sem migrations aplicadas).
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        for dados in USUARIOS_INICIAIS:
            existente = (
                db.query(Usuario)
                .filter(Usuario.username == dados["username"])
                .first()
            )
            if existente:
                print(f"Usuário '{dados['username']}' já existe. Pulando.")
                continue

            # S2: recusa senha fraca já na carga inicial.
            ok, motivo = validar_forca_senha(dados["senha"])
            if not ok:
                print(
                    f"Usuário '{dados['username']}' NÃO criado: senha fraca "
                    f"({motivo}). Defina YNK_ADMIN*_PASS com uma senha forte."
                )
                continue

            db.add(
                Usuario(
                    username=dados["username"],
                    senha_hash=hash_senha(dados["senha"]),
                    role=dados["role"],
                    ativo=True,
                    # S2: obriga a troca no primeiro acesso.
                    precisa_trocar_senha=True,
                )
            )
            print(f"Usuário admin '{dados['username']}' criado com sucesso.")
        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    criar_usuarios_iniciais()
    print("Carga inicial concluída. Lembre-se de trocar as senhas após o 1º acesso.")
