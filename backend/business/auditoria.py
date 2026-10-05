"""
Domínio Auditoria — Log de segurança (Fase 4 do roadmap) — SGI-YKR.

Fonte da verdade: steering `regras-negocio-ykr.md`, Fase 4.

Concentra a lógica da auditoria (sem FastAPI):

- `registrar`: grava uma entrada no log (sem commit — quem chama commita). A
  categoria é inferida pela ação (ver `ACOES_SENSIVEIS`), salvo quando passada
  explicitamente.
- `aplicar_retencao`: política de retenção da categoria **geral** —
  (1) descarta o que passou de 60 dias e (2) mantém no máximo 50 na fila
  (remove as mais antigas acima disso). As ações **sensíveis** não entram nessa
  poda (ficam isoladas e preservadas).
- `listar`: consulta com filtros por categoria e/ou aluno.

Projetado para NUNCA derrubar a operação: `registrar` é best-effort (um erro de
auditoria não deve impedir a ação de negócio) — o chamador decide se envolve em
try/except, mas aqui mantemos simples e sem efeitos colaterais além do `add`.
"""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta

from sqlalchemy.orm import Session

from models import RegistroAuditoria

# Ações consideradas CRÍTICAS => categoria 'sensivel' (isoladas, sem poda).
ACOES_SENSIVEIS = {
    "apagar_pagamento",
    "receber_pagamento",
    "encerrar_matricula",
    "revogar_encerramento",
    "expurgo_aluno",
    "destrancar_aluno",
    "desativar_aluno",
    "alterar_status",
}

# Retenção da fila geral.
DIAS_RETENCAO = 60
LIMITE_FILA_GERAL = 50


def categoria_de(acao: str) -> str:
    """Infere a categoria pela ação: 'sensivel' se crítica, senão 'geral'."""
    return "sensivel" if acao in ACOES_SENSIVEIS else "geral"


def registrar(
    db: Session,
    acao: str,
    autor: str | None = None,
    id_aluno: str | None = None,
    descricao: str | None = None,
    detalhes: dict | None = None,
    categoria: str | None = None,
) -> RegistroAuditoria:
    """Cria (sem commit) uma entrada de auditoria.

    `categoria` é inferida de `acao` quando não informada. `detalhes` é
    serializado em JSON. O commit é responsabilidade do chamador (a rota).
    """
    registro = RegistroAuditoria(
        categoria=categoria or categoria_de(acao),
        acao=acao,
        id_aluno=id_aluno,
        autor=autor,
        descricao=descricao,
        detalhes_json=json.dumps(detalhes) if detalhes is not None else None,
        criado_em=datetime.now(),
    )
    db.add(registro)
    return registro


def aplicar_retencao(db: Session, hoje: date | None = None) -> int:
    """Aplica a política de retenção da fila **geral**.

    1. Remove entradas 'geral' com mais de `DIAS_RETENCAO` dias.
    2. Mantém no máximo `LIMITE_FILA_GERAL` entradas 'geral' (remove as mais
       antigas que excederem).

    Ações 'sensivel' NÃO são podadas. Retorna quantas entradas foram removidas.
    Não faz commit.
    """
    hoje = hoje or date.today()
    limite_data = datetime.now() - timedelta(days=DIAS_RETENCAO)
    removidas = 0

    gerais = (
        db.query(RegistroAuditoria)
        .filter(RegistroAuditoria.categoria == "geral")
        .order_by(RegistroAuditoria.criado_em.desc())
        .all()
    )

    for idx, reg in enumerate(gerais):
        # Expira por idade OU por exceder o tamanho da fila (mais antigas).
        if reg.criado_em < limite_data or idx >= LIMITE_FILA_GERAL:
            db.delete(reg)
            removidas += 1

    return removidas


def _registro_dict(r: RegistroAuditoria) -> dict:
    return {
        "id": r.id,
        "categoria": r.categoria,
        "acao": r.acao,
        "id_aluno": r.id_aluno,
        "autor": r.autor,
        "descricao": r.descricao,
        "detalhes": json.loads(r.detalhes_json) if r.detalhes_json else None,
        "criado_em": r.criado_em.strftime("%d/%m/%Y %H:%M"),
    }


def listar(
    db: Session,
    categoria: str | None = None,
    id_aluno: str | None = None,
    limite: int = 200,
) -> list[dict]:
    """Lista eventos (mais recentes primeiro), filtrando por categoria/aluno.

    - `categoria='geral'` ou `'sensivel'`: filtra a coluna categoria.
    - `id_aluno`: a visão por aluno — todos os eventos daquele aluno,
      independentemente da categoria.
    """
    q = db.query(RegistroAuditoria)
    if id_aluno:
        q = q.filter(RegistroAuditoria.id_aluno == id_aluno)
    elif categoria in ("geral", "sensivel"):
        q = q.filter(RegistroAuditoria.categoria == categoria)
    registros = q.order_by(RegistroAuditoria.criado_em.desc()).limit(limite).all()
    return [_registro_dict(r) for r in registros]
