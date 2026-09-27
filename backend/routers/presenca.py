"""
Rotas de domínio Presença — SGI-YKR.

Listagem da chamada diária (omitindo alunos Inativos) e registro em lote.
Comportamento idêntico ao monolito original.
"""

from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from models import Aluno, Presenca
from schemas import PresencaBulkRequest
from business.auth import requer_papel

router = APIRouter(tags=["Presença"], dependencies=[Depends(requer_papel("admin"))])


@router.get(
    "/presenca/diaria/{data_consulta}",
    summary="Listar chamada diária",
    description=(
        "Retorna a chamada da data informada com o status de cada aluno "
        "(`Presente`/`Ausente`/`Pendente`). Alunos `Inativo` são omitidos."
    ),
)
def listar_chamada_diaria(data_consulta: date, db: Session = Depends(get_db)):
    alunos = (
        db.query(Aluno)
        .filter(Aluno.status_atividade.notin_(["Inativo", "Encerrado"]))
        .all()
    )
    resultado = []
    for a in alunos:
        p = (
            db.query(Presenca)
            .filter(Presenca.id_aluno == a.id_matricula, Presenca.data == data_consulta)
            .first()
        )
        resultado.append(
            {
                "id_matricula": a.id_matricula,
                "nome": a.nome,
                "graduacao_atual": a.graduacao_atual,
                "modo_treino": a.modo_treino,
                "status": p.status if p else "Pendente",
            }
        )
    return resultado


@router.post(
    "/presenca/bulk",
    summary="Registrar presença em lote",
    description=(
        "Cria ou atualiza os registros de presença de vários alunos de uma "
        "vez para a data informada (upsert por aluno+data)."
    ),
)
def registrar_presenca_bulk(req: PresencaBulkRequest, db: Session = Depends(get_db)):
    for p in req.presencas:
        registro = (
            db.query(Presenca)
            .filter(Presenca.id_aluno == p.id_aluno, Presenca.data == req.data)
            .first()
        )
        if registro:
            registro.status = p.status
        else:
            db.add(Presenca(id_aluno=p.id_aluno, data=req.data, status=p.status))
    db.commit()
    return {"status": "Chamada registrada"}
