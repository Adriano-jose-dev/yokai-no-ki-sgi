# Dockerfile da API — SGI-YKR (FastAPI / ASGI)
FROM python:3.12-slim

# Boas práticas de runtime Python em container.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Dependências de sistema mínimas. psycopg2-binary traz suas libs, mas mantemos
# libpq e as ferramentas essenciais para robustez do runtime.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Instala as dependências primeiro (camada cacheável) e só depois o código.
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copia o código da API.
COPY . .

# Torna o entrypoint executável (o arquivo é copiado acima).
RUN chmod +x docker-entrypoint.sh

EXPOSE 8000

# Healthcheck: a doc interativa responde 200 quando a API está no ar.
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=5 \
    CMD python -c "import urllib.request,sys; sys.exit(0) if urllib.request.urlopen('http://localhost:8000/docs').status==200 else sys.exit(1)"

ENTRYPOINT ["./docker-entrypoint.sh"]
