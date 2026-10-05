"""
Rotas de Ocorrências de Aula / Calendário — SGI-YKR (Fase 1b).

Uma **ocorrência** é uma turma numa data. São geradas a partir da recorrência
(RRULE) da turma e totalmente editáveis pelo admin: mover de data, cancelar,
excluir ou criar avulsas.

- **Adicionar** ocorrência (gerar/avulsa) — ambiente Tatame/Calendário.
- **Modificar** (ver/editar/excluir/cancelar) — ambiente Calendário.

O financeiro (Fase 2) somará as horas das ocorrências `prevista`/`realizada`
(descartando `cancelada`). Todas as rotas exigem admin.
"""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from database import get_db
from models import Turma, OcorrenciaAula, TurmaMatricula, Aluno, Presenca
from schemas import (
    GerarOcorrenciasRequest,
    NovaOcorrenciaAvulsaRequest,
    EditarOcorrenciaRequest,
    PresencaOcorrenciaRequest,
    DuracaoRealRequest,
)
from business.auth import requer_papel
from business.ocorrencias import gerar_ocorrencias, duracao_prevista_horas

router = APIRouter(
    tags=["Calendário / Ocorrências"],
    dependencies=[Depends(requer_papel("admin"))],
)

ESTADOS_VALIDOS = ("prevista", "realizada", "cancelada")


def _ocorrencia_dict(db: Session, oc: OcorrenciaAula) -> dict:
    turma = db.query(Turma).filter(Turma.id == oc.id_turma).first()
    return {
        "id": oc.id,
        "id_turma": oc.id_turma,
        "turma_nome": turma.nome if turma else "(turma removida)",
        "tipo_pagamento": turma.tipo_pagamento if turma else None,
        "classe": turma.classe if turma else None,
        "data": oc.data.isoformat(),
        "hora_inicio": oc.hora_inicio,
        "hora_fim": oc.hora_fim,
        "estado": oc.estado,
        "origem": oc.origem,
        "observacao": oc.observacao,
        "duracao_prevista_horas": duracao_prevista_horas(oc),
        "duracao_real_min": oc.duracao_real_min,
    }


@router.post(
    "/turmas/{id_turma}/ocorrencias/gerar",
    summary="Gerar ocorrências da recorrência da turma num intervalo",
    description=(
        "Expande a RRULE da turma no intervalo informado e cria as ocorrências "
        "que ainda não existem (idempotente — não duplica)."
    ),
)
def gerar(
    id_turma: int, req: GerarOcorrenciasRequest, db: Session = Depends(get_db)
):
    turma = db.query(Turma).filter(Turma.id == id_turma).first()
    if not turma:
        raise HTTPException(status_code=404, detail="Turma não encontrada")
    if req.data_fim < req.data_inicio:
        raise HTTPException(status_code=400, detail="Intervalo de datas inválido")

    novas = gerar_ocorrencias(db, turma, req.data_inicio, req.data_fim)
    db.commit()
    return {"geradas": len(novas), "turma": turma.nome}


@router.get(
    "/ocorrencias",
    summary="Listar ocorrências num período",
    description="Lista as ocorrências entre `inicio` e `fim` (para o calendário).",
)
def listar(
    inicio: date = Query(...),
    fim: date = Query(...),
    db: Session = Depends(get_db),
):
    ocs = (
        db.query(OcorrenciaAula)
        .filter(OcorrenciaAula.data >= inicio, OcorrenciaAula.data <= fim)
        .order_by(OcorrenciaAula.data.asc())
        .all()
    )
    return [_ocorrencia_dict(db, o) for o in ocs]


@router.get(
    "/calendario/dia/{dia}",
    summary="Detalhe de um dia (ocorrências, participantes e duração)",
    description=(
        "Retorna as ocorrências do dia com os alunos da turma e a duração "
        "prevista/real — base da visão 'quem participou e quanto tempo durou'."
    ),
)
def detalhe_dia(dia: date, db: Session = Depends(get_db)):
    ocs = (
        db.query(OcorrenciaAula)
        .filter(OcorrenciaAula.data == dia)
        .all()
    )
    resultado = []
    for o in ocs:
        info = _ocorrencia_dict(db, o)
        vinculos = (
            db.query(TurmaMatricula)
            .filter(TurmaMatricula.id_turma == o.id_turma)
            .all()
        )
        participantes = []
        for v in vinculos:
            aluno = db.query(Aluno).filter(Aluno.id_matricula == v.id_aluno).first()
            participantes.append(
                {
                    "id_aluno": v.id_aluno,
                    "nome": aluno.nome if aluno else "(removido)",
                    "papel": v.papel,
                }
            )
        info["participantes"] = participantes
        resultado.append(info)
    return resultado


@router.post(
    "/ocorrencias/avulsa",
    summary="Criar ocorrência avulsa",
    description="Cria uma aula fora da recorrência (ex.: remarcação de hora-aula).",
)
def criar_avulsa(req: NovaOcorrenciaAvulsaRequest, db: Session = Depends(get_db)):
    turma = db.query(Turma).filter(Turma.id == req.id_turma).first()
    if not turma:
        raise HTTPException(status_code=404, detail="Turma não encontrada")
    oc = OcorrenciaAula(
        id_turma=req.id_turma,
        data=req.data,
        hora_inicio=req.hora_inicio or turma.hora_inicio,
        hora_fim=req.hora_fim or turma.hora_fim,
        estado="prevista",
        origem="avulsa",
        observacao=req.observacao,
    )
    db.add(oc)
    db.commit()
    db.refresh(oc)
    return _ocorrencia_dict(db, oc)


@router.put(
    "/ocorrencias/{id_ocorrencia}",
    summary="Editar ocorrência (mover data, mudar estado, etc.)",
)
def editar(
    id_ocorrencia: int, req: EditarOcorrenciaRequest, db: Session = Depends(get_db)
):
    oc = db.query(OcorrenciaAula).filter(OcorrenciaAula.id == id_ocorrencia).first()
    if not oc:
        raise HTTPException(status_code=404, detail="Ocorrência não encontrada")
    if req.estado is not None and req.estado not in ESTADOS_VALIDOS:
        raise HTTPException(
            status_code=400, detail=f"estado inválido. Use um de: {ESTADOS_VALIDOS}."
        )
    for campo in (
        "data",
        "hora_inicio",
        "hora_fim",
        "estado",
        "observacao",
        "duracao_real_min",
    ):
        valor = getattr(req, campo)
        if valor is not None:
            setattr(oc, campo, valor)
    db.commit()
    db.refresh(oc)
    return _ocorrencia_dict(db, oc)


@router.post(
    "/ocorrencias/{id_ocorrencia}/cancelar",
    summary="Cancelar ocorrência (sai do cálculo financeiro)",
    description=(
        "Marca a ocorrência como `cancelada`. Para turmas de Mensalidade, isso "
        "remove as horas da aula do cálculo do mês (Fase 2)."
    ),
)
def cancelar(id_ocorrencia: int, db: Session = Depends(get_db)):
    oc = db.query(OcorrenciaAula).filter(OcorrenciaAula.id == id_ocorrencia).first()
    if not oc:
        raise HTTPException(status_code=404, detail="Ocorrência não encontrada")
    oc.estado = "cancelada"
    db.commit()
    return {"status": "Ocorrência cancelada", "id": id_ocorrencia}


@router.post(
    "/ocorrencias/{id_ocorrencia}/presenca",
    summary="Marcar presença/ausência de aluno (Modo Tatame Mensalidade)",
    description=(
        "Registra presença ou ausência de um aluno na ocorrência (turma de "
        "Mensalidade: cronômetro global + botão por aluno). Grava na tabela de "
        "presenças (upsert por aluno+data) e marca a ocorrência como "
        "`realizada`."
    ),
)
def marcar_presenca(
    id_ocorrencia: int,
    req: PresencaOcorrenciaRequest,
    db: Session = Depends(get_db),
):
    oc = db.query(OcorrenciaAula).filter(OcorrenciaAula.id == id_ocorrencia).first()
    if not oc:
        raise HTTPException(status_code=404, detail="Ocorrência não encontrada")
    aluno = db.query(Aluno).filter(Aluno.id_matricula == req.id_aluno).first()
    if not aluno:
        raise HTTPException(status_code=404, detail="Aluno não encontrado")

    status = "Presente" if req.presente else "Ausente"
    registro = (
        db.query(Presenca)
        .filter(Presenca.id_aluno == req.id_aluno, Presenca.data == oc.data)
        .first()
    )
    if registro:
        registro.status = status
    else:
        db.add(Presenca(id_aluno=req.id_aluno, data=oc.data, status=status))

    # A ocorrência passa a 'realizada' assim que a chamada começa a ser feita.
    if oc.estado == "prevista":
        oc.estado = "realizada"

    db.commit()
    return {"status": f"Presença registrada: {status}", "aluno": req.id_aluno}


@router.put(
    "/ocorrencias/{id_ocorrencia}/duracao",
    summary="Registrar duração real da aula (cronômetro global)",
    description=(
        "Grava a duração real cronometrada da ocorrência. É validação do "
        "professor — NÃO entra no cálculo financeiro da mensalidade (que usa as "
        "horas previstas do calendário)."
    ),
)
def registrar_duracao(
    id_ocorrencia: int, req: DuracaoRealRequest, db: Session = Depends(get_db)
):
    oc = db.query(OcorrenciaAula).filter(OcorrenciaAula.id == id_ocorrencia).first()
    if not oc:
        raise HTTPException(status_code=404, detail="Ocorrência não encontrada")
    oc.duracao_real_min = req.duracao_real_min
    if oc.estado == "prevista":
        oc.estado = "realizada"
    db.commit()
    return {"status": "Duração registrada", "duracao_real_min": req.duracao_real_min}


@router.delete(
    "/ocorrencias/{id_ocorrencia}", summary="Excluir ocorrência"
)
def excluir(id_ocorrencia: int, db: Session = Depends(get_db)):
    oc = db.query(OcorrenciaAula).filter(OcorrenciaAula.id == id_ocorrencia).first()
    if not oc:
        raise HTTPException(status_code=404, detail="Ocorrência não encontrada")
    db.delete(oc)
    db.commit()
    return {"status": "Ocorrência excluída", "id": id_ocorrencia}
