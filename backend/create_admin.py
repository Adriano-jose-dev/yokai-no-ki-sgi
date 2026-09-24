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

from database import SessionLocal, Base, engine
from models import Usuario
from business.auth import hash_senha

# Diretoria do Dojo — usuários fixos do MVP (papel admin).
USUARIOS_INICIAIS = [
    {"username": "sawayama.naryu", "senha": "Yokai2026*", "role": "admin"},
    {"username": "sumiyoshi.kaito", "senha": "Yokai2026*", "role": "admin"},
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

            db.add(
                Usuario(
                    username=dados["username"],
                    senha_hash=hash_senha(dados["senha"]),
                    role=dados["role"],
                    ativo=True,
                )
            )
            print(f"Usuário admin '{dados['username']}' criado com sucesso.")
        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    criar_usuarios_iniciais()
    print("Carga inicial concluída. Lembre-se de trocar as senhas após o 1º acesso.")
