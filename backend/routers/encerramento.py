"""
Rotas de Encerramento de Matrícula — SGI-YKR.

Distinção fundamental (ver steering, seção de ciclo de vida da matrícula):
- **Suspensão** (soft, reversível): `status_atividade` vira `Inativo`/`Trancado`;
  o vínculo é mantido. Tratada nas rotas de status/soft delete.
- **Encerramento** (definitivo): fim de vínculo. Gera um **dossiê PDF completo**,
  move a matrícula para uma janela de retenção de 30 dias e, ao fim dela, um job
  do APScheduler faz o **Hard Delete** (conformidade com a LGPD).

Durante a janela de 30 dias:
- o dossiê fica disponível para download;
- um admin pode **revogar** o encerramento, restaurando o aluno ao estado
  anterior (nada é apagado até o expurgo, então a revogação é uma restauração
  simples).

Todas as rotas exigem papel `admin`.
"""

from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session

from database import get_db
from models import Aluno, EncerramentoMatricula, Usuario
from business.auth import requer_papel
from business.dossie import gerar_dossie_pdf
from business import auditoria

router = APIRouter(
    tags=["Encerramento de Matrícula"],
    dependencies=[Depends(requer_papel("admin"))],
)

# Dias de retenção do dossiê antes do expurgo definitivo (Hard Delete).
DIAS_RETENCAO = 30

# Status que marca o aluno como encerrado (fora das telas do dia a dia).
STATUS_ENCERRADO = "Encerrado"


@router.post(
    "/alunos/{id_matricula}/encerrar",
    summary="Encerrar matrícula (gera dossiê e agenda expurgo em 30 dias)",
    description=(
        "**Encerramento definitivo** de vínculo (não confundir com suspensão).\n\n"
        "1. Gera o **dossiê PDF completo** do aluno (ficha, graduação, contrato, "
        "sessões, pagamentos e presenças) e o guarda para download.\n"
        "2. Marca o aluno como `Encerrado` (some das telas do dia a dia) e "
        "registra o **estado anterior** para permitir revogação.\n"
        "3. Agenda o **expurgo (Hard Delete)** para daqui a 30 dias.\n\n"
        "Reversível por um admin durante a janela de 30 dias via `/revogar-encerramento`."
    ),
)
def encerrar_matricula(
    id_matricula: str,
    db: Session = Depends(get_db),
    admin: Usuario = Depends(requer_papel("admin")),
):
    aluno = db.query(Aluno).filter(Aluno.id_matricula == id_matricula).first()
    if not aluno:
        raise HTTPException(status_code=404, detail="Aluno não encontrado")

    ja_encerrado = (
        db.query(EncerramentoMatricula)
        .filter(EncerramentoMatricula.id_aluno == id_matricula)
        .first()
    )
    if ja_encerrado:
        raise HTTPException(
            status_code=400, detail="Matrícula já está encerrada."
        )

    # 1. Gera o dossiê ANTES de qualquer alteração de estado (a prova vem primeiro).
    pdf_bytes = gerar_dossie_pdf(db, aluno)
    nome_arquivo = f"dossie_{id_matricula}_{date.today().isoformat()}.pdf"

    # 2. Registra o encerramento guardando o estado anterior (p/ revogação).
    encerramento = EncerramentoMatricula(
        id_aluno=id_matricula,
        estado_anterior=aluno.status_atividade,
        data_encerramento=datetime.now(),
        data_expurgo=date.today() + timedelta(days=DIAS_RETENCAO),
        dossie_pdf=pdf_bytes,
        dossie_nome=nome_arquivo,
        encerrado_por=admin.username,
    )
    db.add(encerramento)

    # 3. Tira o aluno das telas do dia a dia (mas NÃO apaga nada ainda).
    aluno.status_atividade = STATUS_ENCERRADO

    auditoria.registrar(
        db,
        acao="encerrar_matricula",
        autor=admin.username,
        id_aluno=id_matricula,
        descricao=f"Matrícula encerrada; expurgo em {encerramento.data_expurgo.isoformat()}.",
    )

    db.commit()
    return {
        "status": "Matrícula encerrada",
        "dossie": nome_arquivo,
        "data_expurgo": encerramento.data_expurgo.isoformat(),
    }


@router.get(
    "/encerramentos",
    summary="Listar matrículas encerradas (janela de retenção)",
    description=(
        "Retorna as matrículas encerradas ainda dentro da janela de 30 dias, "
        "com os dias restantes até o expurgo definitivo."
    ),
)
def listar_encerradas(db: Session = Depends(get_db)):
    hoje = date.today()
    registros = (
        db.query(EncerramentoMatricula)
        .order_by(EncerramentoMatricula.data_encerramento.desc())
        .all()
    )
    resultado = []
    for e in registros:
        aluno = db.query(Aluno).filter(Aluno.id_matricula == e.id_aluno).first()
        dias_restantes = max(0, (e.data_expurgo - hoje).days)
        resultado.append(
            {
                "id_matricula": e.id_aluno,
                "nome": aluno.nome if aluno else "(registro em expurgo)",
                "data_encerramento": e.data_encerramento.strftime("%d/%m/%Y %H:%M"),
                "data_expurgo": e.data_expurgo.isoformat(),
                "dias_restantes": dias_restantes,
                "encerrado_por": e.encerrado_por,
                "dossie_nome": e.dossie_nome,
            }
        )
    return resultado


@router.get(
    "/alunos/{id_matricula}/dossie",
    summary="Baixar o dossiê PDF da matrícula encerrada",
    description=(
        "Devolve o dossiê PDF gerado no ato do encerramento (disponível durante "
        "a janela de 30 dias)."
    ),
    response_class=Response,
)
def baixar_dossie(id_matricula: str, db: Session = Depends(get_db)):
    encerramento = (
        db.query(EncerramentoMatricula)
        .filter(EncerramentoMatricula.id_aluno == id_matricula)
        .first()
    )
    if not encerramento or not encerramento.dossie_pdf:
        raise HTTPException(status_code=404, detail="Dossiê não encontrado")

    return Response(
        content=encerramento.dossie_pdf,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{encerramento.dossie_nome}"'
        },
    )


@router.post(
    "/alunos/{id_matricula}/revogar-encerramento",
    summary="Revogar o encerramento (restaura o aluno ao estado anterior)",
    description=(
        "Cancela um encerramento dentro da janela de 30 dias. Como nada foi "
        "apagado até o expurgo, a revogação apenas restaura o "
        "`status_atividade` anterior e remove o registro de encerramento "
        "(cancelando o expurgo agendado)."
    ),
)
def revogar_encerramento(
    id_matricula: str,
    db: Session = Depends(get_db),
    admin: Usuario = Depends(requer_papel("admin")),
):
    encerramento = (
        db.query(EncerramentoMatricula)
        .filter(EncerramentoMatricula.id_aluno == id_matricula)
        .first()
    )
    if not encerramento:
        raise HTTPException(
            status_code=404, detail="Não há encerramento a revogar para esta matrícula."
        )

    aluno = db.query(Aluno).filter(Aluno.id_matricula == id_matricula).first()
    if aluno:
        # Restaura exatamente o status em que o aluno estava antes.
        aluno.status_atividade = encerramento.estado_anterior

    estado_restaurado = encerramento.estado_anterior
    auditoria.registrar(
        db,
        acao="revogar_encerramento",
        autor=admin.username,
        id_aluno=id_matricula,
        descricao=f"Encerramento revogado; status restaurado para {estado_restaurado}.",
    )

    db.delete(encerramento)
    db.commit()
    return {
        "status": "Encerramento revogado",
        "estado_restaurado": estado_restaurado,
    }
