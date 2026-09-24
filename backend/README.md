# Back-end SGI-YKR

API FastAPI do sistema de gestão do Dojo Yōkai no Ki Ryūha.

## Requisitos

- Python 3.12 (instalado via `winget install Python.Python.3.12`)
- Dependências em `requirements.txt`

## Setup do ambiente

Na pasta `YnkBD/`:

```powershell
# 1. Criar o ambiente virtual
python -m venv venv

# 2. Ativar o venv
.\venv\Scripts\Activate.ps1

# 3. Instalar dependências
pip install -r requirements.txt
```

## Rodar a API (desenvolvimento)

```powershell
.\venv\Scripts\Activate.ps1
uvicorn main:app --reload
```

A API sobe em `http://127.0.0.1:8000`. A documentação interativa fica em
`http://127.0.0.1:8000/docs`.

## Rodar os testes

```powershell
.\venv\Scripts\Activate.ps1
pytest -v
```

### Estrutura de testes

- `conftest.py` — fixtures compartilhadas: banco SQLite em memória isolado por
  teste e um `TestClient` do FastAPI com a dependência `get_db` sobrescrita.
- `test_smoke.py` — testes de sanidade da infraestrutura (listagem vazia e fluxo
  mínimo de matrícula).

Novos testes seguem o padrão `test_*.py` e recebem as fixtures `client` e/ou
`db_session`.
