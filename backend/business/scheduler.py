"""
Agendador da Trava Automática de Inadimplência — SGI-YKR (Tarefa 13 / Requisito 10).

Evolução planejada no steering `regras-negocio-ykr.md` (seção 1.2): sair da
avaliação sob demanda (lazy) e passar a varrer o banco proativamente, uma vez
por dia, de madrugada.

Este módulo faz exatamente isso:
- `varrer_travas_inadimplencia()`: abre uma sessão própria (roda fora do ciclo
  de request, então NÃO usa `Depends(get_db)`), percorre todos os contratos de
  plano `Mensalidade` e delega cada avaliação à função única
  `avaliar_trava_inadimplencia` (business/trava.py). Um único commit ao final.
- `iniciar_agendador()` / `parar_agendador()`: sobem e derrubam um
  `BackgroundScheduler` do APScheduler. Ele roda em uma thread separada, então
  não bloqueia a inicialização da API nem o event loop do FastAPI.

Princípio de robustez (Requisito: "não travar a inicialização da API"): qualquer
falha ao configurar ou executar o job é capturada e apenas logada. A API sobe e
serve requisições mesmo que o agendador falhe — a avaliação lazy nas rotas
(`obter_progresso`, `editar_contrato`) continua sendo a rede de segurança.
"""

from __future__ import annotations

import logging
import os
from datetime import date

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from database import SessionLocal
from models import Aluno, Contrato
from business.trava import avaliar_trava_inadimplencia

logger = logging.getLogger("ynk.scheduler")

# Horário do job diário (madrugada). Configurável por ambiente para não exigir
# alteração de código entre dev e produção; padrão: 00:00.
_HORA_JOB = int(os.getenv("TRAVA_JOB_HORA", "0"))
_MINUTO_JOB = int(os.getenv("TRAVA_JOB_MINUTO", "0"))

# ID fixo do job: evita duplicação caso o startup rode mais de uma vez.
_JOB_ID = "trava_inadimplencia_diaria"

# Instância única do agendador neste processo.
_scheduler: BackgroundScheduler | None = None


def varrer_travas_inadimplencia() -> int:
    """Varre todos os contratos de Mensalidade e aplica/reverte a trava.

    Abre e fecha a própria sessão (não recebe `db` porque roda fora do request).
    Faz um único commit ao final. Retorna quantos alunos ficaram em atraso
    crítico (para fins de log/observabilidade).

    Returns:
        int: quantidade de alunos avaliados como em atraso crítico.
    """
    db = SessionLocal()
    try:
        hoje = date.today()
        # Só o plano Mensalidade sofre trava; filtramos já na query para não
        # carregar contratos irrelevantes. A função ainda revalida o plano.
        contratos = (
            db.query(Contrato)
            .filter(Contrato.modelo_plano == "Mensalidade")
            .all()
        )

        avaliados = 0
        em_atraso = 0
        for contrato in contratos:
            aluno = (
                db.query(Aluno)
                .filter(Aluno.id_matricula == contrato.id_aluno)
                .first()
            )
            if aluno is None:
                # Contrato órfão (sem aluno): ignora com segurança.
                continue
            avaliados += 1
            if avaliar_trava_inadimplencia(db, aluno, contrato, hoje):
                em_atraso += 1

        db.commit()
        logger.info(
            "Varredura de trava concluída: %d contratos Mensalidade avaliados, "
            "%d em atraso crítico.",
            avaliados,
            em_atraso,
        )
        return em_atraso
    except Exception:  # noqa: BLE001 — job de background: nunca deve derrubar a app.
        db.rollback()
        logger.exception("Falha ao executar a varredura de trava de inadimplência.")
        return 0
    finally:
        db.close()


def iniciar_agendador() -> None:
    """Sobe o BackgroundScheduler e agenda a varredura diária de madrugada.

    Idempotente e defensivo: se já houver um agendador rodando, não cria outro;
    e qualquer erro de configuração é logado sem propagar, para NÃO travar a
    inicialização da API.
    """
    global _scheduler

    if _scheduler is not None and _scheduler.running:
        logger.info("Agendador já está em execução; ignorando novo start.")
        return

    try:
        scheduler = BackgroundScheduler(timezone="America/Sao_Paulo")
        scheduler.add_job(
            varrer_travas_inadimplencia,
            trigger=CronTrigger(hour=_HORA_JOB, minute=_MINUTO_JOB),
            id=_JOB_ID,
            name="Trava de inadimplência (varredura diária)",
            replace_existing=True,
            # Se a app ficou fora do ar no horário do job, roda uma vez ao voltar
            # (dentro da janela de 1h), em vez de acumular execuções perdidas.
            misfire_grace_time=3600,
            coalesce=True,
            max_instances=1,
        )
        scheduler.start()
        _scheduler = scheduler
        logger.info(
            "Agendador da trava iniciado. Job diário às %02d:%02d "
            "(America/Sao_Paulo).",
            _HORA_JOB,
            _MINUTO_JOB,
        )
    except Exception:  # noqa: BLE001 — não travar a inicialização da API.
        logger.exception(
            "Não foi possível iniciar o agendador da trava. A API seguirá "
            "funcionando com a avaliação sob demanda (lazy) nas rotas."
        )


def parar_agendador() -> None:
    """Derruba o agendador no shutdown da API, se estiver ativo."""
    global _scheduler

    if _scheduler is None:
        return
    try:
        if _scheduler.running:
            _scheduler.shutdown(wait=False)
            logger.info("Agendador da trava encerrado.")
    except Exception:  # noqa: BLE001
        logger.exception("Falha ao encerrar o agendador da trava.")
    finally:
        _scheduler = None
