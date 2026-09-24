# Guia de Contribuição — Yōkai no Ki SGI

Obrigado pelo interesse em contribuir! Este documento resume o fluxo de trabalho
e as convenções do projeto.

## Fluxo de trabalho

1. Faça um fork e crie uma branch a partir de `main`:
   `git checkout -b feat/minha-feature`
2. Faça suas alterações seguindo as convenções abaixo.
3. Garanta que os testes e o build passam localmente.
4. Abra um Pull Request descrevendo o **que** mudou e o **porquê**.

## Convenções de commit

Usamos [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` nova funcionalidade
- `fix:` correção de bug
- `docs:` documentação
- `refactor:` refatoração sem mudança de comportamento
- `test:` testes
- `chore:` tarefas de manutenção (build, deps, config)

Exemplo: `feat(tatame): adiciona cálculo de desconto por fidelidade`

## Padrões de código

**Back-end (Python)**
- Siga o estilo já presente no projeto (nomes em português no domínio, docstrings explicativas).
- Regras de negócio vivem em `backend/business/` — não duplique lógica nos routers.
- Toda nova regra ou correção de bug deve vir acompanhada de teste em `backend/test_*.py`.

**Front-end (Angular)**
- Componentes são **standalone**; declare os `imports` no próprio componente.
- Use a nova sintaxe de fluxo de controle (`@if`, `@for`) — nada de `*ngIf`/`*ngFor`.
- Estilização com as classes utilitárias da paleta do projeto (`sumi`, `carmesim`, `ouro`).
- Ícones via Lucide (`<lucide-icon>`), sem emojis na UI.

## Antes de abrir o PR

```bash
# Back-end
cd backend && pytest -q

# Front-end
cd frontend && npm run build
```

Ambos devem passar. O CI (GitHub Actions) roda essas mesmas verificações
automaticamente em cada PR.

## Reportando bugs

Abra uma issue usando o template de bug, incluindo passos para reproduzir,
comportamento esperado e o que de fato aconteceu.
