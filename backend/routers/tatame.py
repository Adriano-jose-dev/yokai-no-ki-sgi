"""
Rotas de domínio Tatame — SGI-YKR.

Listagem de alunos disponíveis, início e encerramento de sessão (com o cálculo
de custo conforme a hierarquia de cobrança do steering). Comportamento idêntico
ao monolito original.
"""

from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import Aluno, Contrato, Sessao, Presenca
from schemas import SessaoRequest, StopSessaoRequest
from business.auth import requer_papel

router = APIRouter(tags=["Tatame"], dependencies=[Depends(requer_papel("admin"))])


@router.get(
    "/tatame/ativos",
    summary="Listar alunos disponíveis no tatame",
    description=(
        "Retorna os alunos aptos a treinar (`Ativo` e `Aula Experimental`), "
        "indicando se há sessão em andamento. Alunos `Trancado`/`Inativo` "
        "não aparecem."
    ),
)
def listar_ativos(db: Session = Depends(get_db)):
    resultado = []
    for a in (
        db.query(Aluno)
        .filter(Aluno.status_atividade.in_(["Ativo", "Aula Experimental"]))
        .all()
    ):
        sessao_ativa = (
            db.query(Sessao)
            .filter(Sessao.id_aluno == a.id_matricula, Sessao.hora_saida == None)
            .first()
        )
        contrato = (
            db.query(Contrato).filter(Contrato.id_aluno == a.id_matricula).first()
        )
        total_horas_exp = (
            sum(
                [
                    (s.hora_saida - s.hora_entrada).total_seconds() / 3600
                    for s in db.query(Sessao)
                    .filter(
                        Sessao.id_aluno == a.id_matricula, Sessao.hora_saida != None
                    )
                    .all()
                ]
            )
            if a.status_atividade == "Aula Experimental"
            else 0.0
        )

        resultado.append(
            {
                "id_matricula": a.id_matricula,
                "nome": a.nome,
                "status_atividade": a.status_atividade,
                "graduacao_atual": a.graduacao_atual,
                "restricao_medica": a.restricao_medica,
                "autorizacao_imagem": a.autorizacao_imagem,
                "hora_entrada": (
                    sessao_ativa.hora_entrada.isoformat() if sessao_ativa else None
                ),
                "total_horas_exp": round(total_horas_exp, 4),
                "modelo_plano": contrato.modelo_plano if contrato else "Horas Livres",
                "modo_treino": a.modo_treino,
                "hora_flexivel": a.hora_flexivel,
            }
        )
    return resultado


@router.post(
    "/sessao/start",
    summary="Iniciar sessão de tatame (cronômetro)",
    description=(
        "Abre uma sessão para o aluno.\n\n"
        "- Recusa (**400**) alunos que não estejam `Ativo`/`Aula "
        "Experimental` (bloqueado, trancado ou inativo).\n"
        "- Para **Aula Experimental**, respeita a cota experimental de tempo.\n"
        "- Recusa (**400**) se já houver uma sessão ativa para o aluno."
    ),
)
def iniciar_sessao(req: SessaoRequest, db: Session = Depends(get_db)):
    aluno = db.query(Aluno).filter(Aluno.id_matricula == req.id_matricula).first()

    if aluno.status_atividade not in ["Ativo", "Aula Experimental"]:
        raise HTTPException(
            status_code=400,
            detail="Aluno bloqueado, trancado ou inativo. Acesse a secretaria.",
        )

    if aluno.status_atividade == "Aula Experimental":
        total = sum(
            [
                (s.hora_saida - s.hora_entrada).total_seconds() / 3600
                for s in db.query(Sessao)
                .filter(Sessao.id_aluno == req.id_matricula, Sessao.hora_saida != None)
                .all()
            ]
        )
        if total >= 0.0166:
            raise HTTPException(status_code=400, detail="Cota experimental atingida.")

    if (
        db.query(Sessao)
        .filter(Sessao.id_aluno == req.id_matricula, Sessao.hora_saida == None)
        .first()
    ):
        raise HTTPException(status_code=400, detail="Sessão já ativa")

    db.add(Sessao(id_aluno=req.id_matricula, hora_entrada=datetime.now()))
    db.commit()
    return {"status": "Sessão iniciada"}


@router.post(
    "/sessao/stop",
    summary="Encerrar sessão, calcular custo e registrar presença",
    description=(
        "Fecha a sessão ativa, converte o tempo em horas decimais e calcula o "
        "custo pela **hierarquia de cobrança**:\n\n"
        "- **Hora flexível**: `horas × valor_base`.\n"
        "- **Mensalidade**: cobra só o que exceder a franquia de 3h "
        "(`(horas − 3) × valor_base`, nunca negativo).\n"
        "- **Intensivão**: `horas × (valor_base × 1.5)`.\n"
        "- **Horas Livres**: `horas × valor_base`.\n\n"
        "Aplica o desconto informado e registra automaticamente a **presença** "
        "do dia como `Presente`. Retorna **404** se não houver sessão ativa."
    ),
)
def finalizar_sessao(req: StopSessaoRequest, db: Session = Depends(get_db)):
    sessao = (
        db.query(Sessao)
        .filter(Sessao.id_aluno == req.id_matricula, Sessao.hora_saida == None)
        .first()
    )
    aluno = db.query(Aluno).filter(Aluno.id_matricula == req.id_matricula).first()
    if not sessao:
        raise HTTPException(status_code=404, detail="Sessão ativa não encontrada")

    contrato = db.query(Contrato).filter(Contrato.id_aluno == req.id_matricula).first()
    sessao.hora_saida = datetime.now()
    sessao.diario_sensei = req.diario_sensei
    sessao.desconto_aplicado = req.desconto_aplicado or 0.0

    horas_decimais = (sessao.hora_saida - sessao.hora_entrada).total_seconds() / 3600

    valor_base = contrato.valor_base if contrato else 20.0

    if aluno.hora_flexivel:
        custo_base = horas_decimais * valor_base
    elif contrato and contrato.modelo_plano == "Mensalidade":
        franquia = contrato.horas_franquia
        excedente = max(0.0, horas_decimais - franquia)
        custo_base = excedente * valor_base
    elif contrato and contrato.modelo_plano == "Intensivão":
        custo_base = horas_decimais * (valor_base * 1.5)
    else:
        custo_base = horas_decimais * valor_base

    sessao.valor_apurado = round(max(0.0, custo_base - sessao.desconto_aplicado), 2)

    # INTELIGÊNCIA NOVA: Registra automaticamente a presença na chamada do dia!
    hoje = date.today()
    registro_presenca = (
        db.query(Presenca)
        .filter(Presenca.id_aluno == req.id_matricula, Presenca.data == hoje)
        .first()
    )
    if registro_presenca:
        registro_presenca.status = "Presente"
    else:
        db.add(Presenca(id_aluno=req.id_matricula, data=hoje, status="Presente"))

    db.commit()
    return {"status": "Sessão finalizada", "valor": sessao.valor_apurado}
