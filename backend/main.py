"""
Ponto de entrada da API — SGI-YKR.

Após a modularização (Tarefa 7), este arquivo apenas monta o app FastAPI,
configura o CORS, cria as tabelas e inclui os routers por domínio. A lógica de
negócio vive em `models.py`, `schemas.py`, `business/` e `routers/`.

Reexporta símbolos-chave (`app`, `Base`, `get_db`, models e schemas) para manter
compatibilidade com os testes e com imports existentes (`from main import ...`).
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import config

# --- Infra e domínio (reexportados para compatibilidade) ---
from database import DATABASE_URL, engine, SessionLocal, Base, get_db  # noqa: F401
from models import (  # noqa: F401
    Aluno,
    Contrato,
    Sessao,
    Pagamento,
    Presenca,
    Usuario,
    EncerramentoMatricula,
)
from schemas import (  # noqa: F401
    SessaoRequest,
    StopSessaoRequest,
    NovoAlunoRequest,
    EditarFichaRequest,
    EditarContratoRequest,
    ChamadaRequest,
    ListarChamadaRequest,
    PresencaItem,
    PresencaBulkRequest,
    ReceberPagamentoRequest,
    PromoverRequest,
    StatusRequest,
    UpdateNotaRequest,
    AtualizarValorBaseRequest,
    LoginRequest,
    TokenResponse,
)
from business.helpers import formata_hora, encerrar_sessao_aberta  # noqa: F401
from business.trava import avaliar_trava_inadimplencia  # noqa: F401

from routers import alunos, tatame, presenca, pagamentos, auth, encerramento

# Evolução do esquema (Requisito 9.4): em PRODUÇÃO o esquema é gerido por
# migrations do Alembic (`alembic upgrade head`), NÃO por create_all. Mantemos o
# create_all apenas como conveniência de desenvolvimento local com SQLite, para
# não exigir rodar o Alembic só para experimentar a API.
if config.is_sqlite():
    Base.metadata.create_all(bind=engine)

# --- Ciclo de vida da aplicação (Tarefa 13 / Requisito 10) ---
# Usa o padrão `lifespan` do FastAPI (recomendado; substitui os on_event
# deprecados). No startup, sobe o BackgroundScheduler que varre o banco
# diariamente de madrugada e aplica a trava de inadimplência de forma proativa.
# No shutdown, derruba o agendador. Cada etapa é envolvida em try/except para
# que NENHUMA falha do agendador impeça a API de iniciar ou encerrar — a
# avaliação sob demanda (lazy) nas rotas permanece como rede de segurança.
@asynccontextmanager
async def lifespan(_app: FastAPI):
    try:
        from business.scheduler import iniciar_agendador

        iniciar_agendador()
    except Exception:  # noqa: BLE001 — jamais travar a inicialização da API.
        logging.getLogger("ynk.scheduler").exception(
            "Falha ao iniciar o agendador no startup; API segue no modo lazy."
        )

    yield  # aplicação em execução

    try:
        from business.scheduler import parar_agendador

        parar_agendador()
    except Exception:  # noqa: BLE001
        logging.getLogger("ynk.scheduler").exception(
            "Falha ao encerrar o agendador no shutdown."
        )


# --- Metadados da documentação OpenAPI/Swagger (Tarefa 15 / Requisito 12) ---
# Título, descrição e versão aparecem no topo do /docs; as tags agrupam os
# endpoints por domínio e recebem uma descrição curta cada uma.
DESCRICAO_API = """
API interna do **Dojo Yōkai no Ki Ryūha** (Kenjutsu / Bujutsu tradicional).

Cobre a operação diária da escola: matrícula e secretaria, controle de tatame
com cálculo de custo por sessão, chamada de presença, recebimento de pagamentos
e autenticação da diretoria.

**Regras de negócio embarcadas** (ver detalhe em cada endpoint):
- **Hierarquia de cobrança por sessão**: hora flexível, franquia de 3h da
  Mensalidade, acréscimo de 50% no Intensivão e Horas Livres.
- **Trava automática de inadimplência**: aplica-se ao plano Mensalidade após
  5 dias de atraso; `[ACORDO]` na observação financeira faz bypass.
- **Soft delete**: alunos nunca são removidos do banco (status → `Inativo`).

Todas as rotas de domínio exigem autenticação **Bearer** (JWT), obtida em
`POST /auth/login`.
"""

TAGS_METADATA = [
    {
        "name": "Autenticação",
        "description": (
            "Login da diretoria e emissão de token JWT (papel `admin`). "
            "O token deve ser enviado no header `Authorization: Bearer <token>`."
        ),
    },
    {
        "name": "Alunos & Secretaria",
        "description": (
            "Matrícula, edição de ficha e contrato, valor base, progressão "
            "marcial, trava/destrava de inadimplência e soft delete."
        ),
    },
    {
        "name": "Tatame",
        "description": (
            "Alunos disponíveis para treino e cronômetro de sessão. O "
            "encerramento calcula o custo pela hierarquia de cobrança e "
            "registra presença automática."
        ),
    },
    {
        "name": "Presença",
        "description": (
            "Chamada diária (omite alunos `Inativo`) e registro de presença "
            "em lote."
        ),
    },
    {
        "name": "Pagamentos",
        "description": (
            "Recebimento com quitação em cascata: taxa de admissão primeiro, "
            "depois sessões pendentes em ordem cronológica."
        ),
    },
    {
        "name": "Encerramento de Matrícula",
        "description": (
            "Encerramento definitivo de vínculo: gera dossiê PDF, retém por 30 "
            "dias (com download e revogação) e expurga o registro do aluno ao "
            "fim da janela (Hard Delete / LGPD)."
        ),
    },
]

app = FastAPI(
    title="SGI-YKR — Sistema de Gestão Interna Yōkai no Ki Ryūha",
    description=DESCRICAO_API,
    version="1.0.0",
    openapi_tags=TAGS_METADATA,
    contact={"name": "Diretoria — Yōkai no Ki Ryūha"},
)
# CORS restrito por configuração (Requisito 7): as origens vêm de config.CORS_ORIGINS,
# alimentado pela variável de ambiente CORS_ORIGINS. Em dev, o padrão inclui a
# origem local do Angular (http://localhost:4200). Sem mais "*" fixo.
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(alunos.router)
app.include_router(tatame.router)
app.include_router(presenca.router)
app.include_router(pagamentos.router)
app.include_router(encerramento.router)
