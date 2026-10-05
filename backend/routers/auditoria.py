"""
Rotas de domínio Auditoria — Log de segurança (Fase 4) — SGI-YKR.

Aba **exclusiva de administradores** com o histórico de ações sensíveis. Expõe:

- `GET /auditoria` — lista eventos, filtrando por `categoria` (`geral` ou
  `sensivel`). Aplica a **retenção** da fila geral (poda >60 dias e mantém no
  máximo 50) de forma preguiçosa (lazy) na leitura.
- `GET /auditoria/aluno/{id_aluno}` — visão por aluno (todos os eventos do
  aluno, de qualquer categoria).

A gravação dos eventos acontece dentro das rotas de negócio (contrato,
pagamento, encerramento, anamnese, etc.) via `business.auditoria.registrar`.
A categorização, retenção e consulta ficam em `business/auditoria.py`.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from database import get_db
from business.auth import requer_papel
from business import auditoria

router = APIRouter(
    tags=["Auditoria"], dependencies=[Depends(requer_papel("admin"))]
)


@router.get(
    "/auditoria",
    summary="Listar eventos de auditoria (Geral / Sensíveis)",
    description=(
        "Lista os eventos do log, mais recentes primeiro. Use "
        "`categoria=geral` ou `categoria=sensivel` para filtrar. A leitura "
        "aplica a política de **retenção** da fila geral (descarta o que passou "
        "de 60 dias e mantém no máximo 50 entradas)."
    ),
)
def listar_auditoria(
    categoria: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    # Retenção preguiçosa: toda leitura mantém a fila geral enxuta.
    auditoria.aplicar_retencao(db)
    db.commit()
    return auditoria.listar(db, categoria=categoria)


@router.get(
    "/auditoria/aluno/{id_aluno}",
    summary="Histórico de auditoria por aluno",
    description=(
        "Retorna todos os eventos de auditoria relacionados a um aluno "
        "específico (de qualquer categoria), mais recentes primeiro."
    ),
)
def auditoria_por_aluno(id_aluno: str, db: Session = Depends(get_db)):
    return auditoria.listar(db, id_aluno=id_aluno)
