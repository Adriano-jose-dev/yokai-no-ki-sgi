"""
Geração de ocorrências de aula a partir da recorrência (RRULE) — SGI-YKR.

Expande a `recorrencia_rrule` de uma turma (padrão iCalendar/RRULE) dentro de um
intervalo de datas e cria as `OcorrenciaAula` que ainda não existem. Idempotente:
rodar de novo não duplica ocorrências já geradas, nem recria as que foram
excluídas/canceladas manualmente para a mesma data.

Usa `dateutil.rrule.rrulestr` para suportar qualquer regra (ex.:
'FREQ=WEEKLY;BYDAY=SA' = todo sábado; 'FREQ=MONTHLY;BYDAY=+1TU,+3TU' = 1ª e 3ª
terça do mês).
"""

from __future__ import annotations

from datetime import date, datetime

from dateutil.rrule import rrulestr

from models import Turma, OcorrenciaAula


def expandir_datas(rrule_str: str, inicio: date, fim: date) -> list[date]:
    """Expande uma regra RRULE no intervalo [inicio, fim], retornando as datas.

    `DTSTART` é ancorado em `inicio` quando a regra não traz um próprio.
    """
    if not rrule_str:
        return []
    regra = rrule_str.strip()
    # Garante um DTSTART para a expansão (dateutil exige âncora).
    if "DTSTART" not in regra.upper():
        dtstart = datetime(inicio.year, inicio.month, inicio.day)
        rule = rrulestr(regra, dtstart=dtstart)
    else:
        rule = rrulestr(regra)

    ini_dt = datetime(inicio.year, inicio.month, inicio.day)
    fim_dt = datetime(fim.year, fim.month, fim.day, 23, 59, 59)
    return [dt.date() for dt in rule.between(ini_dt, fim_dt, inc=True)]


def gerar_ocorrencias(
    db, turma: Turma, inicio: date, fim: date
) -> list[OcorrenciaAula]:
    """Gera (sem commit) as ocorrências da turma no intervalo que ainda faltam.

    - Só gera para turmas com `recorrencia_rrule` definida.
    - Não duplica: pula datas que já têm ocorrência para a turma.
    - Herda `hora_inicio`/`hora_fim` da turma como snapshot.

    Retorna a lista das ocorrências recém-criadas.
    """
    if not turma.recorrencia_rrule:
        return []

    datas = expandir_datas(turma.recorrencia_rrule, inicio, fim)
    if not datas:
        return []

    # Datas que já possuem ocorrência (qualquer estado) para não duplicar.
    existentes = {
        o.data
        for o in db.query(OcorrenciaAula)
        .filter(
            OcorrenciaAula.id_turma == turma.id,
            OcorrenciaAula.data >= inicio,
            OcorrenciaAula.data <= fim,
        )
        .all()
    }

    novas = []
    for d in datas:
        if d in existentes:
            continue
        oc = OcorrenciaAula(
            id_turma=turma.id,
            data=d,
            hora_inicio=turma.hora_inicio,
            hora_fim=turma.hora_fim,
            estado="prevista",
            origem="recorrencia",
        )
        db.add(oc)
        novas.append(oc)
    return novas


def duracao_prevista_horas(oc: OcorrenciaAula) -> float:
    """Duração prevista da ocorrência em horas decimais, a partir de hora_inicio/fim.

    Retorna 0.0 se as horas não estiverem definidas ou forem inválidas.
    """
    if not oc.hora_inicio or not oc.hora_fim:
        return 0.0
    try:
        hi_h, hi_m = (int(x) for x in oc.hora_inicio.split(":"))
        hf_h, hf_m = (int(x) for x in oc.hora_fim.split(":"))
    except (ValueError, AttributeError):
        return 0.0
    minutos = (hf_h * 60 + hf_m) - (hi_h * 60 + hi_m)
    return round(max(0, minutos) / 60.0, 4)
