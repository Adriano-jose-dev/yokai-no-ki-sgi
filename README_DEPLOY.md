# Deploy — SGI-YKR (Sistema de Gestão Interna Yōkai no Ki Ryūha)

Guia de subida do zero em produção. A aplicação tem duas partes:

- **Back-end**: API FastAPI (ASGI) em `backend/`.
- **Front-end**: SPA Angular em `frontend/` (build estático servido por um
  servidor web / CDN).

> Siga os passos **na ordem**. O banco precisa existir e as migrations serem
> aplicadas **antes** de subir a API. O front só precisa saber a URL pública da
> API no momento do build.

---

## Pré-requisitos

- Python **3.12**
- Node.js **16+** e npm (para o build do Angular)
- Um servidor **PostgreSQL** acessível (gerenciado ou próprio)
- Acesso a um ambiente onde você consiga definir variáveis de ambiente

---

## 1. Provisionar o banco (PostgreSQL)

1. Crie um banco e um usuário dedicados. Exemplo com `psql`:

   ```sql
   CREATE DATABASE yokai;
   CREATE USER yokai_app WITH PASSWORD 'SENHA_FORTE_AQUI';
   GRANT ALL PRIVILEGES ON DATABASE yokai TO yokai_app;
   ```

2. Anote a string de conexão no formato SQLAlchemy + psycopg2:

   ```
   postgresql+psycopg2://yokai_app:SENHA_FORTE_AQUI@HOST:5432/yokai
   ```

   > Se a senha tiver caracteres especiais (`@ : / ?`), use a versão
   > URL-encoded.

O driver `psycopg2-binary` já está no `requirements.txt`; não é preciso
instalar nada à parte.

---

## 2. Configurar as variáveis de ambiente

Use o `backend/.env.example` como modelo. **Nunca** versione o `.env`
real — defina as variáveis no painel da hospedagem quando possível.

Variáveis **obrigatórias em produção**:

| Variável        | Descrição                                                        |
| --------------- | ---------------------------------------------------------------- |
| `DATABASE_URL`  | Conexão PostgreSQL do passo 1.                                   |
| `JWT_SECRET`    | Segredo forte e aleatório para assinar os tokens (ver abaixo).   |
| `CORS_ORIGINS`  | Origem(ns) exata(s) do front, separadas por vírgula.             |

Opcionais (têm padrão seguro): `JWT_EXPIRE_MIN` (60), `TRAVA_JOB_HORA` (0),
`TRAVA_JOB_MINUTO` (0).

Gere o `JWT_SECRET` (>= 32 bytes):

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

Exemplo de `.env` de produção:

```env
DATABASE_URL=postgresql+psycopg2://yokai_app:SENHA_FORTE@db.interno:5432/yokai
JWT_SECRET=coloque-o-hex-gerado-acima
JWT_EXPIRE_MIN=60
CORS_ORIGINS=https://app.seudominio.com
```

> **CORS**: informe a origem pública EXATA do front (esquema + host + porta),
> sem barra final e sem `*`. Se o CORS estiver errado, o navegador bloqueia as
> chamadas do Angular mesmo com a API no ar.

---

## 3. Instalar dependências e aplicar as migrations

Na pasta do back-end (`backend/`):

```bash
python -m venv venv
# Linux/macOS:
source venv/bin/activate
# Windows (PowerShell):
.\venv\Scripts\Activate.ps1

pip install -r requirements.txt
```

Com as variáveis de ambiente já carregadas (o `.env` no diretório ou definidas
no ambiente), evolua o esquema do banco com o Alembic:

```bash
alembic upgrade head
```

> Em produção o esquema é gerido **exclusivamente** pelo Alembic. Não conte com
> `create_all` (ele só roda no fallback SQLite de desenvolvimento).

Crie os usuários iniciais da diretoria (MVP):

```bash
python create_admin.py
```

> As credenciais iniciais são fixas no script. **Troque as senhas após o
> primeiro acesso.**

---

## 4. Subir o back-end (ASGI)

A API é ASGI; use **uvicorn** (com workers via `--workers`, ou atrás de um
gerenciador de processos / proxy reverso). Comando definitivo de produção:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4 --proxy-headers
```

Notas:

- Execute a partir de `backend/` (é onde `main.py` e o `alembic.ini`
  vivem).
- **Não** use `--reload` em produção (é só para desenvolvimento).
- O agendador da trava de inadimplência sobe junto com a API (job diário de
  madrugada) e é resiliente: se falhar, a API sobe do mesmo jeito e a avaliação
  sob demanda continua funcionando.
- Coloque a API atrás de um proxy reverso (Nginx/Caddy) com HTTPS. Por isso o
  `--proxy-headers`.
- Verifique a saúde acessando a documentação em `/docs`.

Exemplo com Gunicorn gerenciando workers uvicorn (alternativa a `--workers`):

```bash
gunicorn main:app -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000 --workers 4
```

> `gunicorn` não está no `requirements.txt`; instale-o no ambiente se optar por
> essa forma (`pip install gunicorn`).

---

## 5. Build de produção do Angular

Antes do build, ajuste a URL pública da API em
`frontend/src/environments/environment.prod.ts` (campo `apiUrl`). Aponte para a
URL onde a API do passo 4 está publicada, por exemplo:

```ts
export const environment = {
  production: true,
  apiUrl: 'https://api.seudominio.com'
};
```

Na pasta `frontend/`:

```bash
npm ci
npm run build   # equivale a: ng build (usa a configuração de produção)
```

> Se o `npm run build` for bloqueado pela ExecutionPolicy do PowerShell no
> Windows, chame o CLI direto:
> `node node_modules/@angular/cli/bin/ng.js build`.

O resultado estático fica em `frontend/dist/ynk-app/browser/`. Publique o
conteúdo dessa pasta em um servidor estático / CDN (Nginx, S3+CloudFront,
Netlify, etc.).

- Configure o servidor estático para **fallback de SPA**: qualquer rota
  desconhecida deve servir `index.html` (senão o refresh em rotas internas dá
  404).
- Garanta que a origem pública do front seja exatamente a que você colocou em
  `CORS_ORIGINS` no passo 2.

---

## Checklist final

- [ ] PostgreSQL provisionado e acessível
- [ ] `DATABASE_URL`, `JWT_SECRET` (forte) e `CORS_ORIGINS` definidos no ambiente
- [ ] `pip install -r requirements.txt` executado no venv
- [ ] `alembic upgrade head` aplicado sem erros
- [ ] `python create_admin.py` executado (e senhas trocadas no 1º acesso)
- [ ] API no ar via uvicorn/gunicorn atrás de HTTPS; `/docs` acessível
- [ ] `apiUrl` de produção ajustado e `npm run build` gerando `dist/ynk-app/browser/`
- [ ] Front publicado com fallback de SPA e origem batendo com `CORS_ORIGINS`

---

## Subida com Docker (um único comando)

Alternativa aos passos manuais acima: toda a stack (PostgreSQL + API + front)
é orquestrada por `docker compose`. A partir da raiz do projeto:

```bash
docker compose up --build
```

Isso sobe:

- **db**: PostgreSQL 16 com volume persistente e healthcheck.
- **api**: FastAPI. No start, espera o banco, roda `alembic upgrade head`,
  garante os usuários iniciais (`create_admin.py`) e sobe o uvicorn.
- **web**: build de produção do Angular servido por Nginx, que também faz
  **proxy de `/api`** para a API (mesma origem, sem CORS).

Acessos:

- Front: <http://localhost:8080>
- API / Swagger: <http://localhost:8000/docs>

Configuração (opcional): crie um `.env` ao lado do `docker-compose.yml` para
sobrescrever os padrões de desenvolvimento. **Em produção, defina no mínimo um
`JWT_SECRET` forte:**

```env
POSTGRES_USER=yokai_app
POSTGRES_PASSWORD=uma-senha-forte
POSTGRES_DB=yokai
JWT_SECRET=coloque-um-hex-de-32-bytes-aqui
CORS_ORIGINS=http://localhost:8080
```

Encerrar (mantendo os dados): `docker compose down`.
Encerrar e apagar o banco: `docker compose down -v`.

---

## Ordem resumida (TL;DR)

```
Postgres  →  variáveis de ambiente  →  alembic upgrade head  →  create_admin.py
          →  uvicorn main:app (ASGI)  →  build Angular (dist/ynk-app) → publicar
```
