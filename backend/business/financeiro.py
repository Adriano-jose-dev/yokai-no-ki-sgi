"""
Domínio Financeiro — Conta Corrente (Fase 2 do roadmap) — SGI-YKR.

Fonte da verdade: steering `regras-negocio-ykr.md`, Fase 2.

Toda a aritmética do financeiro vive aqui, isolada das rotas:

- `calcular_mensalidade_prevista`: soma `valor_base × horas previstas` das
  ocorrências do mês (estados `prevista`/`realizada`; `cancelada` sai da conta).
  Falta do aluno NÃO altera o valor — só o cancelamento de aula pela escola.
- `gerar_mensalidade`: materializa o débito da mensalidade do mês no vencimento
  (idempotente por `mes_referencia`), já abatendo crédito disponível.
- `registrar_pagamento`: lança um crédito e o aplica em cascata sobre os débitos
  abertos (mais antigos primeiro).
- `resumo_conta_corrente`: saldo (débito aberto × crédito disponível) + extrato.

Nenhuma função faz commit — a transação é responsabilidade do chamador (rota).
"""

from __future__ import annotations

import calendar
from datetime import date

from sqlalchemy.orm import Session

from models import (
    Aluno,
    Contrato,
    Turma,
    TurmaMatricula,
    OcorrenciaAula,
    Lancamento,
)
from business.ocorrencias import duracao_prevista_horas

# Estados de ocorrência que CONTAM para o cálculo da mensalidade.
ESTADOS_FINANCEIROS = ("prevista", "realizada")


def _intervalo_do_mes(ano: int, mes: int) -> tuple[date, date]:
    """Primeiro e último dia do mês informado."""
    ultimo = calendar.monthrange(ano, mes)[1]
    return date(ano, mes, 1), date(ano, mes, ultimo)


def _turmas_mensalidade_do_aluno(db: Session, id_aluno: str) -> list[Turma]:
    """Turmas de Mensalidade onde o aluno é **matriculado** (não ocorrente).

    Ocorrente não gera cobrança (ex.: Legado assistindo Dojo), então fica fora.
    """
    vinculos = (
        db.query(TurmaMatricula)
        .filter(
            TurmaMatricula.id_aluno == id_aluno,
            TurmaMatricula.papel == "matriculado",
        )
        .all()
    )
    ids = [v.id_turma for v in vinculos]
    if not ids:
        return []
    return (
        db.query(Turma)
        .filter(Turma.id.in_(ids), Turma.tipo_pagamento == "Mensalidade")
        .all()
    )


def calcular_mensalidade_prevista(db: Session, id_aluno: str, ano: int, mes: int) -> dict:
    """Calcula o valor previsto da mensalidade do aluno no mês.

    `valor = Σ (valor_base_da_turma × horas_previstas_da_ocorrência)` para todas
    as ocorrências do mês nas turmas de Mensalidade do aluno, considerando apenas
    os estados `prevista`/`realizada` (as `cancelada` são descartadas).

    Retorna um detalhamento (valor total, nº de aulas, horas e por turma) para a
    rota expor transparência ao gestor.
    """
    inicio, fim = _intervalo_do_mes(ano, mes)
    turmas = _turmas_mensalidade_do_aluno(db, id_aluno)

    total = 0.0
    total_horas = 0.0
    total_aulas = 0
    detalhe_turmas = []

    for turma in turmas:
        ocs = (
            db.query(OcorrenciaAula)
            .filter(
                OcorrenciaAula.id_turma == turma.id,
                OcorrenciaAula.data >= inicio,
                OcorrenciaAula.data <= fim,
                OcorrenciaAula.estado.in_(ESTADOS_FINANCEIROS),
            )
            .all()
        )
        horas_turma = sum(duracao_prevista_horas(o) for o in ocs)
        valor_turma = round(horas_turma * turma.valor_base, 2)
        total += valor_turma
        total_horas += horas_turma
        total_aulas += len(ocs)
        detalhe_turmas.append(
            {
                "id_turma": turma.id,
                "turma_nome": turma.nome,
                "valor_base": turma.valor_base,
                "aulas": len(ocs),
                "horas": round(horas_turma, 4),
                "valor": valor_turma,
            }
        )

    return {
        "mes_referencia": f"{ano:04d}-{mes:02d}",
        "valor": round(total, 2),
        "horas": round(total_horas, 4),
        "aulas": total_aulas,
        "turmas": detalhe_turmas,
    }


def _creditos_disponiveis(db: Session, id_aluno: str) -> list[Lancamento]:
    return (
        db.query(Lancamento)
        .filter(
            Lancamento.id_aluno == id_aluno,
            Lancamento.tipo == "credito",
            Lancamento.valor_aberto > 0,
        )
        .order_by(Lancamento.criado_em.asc())
        .all()
    )


def _debitos_abertos(db: Session, id_aluno: str) -> list[Lancamento]:
    return (
        db.query(Lancamento)
        .filter(
            Lancamento.id_aluno == id_aluno,
            Lancamento.tipo == "debito",
            Lancamento.valor_aberto > 0,
        )
        .order_by(Lancamento.data_competencia.asc(), Lancamento.id.asc())
        .all()
    )


def _abater_debito_com_creditos(db: Session, debito: Lancamento) -> None:
    """Consome créditos disponíveis para abater um débito recém-gerado."""
    for credito in _creditos_disponiveis(db, debito.id_aluno):
        if debito.valor_aberto <= 0:
            break
        usar = min(credito.valor_aberto, debito.valor_aberto)
        credito.valor_aberto = round(credito.valor_aberto - usar, 2)
        debito.valor_aberto = round(debito.valor_aberto - usar, 2)
        if credito.valor_aberto <= 0:
            credito.status = "quitado"
    _atualizar_status_debito(debito)


def _atualizar_status_debito(debito: Lancamento) -> None:
    if debito.valor_aberto <= 0:
        debito.status = "quitado"
        debito.valor_aberto = 0.0
    elif debito.valor_aberto < debito.valor:
        debito.status = "parcial"
    else:
        debito.status = "aberto"


def gerar_debito(
    db: Session,
    id_aluno: str,
    categoria: str,
    valor: float,
    descricao: str,
    data_competencia: date,
    data_vencimento: date | None = None,
    mes_referencia: str | None = None,
    id_ocorrencia: int | None = None,
) -> Lancamento:
    """Cria um débito na conta corrente e já o abate com crédito disponível."""
    debito = Lancamento(
        id_aluno=id_aluno,
        tipo="debito",
        categoria=categoria,
        valor=round(valor, 2),
        valor_aberto=round(valor, 2),
        status="aberto",
        descricao=descricao,
        data_competencia=data_competencia,
        data_vencimento=data_vencimento,
        mes_referencia=mes_referencia,
        id_ocorrencia=id_ocorrencia,
    )
    db.add(debito)
    db.flush()  # garante id/valores antes de abater
    _abater_debito_com_creditos(db, debito)
    return debito


def gerar_mensalidade(db: Session, id_aluno: str, ano: int, mes: int) -> dict:
    """Gera (idempotente) o débito da mensalidade do mês para o aluno.

    - Calcula o valor pelo calendário (ocorrências previstas/realizadas).
    - Usa o `dia_vencimento` do contrato como `data_vencimento` (a trava de
      inadimplência existente age sobre ele).
    - Se já existe um lançamento de mensalidade para o mês, **atualiza** o valor
      (reflete cancelamentos de aula) em vez de duplicar.

    Retorna o detalhamento do cálculo e o id do lançamento.
    """
    calculo = calcular_mensalidade_prevista(db, id_aluno, ano, mes)
    mes_ref = calculo["mes_referencia"]
    contrato = db.query(Contrato).filter(Contrato.id_aluno == id_aluno).first()
    dia_venc = contrato.dia_vencimento if contrato else 10
    ultimo = calendar.monthrange(ano, mes)[1]
    data_venc = date(ano, mes, min(dia_venc, ultimo))

    existente = (
        db.query(Lancamento)
        .filter(
            Lancamento.id_aluno == id_aluno,
            Lancamento.categoria == "mensalidade",
            Lancamento.mes_referencia == mes_ref,
        )
        .first()
    )

    descricao = f"Mensalidade {mes_ref} ({calculo['aulas']} aulas)"

    if existente:
        # Recalcula o valor (ex.: aula cancelada reduz). Preserva o quanto já
        # foi quitado: valor_aberto = novo_valor - (valor_antigo - aberto_antigo).
        ja_quitado = round(existente.valor - existente.valor_aberto, 2)
        existente.valor = calculo["valor"]
        existente.valor_aberto = max(0.0, round(calculo["valor"] - ja_quitado, 2))
        existente.descricao = descricao
        existente.data_vencimento = data_venc
        _atualizar_status_debito(existente)
        if existente.valor_aberto > 0:
            _abater_debito_com_creditos(db, existente)
        lancamento = existente
    else:
        lancamento = gerar_debito(
            db,
            id_aluno=id_aluno,
            categoria="mensalidade",
            valor=calculo["valor"],
            descricao=descricao,
            data_competencia=date(ano, mes, 1),
            data_vencimento=data_venc,
            mes_referencia=mes_ref,
        )

    return {
        **calculo,
        "id_lancamento": lancamento.id,
        "data_vencimento": data_venc.isoformat(),
        "status": lancamento.status,
        "valor_aberto": lancamento.valor_aberto,
    }


def registrar_pagamento(
    db: Session, id_aluno: str, valor: float, metodo: str
) -> dict:
    """Lança um crédito de pagamento e o aplica aos débitos abertos.

    Quita os débitos mais antigos primeiro; qualquer sobra permanece como
    crédito disponível (saldo a favor do aluno).
    """
    credito = Lancamento(
        id_aluno=id_aluno,
        tipo="credito",
        categoria="pagamento",
        valor=round(valor, 2),
        valor_aberto=round(valor, 2),
        status="aberto",
        descricao=f"Pagamento ({metodo})",
        data_competencia=date.today(),
        metodo=metodo,
    )
    db.add(credito)
    db.flush()

    for debito in _debitos_abertos(db, id_aluno):
        if credito.valor_aberto <= 0:
            break
        usar = min(credito.valor_aberto, debito.valor_aberto)
        credito.valor_aberto = round(credito.valor_aberto - usar, 2)
        debito.valor_aberto = round(debito.valor_aberto - usar, 2)
        _atualizar_status_debito(debito)

    if credito.valor_aberto <= 0:
        credito.status = "quitado"
        credito.valor_aberto = 0.0

    return {
        "id_lancamento": credito.id,
        "valor_pago": round(valor, 2),
        "credito_restante": credito.valor_aberto,
    }


def resumo_conta_corrente(db: Session, id_aluno: str) -> dict:
    """Monta o resumo da conta corrente: saldos + extrato de lançamentos."""
    lancamentos = (
        db.query(Lancamento)
        .filter(Lancamento.id_aluno == id_aluno)
        .order_by(Lancamento.data_competencia.desc(), Lancamento.id.desc())
        .all()
    )

    total_debito_aberto = round(
        sum(l.valor_aberto for l in lancamentos if l.tipo == "debito"), 2
    )
    credito_disponivel = round(
        sum(l.valor_aberto for l in lancamentos if l.tipo == "credito"), 2
    )

    extrato = [
        {
            "id": l.id,
            "tipo": l.tipo,
            "categoria": l.categoria,
            "descricao": l.descricao,
            "valor": l.valor,
            "valor_aberto": l.valor_aberto,
            "status": l.status,
            "data_competencia": l.data_competencia.isoformat(),
            "data_vencimento": (
                l.data_vencimento.isoformat() if l.data_vencimento else None
            ),
            "mes_referencia": l.mes_referencia,
        }
        for l in lancamentos
    ]

    return {
        "id_aluno": id_aluno,
        "valores_em_aberto": total_debito_aberto,
        "credito_disponivel": credito_disponivel,
        # Saldo líquido: positivo = crédito a favor; negativo = devendo.
        "saldo_liquido": round(credito_disponivel - total_debito_aberto, 2),
        "extrato": extrato,
    }
