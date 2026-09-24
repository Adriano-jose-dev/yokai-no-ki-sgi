#!/usr/bin/env bash
# Entrypoint da API em container.
# Ordem de subida em produção (ver README_DEPLOY.md):
#   espera o Postgres  ->  alembic upgrade head  ->  usuários iniciais  ->  uvicorn
set -euo pipefail

echo "[entrypoint] Aguardando o banco de dados ficar disponível..."
# Espera ativa e simples pela conexão, usando o próprio SQLAlchemy/engine do app.
# Evita depender de pg_isready no container. Tenta por até ~60s.
python - <<'PY'
import time
import sys
from sqlalchemy import text
from database import engine

for tentativa in range(1, 31):
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print(f"[entrypoint] Banco disponível (tentativa {tentativa}).")
        sys.exit(0)
    except Exception as exc:  # noqa: BLE001
        print(f"[entrypoint] Banco ainda indisponível ({tentativa}/30): {exc}")
        time.sleep(2)

print("[entrypoint] Timeout aguardando o banco.", file=sys.stderr)
sys.exit(1)
PY

echo "[entrypoint] Aplicando migrations (alembic upgrade head)..."
alembic upgrade head

# Criação idempotente dos usuários iniciais da diretoria (MVP).
# Pode ser desativada definindo SKIP_CREATE_ADMIN=1.
if [ "${SKIP_CREATE_ADMIN:-0}" != "1" ]; then
  echo "[entrypoint] Garantindo usuários iniciais (create_admin.py)..."
  python create_admin.py || echo "[entrypoint] create_admin.py falhou (seguindo mesmo assim)."
fi

echo "[entrypoint] Subindo a API (uvicorn)..."
exec uvicorn main:app --host 0.0.0.0 --port 8000 --proxy-headers
