"""
Rotas de domínio Financeiro — Conta Corrente (Fase 2 do roadmap) — SGI-YKR.

Expõe a conta corrente do aluno (débito × crédito) e as automações da Fase 2:

- `GET  /financeiro/{id}/conta` — saldo (valores em aberto × crédito) + extrato.
- `GET  /financeiro/{id}/mensalidade/previsao` — prévia do cálculo pelo
  calendário (sem gerar débito).
- `POST /financeiro/{id}/mensalidade/gerar` — materializa o débito da
  mensalidade do mês no vencimento (idempotente; reflete cancelamentos).
- `POST /financeiro/{id}/pagar` — lança um crédito e abate os débitos abertos.
- `POST /financeiro/abono` — abono de falta justificada (somente mensalistas;
  NÃO altera o valor da mensalidade).

A aritmética fica em `business/financeiro.py`; aqui só orquestramos e fazemos o
commit da transação.
"""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import Aluno, Contrato, AbonoFalta, Usuario
from schemas import (
    GerarMensalidadeRequest,
    PagamentoContaRequest,
    AbonoFaltaRequest,
)
from business.auth import requer_papel, get_usuario_atual
from business import financeiro as fin
from business import auditoria

router = APIRouter(
    tags=["Financeiro"], dependencies=[Depends(requer_papel("admin"))]
)


def _exigir_aluno(db: Session, id_aluno: str) -> Aluno:
    aluno = db.query(Aluno).filter(Aluno.id_matricula == id_aluno).first()
    if not aluno:
        raise HTTPException(status_code=404, detail="Aluno não encontrado")
    return aluno


@router.get(
    "/financeiro/{id_aluno}/conta",
    summary="Conta corrente do aluno (saldo e extrato)",
    description=(
        "Retorna os **valores em aberto** (soma dos débitos não quitados), o "
        "**crédito disponível** (saldo pago a mais) e o **extrato** completo de "
        "lançamentos (débitos e créditos)."
    ),
)
def obter_conta(id_aluno: str, db: Session = Depends(get_db)):
    _exigir_aluno(db, id_aluno)
    return fin.resumo_conta_corrente(db, id_aluno)


@router.get(
    "/financeiro/{id_aluno}/mensalidade/previsao",
    summary="Prévia da mensalidade pelo calendário (sem gerar débito)",
    description=(
        "Calcula o valor previsto da mensalidade do mês somando "
        "`valor_base × horas previstas` das ocorrências `prevista`/`realizada` "
        "das turmas de Mensalidade do aluno. Aulas `cancelada` saem da conta. "
        "Não cria nenhum lançamento."
    ),
)
def previsao_mensalidade(
    id_aluno: str,
    ano: int | None = None,
    mes: int | None = None,
    db: Session = Depends(get_db),
):
    _exigir_aluno(db, id_aluno)
    hoje = date.today()
    return fin.calcular_mensalidade_prevista(
        db, id_aluno, ano or hoje.year, mes or hoje.month
    )


@router.post(
    "/financeiro/{id_aluno}/mensalidade/gerar",
    summary="Gerar/recalcular o débito da mensalidade do mês",
    description=(
        "Materializa a mensalidade do mês como **débito** na conta corrente, "
        "com `data_vencimento` no `dia_vencimento` do contrato. É "
        "**idempotente**: se já existe mensalidade do mês, recalcula o valor "
        "(refletindo aulas canceladas) preservando o que já foi quitado. "
        "Crédito disponível é abatido na hora."
    ),
)
def gerar_mensalidade(
    id_aluno: str,
    req: GerarMensalidadeRequest,
    db: Session = Depends(get_db),
):
    _exigir_aluno(db, id_aluno)
    hoje = date.today()
    resultado = fin.gerar_mensalidade(
        db, id_aluno, req.ano or hoje.year, req.mes or hoje.month
    )
    db.commit()
    return resultado


@router.post(
    "/financeiro/{id_aluno}/pagar",
    summary="Registrar pagamento na conta corrente",
    description=(
        "Lança um **crédito** de pagamento e o aplica aos débitos abertos "
        "(mais antigos primeiro). Qualquer sobra permanece como crédito "
        "disponível (saldo a favor do aluno)."
    ),
)
def pagar(
    id_aluno: str,
    req: PagamentoContaRequest,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_atual),
):
    _exigir_aluno(db, id_aluno)
    if req.valor <= 0:
        raise HTTPException(status_code=400, detail="Valor deve ser positivo")
    resultado = fin.registrar_pagamento(db, id_aluno, req.valor, req.metodo)
    auditoria.registrar(
        db,
        acao="receber_pagamento",
        autor=usuario.username,
        id_aluno=id_aluno,
        descricao=f"Pagamento na conta corrente: R$ {req.valor:.2f} ({req.metodo}).",
        detalhes={"valor": req.valor, "metodo": req.metodo},
    )
    db.commit()
    return resultado


@router.post(
    "/financeiro/abono",
    summary="Abonar falta justificada (somente mensalistas)",
    description=(
        "Registra um abono de falta para um **mensalista**. É puramente sobre "
        "presença/penalidade — **NÃO altera o valor da mensalidade** (a única "
        "coisa que reduz o valor é o cancelamento de aula pela escola). "
        "Recusa (**400**) alunos que não sejam do plano Mensalidade."
    ),
)
def abonar_falta(
    req: AbonoFaltaRequest,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_atual),
):
    _exigir_aluno(db, req.id_aluno)
    contrato = db.query(Contrato).filter(Contrato.id_aluno == req.id_aluno).first()
    if not contrato or contrato.modelo_plano != "Mensalidade":
        raise HTTPException(
            status_code=400,
            detail="Abono de falta aplica-se somente a mensalistas.",
        )
    abono = AbonoFalta(
        id_aluno=req.id_aluno,
        id_ocorrencia=req.id_ocorrencia,
        justificativa=req.justificativa,
        autor=usuario.username,
    )
    db.add(abono)
    auditoria.registrar(
        db,
        acao="abonar_falta",
        autor=usuario.username,
        id_aluno=req.id_aluno,
        descricao="Falta abonada (mensalista).",
    )
    db.commit()
    db.refresh(abono)
    return {
        "status": "Falta abonada",
        "id": abono.id,
        "id_aluno": abono.id_aluno,
        "autor": abono.autor,
    }
