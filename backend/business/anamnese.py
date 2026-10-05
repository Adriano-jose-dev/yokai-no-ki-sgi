"""
Domínio Anamnese — Prontuário médico versionado (Fase 3 do roadmap) — SGI-YKR.

Fonte da verdade: steering `regras-negocio-ykr.md`, Fase 3.

Concentra a lógica pura da anamnese (sem FastAPI):

- `CATALOGO_PERGUNTAS`: as perguntas da anamnese, cada uma com rótulo e um flag
  `critica` (se "sim" naquela condição deve ir ao card de alerta) + a
  `severidade` (alta/media) para a cor do card no front.
- `calcular_validade`: `data_preenchimento + validade_meses`.
- `status_validade`: 'ok', 'vence_em_breve' (≤ 30 dias) ou 'vencida'.
- `extrair_condicoes_criticas`: dado o mapa de respostas, retorna as chaves
  "sim" que são críticas.
- `montar_card_alerta`: monta o CARD DE ALERTA CRÍTICO (condições + contatos de
  emergência + status de validade) a partir da anamnese ativa.
- `serializar_restricao_legada`: gera a string "Condições: X. Obs: Z" para
  manter `Aluno.restricao_medica` em sincronia com a anamnese (coexistência).

Nenhuma função toca o banco nem faz commit — isso é responsabilidade do router.
"""

from __future__ import annotations

import calendar
import json
from datetime import date

# Catálogo das perguntas da anamnese. As chaves espelham as usadas no front
# (matricula-form / admin-detail), para a string legada continuar coerente.
# `critica=True` => a resposta "sim" entra no card de alerta crítico.
CATALOGO_PERGUNTAS = [
    {"chave": "problemas_cardiacos", "label": "Problemas cardíacos", "critica": True, "severidade": "alta"},
    {"chave": "dores_peito", "label": "Dores no peito", "critica": True, "severidade": "alta"},
    {"chave": "falta_ar", "label": "Falta de ar", "critica": True, "severidade": "media"},
    {"chave": "tontura", "label": "Tonturas ou desmaios", "critica": True, "severidade": "alta"},
    {"chave": "pressao_alta", "label": "Pressão alta (hipertensão)", "critica": True, "severidade": "alta"},
    {"chave": "diabetes", "label": "Diabetes", "critica": True, "severidade": "media"},
    {"chave": "asma", "label": "Asma / problema respiratório", "critica": True, "severidade": "alta"},
    {"chave": "cirurgias", "label": "Cirurgia nos últimos 12 meses", "critica": False, "severidade": "media"},
    {"chave": "alergias", "label": "Alergia relevante", "critica": True, "severidade": "media"},
]

# Índices auxiliares derivados do catálogo.
_POR_CHAVE = {p["chave"]: p for p in CATALOGO_PERGUNTAS}
CHAVES_CRITICAS = {p["chave"] for p in CATALOGO_PERGUNTAS if p["critica"]}

# Janela (em dias) para considerar a anamnese "vence em breve".
DIAS_ALERTA_VENCIMENTO = 30


def calcular_validade(data_preenchimento: date, validade_meses: int) -> date:
    """Soma `validade_meses` à data de preenchimento (trata meses curtos)."""
    total = data_preenchimento.month - 1 + validade_meses
    ano = data_preenchimento.year + total // 12
    mes = total % 12 + 1
    ultimo_dia = calendar.monthrange(ano, mes)[1]
    dia = min(data_preenchimento.day, ultimo_dia)
    return date(ano, mes, dia)


def status_validade(data_validade: date | None, hoje: date) -> dict:
    """Classifica a validade: 'ok', 'vence_em_breve' ou 'vencida'.

    Retorna também `dias_restantes` (negativo quando já vencida).
    """
    if not data_validade:
        return {"status": "ok", "dias_restantes": None}
    dias = (data_validade - hoje).days
    if dias < 0:
        estado = "vencida"
    elif dias <= DIAS_ALERTA_VENCIMENTO:
        estado = "vence_em_breve"
    else:
        estado = "ok"
    return {"status": estado, "dias_restantes": dias}


def _carregar_respostas(respostas) -> dict:
    """Aceita dict (já parseado) ou string JSON; devolve sempre um dict."""
    if isinstance(respostas, dict):
        return respostas
    if isinstance(respostas, str) and respostas.strip():
        try:
            return json.loads(respostas)
        except json.JSONDecodeError:
            return {}
    return {}


def _carregar_condicoes_criticas(valor) -> list[str] | None:
    """Lê a lista de condições críticas já persistida (JSON de lista).

    Retorna `None` quando não há valor utilizável, para o chamador derivar das
    respostas.
    """
    if isinstance(valor, list):
        return valor
    if isinstance(valor, str) and valor.strip():
        try:
            carregado = json.loads(valor)
            return carregado if isinstance(carregado, list) else None
        except json.JSONDecodeError:
            return None
    return None


def extrair_condicoes_criticas(respostas) -> list[str]:
    """Chaves respondidas 'sim' que são clinicamente críticas (p/ o card)."""
    mapa = _carregar_respostas(respostas)
    return [
        chave
        for chave, valor in mapa.items()
        if str(valor).lower() == "sim" and chave in CHAVES_CRITICAS
    ]


def rotular(chave: str) -> str:
    """Rótulo legível de uma chave de pergunta (fallback: a própria chave)."""
    item = _POR_CHAVE.get(chave)
    return item["label"] if item else chave


def severidade(chave: str) -> str:
    item = _POR_CHAVE.get(chave)
    return item["severidade"] if item else "media"


def montar_card_alerta(anamnese, hoje: date) -> dict | None:
    """Monta o card de alerta crítico a partir da anamnese ativa.

    Retorna `None` quando não há anamnese. O card lista as condições críticas
    (com rótulo e severidade), a observação, os contatos de emergência e o
    status de validade — tudo que o perfil precisa destacar.
    """
    if anamnese is None:
        return None

    # `condicoes_criticas_json` já é a LISTA de chaves críticas (gravada na
    # criação). Se estiver ausente, derivamos do mapa de respostas.
    criticas = _carregar_condicoes_criticas(anamnese.condicoes_criticas_json)
    if criticas is None:
        criticas = extrair_condicoes_criticas(anamnese.respostas_json)
    validade = status_validade(anamnese.data_validade, hoje)

    return {
        "tem_alerta": bool(criticas),
        "condicoes": [
            {"chave": c, "label": rotular(c), "severidade": severidade(c)}
            for c in criticas
        ],
        "observacao": anamnese.observacao or "",
        "contato_emergencia": {
            "nome": anamnese.contato_emergencia_nome,
            "parentesco": anamnese.contato_emergencia_parentesco,
            "telefone": anamnese.contato_emergencia_telefone,
        },
        "validade": {
            "data_validade": (
                anamnese.data_validade.isoformat() if anamnese.data_validade else None
            ),
            "status": validade["status"],
            "dias_restantes": validade["dias_restantes"],
        },
        "versao": anamnese.versao,
        "data_preenchimento": anamnese.data_preenchimento.isoformat(),
    }


def serializar_restricao_legada(respostas, observacao: str | None) -> str | None:
    """Gera a string legada "Condições: X, Y. Obs: Z" (sincroniza o campo antigo).

    Mantém `Aluno.restricao_medica` coerente com a anamnese para não quebrar as
    telas/parsers legados. Retorna `None` quando não há condição nem observação.
    """
    mapa = _carregar_respostas(respostas)
    marcadas = [c for c, v in mapa.items() if str(v).lower() == "sim"]
    obs = (observacao or "").strip()
    if not marcadas and not obs:
        return None
    condicoes = ", ".join(marcadas)
    return f"Condições: {condicoes}. Obs: {obs or 'Nenhuma'}"
