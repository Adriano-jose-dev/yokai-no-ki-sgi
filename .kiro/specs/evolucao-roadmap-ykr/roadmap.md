# Roadmap — Evolução do SGI-YKR

Execução **por fases**, uma de cada vez, com verificação (testes + build) ao
final de cada uma antes de avançar.

| Fase | Pilar | Escopo | Estado |
| --- | --- | --- | --- |
| 0 | Técnico | Modularização de `models.py`/`routers/` em domínios | ⏳ A planejar |
| 1 | 1 — Tatame | Turmas, Modo Tatame por tipo, Calendário editável | 🔍 Em refinamento |
| 2 | 3 — Financeiro | Conta corrente (débito/crédito), 3 níveis de valor, abono de falta | ✅ Conceito travado (aguarda Turmas) |
| 3 | 2 — Anamnese | Anamnese versionada + card de alerta crítico | 📋 Capturado |
| 4 | 4 — Auditoria | Log de segurança com filtros (Geral/Aluno/Sensíveis) e retenção | 📋 Capturado |
| 5 | 5 — Áreas | Material didático, professor e aluno | 🔮 Futuro (só mapeado) |

**Legenda:** 🔍 refinando conceito · ✅ conceito travado · 📋 requisitos
capturados, aguardando a vez · 🔮 futuro · ⏳ a planejar.

> **Ordem revista:** Turmas (Pilar 1) vem **antes** do Financeiro (Pilar 3)
> porque o cálculo financeiro (valor base da turma, horas do mês pelo calendário,
> cancelamento de aula que altera o valor) **depende** de Turma e Calendário
> existirem. Construir o financeiro antes significaria descartá-lo quando a
> Turma chegasse.

## Princípios de execução

1. **Um pilar por vez.** Só se inicia o design técnico de um pilar após o
   conceito estar aprovado.
2. **Banco → API → Front.** Dentro de cada fase, modela-se o dado, expõe-se a
   API e só então o front consome.
3. **Verificação a cada fase.** `pytest` (back) e `ng build` (front) verdes antes
   de fechar a fase.
4. **Steering vivo.** `regras-negocio-ykr.md` é atualizado ao fim de cada fase
   com as novas regras consolidadas.
5. **Fase 0 primeiro.** A modularização em domínios precede os pilares, para não
   empilhar complexidade sobre um `models.py` monolítico.

## Fase atual

**Fase 1 — Turmas, Modo Tatame e Calendário.** Em refinamento conceitual. O
conceito do **Financeiro (Fase 2) já está travado** e aguarda a Turma como base.
Nenhum código será escrito antes da aprovação do conceito de Turmas.
