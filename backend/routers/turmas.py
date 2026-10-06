"""
Rotas de Turmas — SGI-YKR (Fase 1 do roadmap de evolução).

Uma **Turma** é o molde de uma aula recorrente (nome, tipo de pagamento, classe,
valor base e recorrência). Alunos se associam a uma turma como:
- **matriculado**: vínculo principal, cobrado pela turma;
- **ocorrente**: participa sem ser o vínculo principal (ex.: aluno de Legado
  assistindo Dojo gratuitamente).

Regras desta fase (1a):
- Um aluno pode ter **apenas uma** matrícula principal (papel `matriculado`),
  mas várias participações como `ocorrente`.
- Ocorrente de aluno **Legado** em turma **Dojo** é marcado como gratuito.

As ocorrências de aula (calendário) são da Fase 1b. Todas as rotas exigem admin.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import Turma, TurmaMatricula, Aluno
from schemas import NovaTurmaRequest, EditarTurmaRequest, VincularAlunoTurmaRequest
from business.auth import requer_papel

router = APIRouter(
    tags=["Turmas"], dependencies=[Depends(requer_papel("admin"))]
)

PAPEIS_VALIDOS = ("matriculado", "ocorrente")
TIPOS_PAGAMENTO = ("Mensalidade", "Hora-Aula")
CLASSES = ("Dojo", "Legado")


def _validar_turma(tipo_pagamento: str, classe: str) -> None:
    if tipo_pagamento not in TIPOS_PAGAMENTO:
        raise HTTPException(
            status_code=400,
            detail=f"tipo_pagamento inválido. Use um de: {TIPOS_PAGAMENTO}.",
        )
    if classe not in CLASSES:
        raise HTTPException(
            status_code=400, detail=f"classe inválida. Use um de: {CLASSES}."
        )


def _ocorrente_gratuito(db: Session, id_aluno: str, turma: Turma, papel: str) -> bool:
    """Ocorrente de aluno Legado em turma Dojo é gratuito.

    O "aluno Legado" é identificado por já ser matriculado em alguma turma de
    classe Legado. Participar como ocorrente de uma turma Dojo não gera cobrança.
    """
    if papel != "ocorrente":
        return False
    if turma.classe != "Dojo":
        return False
    eh_legado = (
        db.query(TurmaMatricula)
        .join(Turma, Turma.id == TurmaMatricula.id_turma)
        .filter(
            TurmaMatricula.id_aluno == id_aluno,
            TurmaMatricula.papel == "matriculado",
            Turma.classe == "Legado",
        )
        .first()
        is not None
    )
    return eh_legado


def _vincular(db: Session, turma: Turma, id_aluno: str, papel: str, gratuito: bool):
    aluno = db.query(Aluno).filter(Aluno.id_matricula == id_aluno).first()
    if not aluno:
        raise HTTPException(status_code=404, detail=f"Aluno {id_aluno} não encontrado")
    if papel not in PAPEIS_VALIDOS:
        raise HTTPException(
            status_code=400, detail=f"papel inválido. Use um de: {PAPEIS_VALIDOS}."
        )

    # Um aluno só pode ter UMA matrícula principal (papel 'matriculado').
    if papel == "matriculado":
        ja_matriculado = (
            db.query(TurmaMatricula)
            .filter(
                TurmaMatricula.id_aluno == id_aluno,
                TurmaMatricula.papel == "matriculado",
            )
            .first()
        )
        if ja_matriculado and ja_matriculado.id_turma != turma.id:
            raise HTTPException(
                status_code=400,
                detail="Aluno já é matriculado em outra turma. Um aluno só pode "
                "ter uma matrícula principal (pode ser ocorrente em outras).",
            )

    # Evita duplicar o mesmo vínculo (mesmo aluno + papel + turma).
    existente = (
        db.query(TurmaMatricula)
        .filter(
            TurmaMatricula.id_turma == turma.id,
            TurmaMatricula.id_aluno == id_aluno,
            TurmaMatricula.papel == papel,
        )
        .first()
    )
    if existente:
        return existente

    gratuito_final = gratuito or _ocorrente_gratuito(db, id_aluno, turma, papel)
    vinculo = TurmaMatricula(
        id_turma=turma.id, id_aluno=id_aluno, papel=papel, gratuito=gratuito_final
    )
    db.add(vinculo)
    return vinculo


def _turma_dict(db: Session, turma: Turma) -> dict:
    vinculos = (
        db.query(TurmaMatricula).filter(TurmaMatricula.id_turma == turma.id).all()
    )
    alunos = []
    for v in vinculos:
        aluno = db.query(Aluno).filter(Aluno.id_matricula == v.id_aluno).first()
        alunos.append(
            {
                "id_aluno": v.id_aluno,
                "nome": aluno.nome if aluno else "(aluno removido)",
                "papel": v.papel,
                "gratuito": v.gratuito,
                # Campos de contexto do aluno para o card do Ambiente Tatame
                # reproduzir o visual rico do Modo Tatame original.
                "graduacao_atual": aluno.graduacao_atual if aluno else None,
                "status_atividade": aluno.status_atividade if aluno else None,
                "restricao_medica": aluno.restricao_medica if aluno else None,
                "autorizacao_imagem": aluno.autorizacao_imagem if aluno else False,
            }
        )
    return {
        "id": turma.id,
        "nome": turma.nome,
        "tipo_pagamento": turma.tipo_pagamento,
        "classe": turma.classe,
        "valor_base": turma.valor_base,
        "recorrencia_rrule": turma.recorrencia_rrule,
        "recorrencia_descricao": turma.recorrencia_descricao,
        "hora_inicio": turma.hora_inicio,
        "hora_fim": turma.hora_fim,
        "ativo": turma.ativo,
        "alunos": alunos,
    }


@router.post(
    "/turmas",
    summary="Criar turma",
    description=(
        "Cria uma turma (nome, tipo de pagamento, classe, valor base, "
        "recorrência) e, opcionalmente, já vincula alunos como matriculados ou "
        "ocorrentes. Ocorrente de aluno Legado em turma Dojo fica gratuito."
    ),
)
def criar_turma(req: NovaTurmaRequest, db: Session = Depends(get_db)):
    _validar_turma(req.tipo_pagamento, req.classe)
    turma = Turma(
        nome=req.nome,
        tipo_pagamento=req.tipo_pagamento,
        classe=req.classe,
        valor_base=req.valor_base,
        recorrencia_rrule=req.recorrencia_rrule,
        recorrencia_descricao=req.recorrencia_descricao,
        hora_inicio=req.hora_inicio,
        hora_fim=req.hora_fim,
        ativo=True,
    )
    db.add(turma)
    db.flush()  # garante turma.id para os vínculos

    for item in req.alunos:
        _vincular(db, turma, item.id_aluno, item.papel, item.gratuito)

    db.commit()
    db.refresh(turma)
    return _turma_dict(db, turma)


@router.get("/turmas", summary="Listar turmas")
def listar_turmas(db: Session = Depends(get_db)):
    turmas = db.query(Turma).filter(Turma.ativo == True).all()  # noqa: E712
    return [_turma_dict(db, t) for t in turmas]


@router.get("/turmas/{id_turma}", summary="Detalhar turma (com alunos)")
def obter_turma(id_turma: int, db: Session = Depends(get_db)):
    turma = db.query(Turma).filter(Turma.id == id_turma).first()
    if not turma:
        raise HTTPException(status_code=404, detail="Turma não encontrada")
    return _turma_dict(db, turma)


@router.put("/turmas/{id_turma}", summary="Editar turma")
def editar_turma(
    id_turma: int, req: EditarTurmaRequest, db: Session = Depends(get_db)
):
    turma = db.query(Turma).filter(Turma.id == id_turma).first()
    if not turma:
        raise HTTPException(status_code=404, detail="Turma não encontrada")

    if req.tipo_pagamento is not None or req.classe is not None:
        _validar_turma(
            req.tipo_pagamento or turma.tipo_pagamento,
            req.classe or turma.classe,
        )

    for campo in (
        "nome",
        "tipo_pagamento",
        "classe",
        "valor_base",
        "recorrencia_rrule",
        "recorrencia_descricao",
        "hora_inicio",
        "hora_fim",
        "ativo",
    ):
        valor = getattr(req, campo)
        if valor is not None:
            setattr(turma, campo, valor)

    db.commit()
    db.refresh(turma)
    return _turma_dict(db, turma)


@router.post("/turmas/{id_turma}/alunos", summary="Vincular aluno à turma")
def vincular_aluno(
    id_turma: int, req: VincularAlunoTurmaRequest, db: Session = Depends(get_db)
):
    turma = db.query(Turma).filter(Turma.id == id_turma).first()
    if not turma:
        raise HTTPException(status_code=404, detail="Turma não encontrada")
    _vincular(db, turma, req.id_aluno, req.papel, req.gratuito)
    db.commit()
    return _turma_dict(db, turma)


@router.delete(
    "/turmas/{id_turma}/alunos/{id_aluno}", summary="Desvincular aluno da turma"
)
def desvincular_aluno(id_turma: int, id_aluno: str, db: Session = Depends(get_db)):
    vinculos = (
        db.query(TurmaMatricula)
        .filter(
            TurmaMatricula.id_turma == id_turma, TurmaMatricula.id_aluno == id_aluno
        )
        .all()
    )
    if not vinculos:
        raise HTTPException(status_code=404, detail="Vínculo não encontrado")
    for v in vinculos:
        db.delete(v)
    db.commit()
    return {"status": "Aluno desvinculado da turma"}


@router.delete("/turmas/{id_turma}", summary="Desativar turma (soft)")
def desativar_turma(id_turma: int, db: Session = Depends(get_db)):
    turma = db.query(Turma).filter(Turma.id == id_turma).first()
    if not turma:
        raise HTTPException(status_code=404, detail="Turma não encontrada")
    turma.ativo = False
    db.commit()
    return {"status": "Turma desativada"}
