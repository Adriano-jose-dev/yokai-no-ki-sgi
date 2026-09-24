"""
Regra única da Trava Automática de Inadimplência — SGI-YKR (Tarefa 3 / Requisito 2).

Fonte da verdade: steering `regras-negocio-ykr.md`, seção 1.2 e 1.3.

Toda a lógica de avaliar/aplicar/reverter a trava por inadimplência vive aqui,
em uma única função (`avaliar_trava_inadimplencia`). As rotas (`obter_progresso`,
`editar_contrato`) e, futuramente, o agendador diário (Fase A / Requisito 10)
devem chamar esta função em vez de reimplementar a regra.

Regras consolidadas:
- Aplica-se APENAS ao plano `Mensalidade`.
- Atraso = `hoje > dia_vencimento + 5 dias` (com fallback para meses curtos,
  ex.: vencimento dia 31 em fevereiro).
- `[ACORDO]` em `observacao_financeira` → bypass total (nunca bloqueia).
- Ao trancar: status vira `Trancado`, prefixa `[TRAVA AUTOMÁTICA]` na observação
  e encerra imediatamente uma eventual sessão de tatame aberta.
- Se o aluno voltou a ficar em dia e a trava havia sido automática, reverte o
  status para `Ativo` e remove o prefixo `[TRAVA AUTOMÁTICA]`.

A função NÃO faz commit; quem chama é responsável pela transação. Retorna
`atraso_critico` (bool): `True` quando o aluno está em atraso relevante e sem
`[ACORDO]`.
"""

import calendar
import re
from datetime import date, datetime, timedelta

from models import Sessao

# Marcadores usados na observação financeira.
PREFIXO_TRAVA = "[TRAVA AUTOMÁTICA]"
MARCADOR_ACORDO = "[ACORDO]"
DIAS_TOLERANCIA = 5

# Remove o bloco "[TRAVA AUTOMÁTICA] ...<algo>. " da observação (não-guloso).
_REGEX_LIMPA_TRAVA = re.compile(r"\[TRAVA AUTOMÁTICA\].*?\. ")


def _data_vencimento(hoje: date, dia_vencimento: int) -> date:
    """Monta a data de vencimento no mês corrente, tratando meses curtos.

    Ex.: dia_vencimento = 31 em fevereiro cai para o último dia do mês.
    """
    try:
        return date(hoje.year, hoje.month, dia_vencimento)
    except ValueError:
        ultimo_dia = calendar.monthrange(hoje.year, hoje.month)[1]
        return date(hoje.year, hoje.month, ultimo_dia)


def _encerrar_sessao_aberta(db, id_aluno: str) -> None:
    """Encerra imediatamente uma sessão de tatame aberta do aluno, se houver."""
    sessao_aberta = (
        db.query(Sessao)
        .filter(Sessao.id_aluno == id_aluno, Sessao.hora_saida == None)  # noqa: E711
        .first()
    )
    if sessao_aberta:
        sessao_aberta.hora_saida = datetime.now()
        sessao_aberta.diario_sensei = (
            "[SISTEMA] Cronômetro interrompido pela trava automática."
        )


def avaliar_trava_inadimplencia(db, aluno, contrato, hoje: date) -> bool:
    """Avalia e aplica a trava de inadimplência para um aluno.

    Args:
        db: sessão SQLAlchemy ativa (o commit é responsabilidade do chamador).
        aluno: instância de `Aluno`.
        contrato: instância de `Contrato` (pode ser `None`).
        hoje: data de referência para a avaliação.

    Returns:
        bool: `atraso_critico` — `True` se o aluno está em atraso e sem
        `[ACORDO]`; `False` caso contrário.
    """
    # A trava só se aplica ao plano Mensalidade.
    if not contrato or contrato.modelo_plano != "Mensalidade":
        return False

    # Só avaliamos alunos que podem transitar entre Ativo/Trancado por trava.
    if aluno.status_atividade not in ("Ativo", "Trancado"):
        return False

    observacao = contrato.observacao_financeira or ""
    tem_acordo = MARCADOR_ACORDO in observacao

    data_venc = _data_vencimento(hoje, contrato.dia_vencimento)
    em_atraso = hoje > data_venc + timedelta(days=DIAS_TOLERANCIA)

    # Bypass total por acordo: nunca bloqueia, e não marca atraso crítico.
    if tem_acordo:
        return False

    if em_atraso:
        # Aplica a trava caso ainda não esteja travado por ela.
        if aluno.status_atividade == "Ativo":
            aluno.status_atividade = "Trancado"
            contrato.observacao_financeira = (
                f"{PREFIXO_TRAVA} Matrícula bloqueada em "
                f"{hoje.strftime('%d/%m/%Y')}. " + observacao
            )
            _encerrar_sessao_aberta(db, aluno.id_matricula)
        return True

    # Em dia: reverte trava automática anterior, se houver.
    if aluno.status_atividade == "Trancado" and PREFIXO_TRAVA in observacao:
        aluno.status_atividade = "Ativo"
        contrato.observacao_financeira = _REGEX_LIMPA_TRAVA.sub("", observacao)

    return False
