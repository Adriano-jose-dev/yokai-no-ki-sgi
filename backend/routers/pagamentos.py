"""
Rotas de domínio Pagamentos — SGI-YKR.

Recebimento de pagamento com quitação em cascata (taxa de admissão primeiro,
depois sessões pendentes por ordem cronológica). Comportamento idêntico ao
monolito original.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from models import Contrato, Sessao, Pagamento, Usuario
from schemas import ReceberPagamentoRequest
from business.auth import requer_papel, get_usuario_atual
from business import auditoria

router = APIRouter(
    tags=["Pagamentos"], dependencies=[Depends(requer_papel("admin"))]
)


@router.post(
    "/pagamentos/receber",
    summary="Registrar pagamento com quitação em cascata",
    description=(
        "Lança um pagamento e o aplica em cascata:\n\n"
        "1. Abate primeiro a **taxa de admissão** pendente.\n"
        "2. Em seguida, quita as **sessões pendentes** em ordem cronológica "
        "(mais antigas primeiro), marcando-as como pagas.\n\n"
        "Qualquer sobra retorna em `troco_em_credito`."
    ),
)
def receber_pagamento(
    req: ReceberPagamentoRequest,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_atual),
):
    db.add(
        Pagamento(id_aluno=req.id_matricula, valor=req.valor_pago, metodo=req.metodo)
    )
    auditoria.registrar(
        db,
        acao="receber_pagamento",
        autor=usuario.username,
        id_aluno=req.id_matricula,
        descricao=f"Pagamento recebido: R$ {req.valor_pago:.2f} ({req.metodo}).",
        detalhes={"valor": req.valor_pago, "metodo": req.metodo},
    )
    saldo = req.valor_pago
    contrato = db.query(Contrato).filter(Contrato.id_aluno == req.id_matricula).first()
    if contrato and contrato.taxa_admissao_saldo > 0 and saldo > 0:
        if saldo >= contrato.taxa_admissao_saldo:
            saldo -= contrato.taxa_admissao_saldo
            contrato.taxa_admissao_saldo = 0.0
        else:
            contrato.taxa_admissao_saldo -= saldo
            saldo = 0.0
    if saldo > 0:
        for s in (
            db.query(Sessao)
            .filter(
                Sessao.id_aluno == req.id_matricula,
                Sessao.pago == False,
                Sessao.hora_saida != None,
            )
            .order_by(Sessao.hora_entrada.asc())
            .all()
        ):
            if saldo >= s.valor_apurado:
                saldo -= s.valor_apurado
                s.pago = True
            else:
                s.valor_apurado -= saldo
                saldo = 0.0
                break
    db.commit()
    return {"status": "sucesso", "troco_em_credito": saldo}
