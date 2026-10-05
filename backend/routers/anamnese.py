"""
Rotas de domínio Anamnese — Prontuário médico versionado (Fase 3) — SGI-YKR.

Expõe a anamnese versionada e o card de alerta crítico do perfil:

- `POST /anamnese/{id_aluno}` — registra uma NOVA versão (desativa a anterior,
  calcula a validade e sincroniza a `restricao_medica` legada do aluno).
- `GET  /anamnese/{id_aluno}` — anamnese ativa + card de alerta crítico + status
  de validade (o que o perfil destaca).
- `GET  /anamnese/{id_aluno}/historico` — todas as versões (histórico que não
  some).

A régua de criticidade, o cálculo de validade e a montagem do card ficam em
`business/anamnese.py`; aqui só orquestramos e fazemos o commit.
"""

import json
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import Aluno, Anamnese, Usuario
from schemas import SalvarAnamneseRequest
from business.auth import requer_papel, get_usuario_atual
from business import anamnese as svc
from business import auditoria

router = APIRouter(
    tags=["Anamnese"], dependencies=[Depends(requer_papel("admin"))]
)


def _exigir_aluno(db: Session, id_aluno: str) -> Aluno:
    aluno = db.query(Aluno).filter(Aluno.id_matricula == id_aluno).first()
    if not aluno:
        raise HTTPException(status_code=404, detail="Aluno não encontrado")
    return aluno


def _anamnese_ativa(db: Session, id_aluno: str) -> Anamnese | None:
    return (
        db.query(Anamnese)
        .filter(Anamnese.id_aluno == id_aluno, Anamnese.ativa == True)  # noqa: E712
        .first()
    )


def _versao_dict(a: Anamnese) -> dict:
    return {
        "id": a.id,
        "versao": a.versao,
        "ativa": a.ativa,
        "data_preenchimento": a.data_preenchimento.isoformat(),
        "validade_meses": a.validade_meses,
        "data_validade": a.data_validade.isoformat() if a.data_validade else None,
        "respostas": svc._carregar_respostas(a.respostas_json),
        "observacao": a.observacao,
        "autor": a.autor,
    }


@router.post(
    "/anamnese/{id_aluno}",
    summary="Registrar nova versão da anamnese",
    description=(
        "Cria uma **nova versão** da anamnese: desativa a versão anterior (vira "
        "histórico), incrementa `versao`, calcula `data_validade` "
        "(`preenchimento + validade_meses`) e extrai as **condições críticas** "
        "para o card de alerta. Também sincroniza a `restricao_medica` legada "
        "do aluno. `validade_meses` deve ser **6** ou **12**."
    ),
)
def salvar_anamnese(
    id_aluno: str,
    req: SalvarAnamneseRequest,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_atual),
):
    aluno = _exigir_aluno(db, id_aluno)
    if req.validade_meses not in (6, 12):
        raise HTTPException(
            status_code=400, detail="validade_meses deve ser 6 ou 12."
        )

    hoje = date.today()
    anterior = _anamnese_ativa(db, id_aluno)
    nova_versao = (anterior.versao + 1) if anterior else 1
    if anterior:
        anterior.ativa = False

    criticas = svc.extrair_condicoes_criticas(req.respostas)
    nova = Anamnese(
        id_aluno=id_aluno,
        versao=nova_versao,
        ativa=True,
        data_preenchimento=hoje,
        validade_meses=req.validade_meses,
        data_validade=svc.calcular_validade(hoje, req.validade_meses),
        respostas_json=json.dumps(req.respostas or {}),
        condicoes_criticas_json=json.dumps(criticas),
        observacao=req.observacao,
        contato_emergencia_nome=(
            req.contato_emergencia_nome or aluno.contato_emergencia_nome
        ),
        contato_emergencia_parentesco=(
            req.contato_emergencia_parentesco or aluno.contato_emergencia_parentesco
        ),
        contato_emergencia_telefone=(
            req.contato_emergencia_telefone or aluno.contato_emergencia_telefone
        ),
        autor=usuario.username,
    )
    db.add(nova)

    # Sincroniza a string legada para não quebrar telas/parsers antigos.
    aluno.restricao_medica = svc.serializar_restricao_legada(
        req.respostas, req.observacao
    )

    auditoria.registrar(
        db,
        acao="salvar_anamnese",
        autor=usuario.username,
        id_aluno=id_aluno,
        descricao=f"Anamnese registrada (v{nova_versao}).",
    )

    db.commit()
    db.refresh(nova)
    return {
        "status": "Anamnese registrada",
        "versao": nova.versao,
        "data_validade": nova.data_validade.isoformat(),
        "card_alerta": svc.montar_card_alerta(nova, hoje),
    }


@router.get(
    "/anamnese/{id_aluno}",
    summary="Anamnese ativa + card de alerta crítico",
    description=(
        "Retorna a versão **ativa** da anamnese e o **card de alerta crítico** "
        "(condições que interferem na aula + contatos de emergência + status de "
        "validade: `ok`, `vence_em_breve` ou `vencida`). Se o aluno ainda não "
        "tem anamnese, `card_alerta` é `null`."
    ),
)
def obter_anamnese(id_aluno: str, db: Session = Depends(get_db)):
    _exigir_aluno(db, id_aluno)
    ativa = _anamnese_ativa(db, id_aluno)
    hoje = date.today()
    return {
        "id_aluno": id_aluno,
        "ativa": _versao_dict(ativa) if ativa else None,
        "card_alerta": svc.montar_card_alerta(ativa, hoje),
    }


@router.get(
    "/anamnese/{id_aluno}/historico",
    summary="Histórico de versões da anamnese",
    description=(
        "Lista **todas** as versões da anamnese do aluno (mais recente "
        "primeiro). As versões anteriores não somem — viram histórico."
    ),
)
def historico_anamnese(id_aluno: str, db: Session = Depends(get_db)):
    _exigir_aluno(db, id_aluno)
    versoes = (
        db.query(Anamnese)
        .filter(Anamnese.id_aluno == id_aluno)
        .order_by(Anamnese.versao.desc())
        .all()
    )
    return [_versao_dict(a) for a in versoes]
