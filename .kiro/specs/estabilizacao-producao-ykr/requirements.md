# Requisitos — Estabilização e Produção do SGI-YKR

## Introdução

Esta Spec cobre a evolução do MVP do SGI-YKR (plataforma de gestão do Dojo
Yōkai no Ki Ryūha) em duas fases:

- **Fase B — Estabilização:** corrigir divergências entre o código e as regras
  de negócio, eliminar bugs e duplicações, e organizar a base de código sem
  alterar o comportamento correto já existente.
- **Fase A — Produção:** preparar a aplicação para deploy em nuvem de baixo
  custo, com autenticação, configuração por ambiente, banco PostgreSQL,
  migrations e agendador da trava de inadimplência.

A stack é mantida: Python/FastAPI/SQLAlchemy no back-end e Angular/TailwindCSS
no front-end. As regras de negócio do arquivo de steering
`regras-negocio-ykr.md` são a fonte da verdade e prevalecem sobre o código atual
em caso de conflito.

---

## Fase B — Estabilização

### Requisito 1 — Franquia de horas dinâmica (Mensalidade)

**História:** Como gestor da escola, quero que a franquia de horas da
Mensalidade venha de um único lugar confiável, para que a regra das 3 horas seja
aplicada de forma consistente e sem valores mágicos no código.

#### Critérios de Aceitação

1. QUANDO um contrato do tipo `Mensalidade` é criado, O SISTEMA DEVE definir
   `horas_franquia` com valor padrão `3`.
2. QUANDO uma sessão de um aluno no plano `Mensalidade` é finalizada, O SISTEMA
   DEVE calcular o custo como `(horas_decimais - contrato.horas_franquia) *
   valor_base`, consumindo o campo do banco em vez de um número fixo no código.
3. SE `horas_decimais` for menor ou igual a `contrato.horas_franquia`, ENTÃO O
   SISTEMA DEVE registrar custo `0` (nunca negativo).
4. O SISTEMA NÃO DEVE conter o valor de franquia (3 ou 4) escrito diretamente na
   lógica de cálculo de `finalizar_sessao`.
5. QUANDO contratos legados existentes tiverem `horas_franquia = 4`, O SISTEMA
   DEVE migrá-los para `3` via script/migration.

### Requisito 2 — Regra de trava automática unificada

**História:** Como mantenedor do código, quero que a regra de inadimplência
exista em um único ponto, para que leitura de progresso e edição de contrato se
comportem de forma idêntica.

#### Critérios de Aceitação

1. O SISTEMA DEVE conter uma única função responsável por avaliar e aplicar a
   trava automática de inadimplência.
2. QUANDO a rota de progresso do aluno é acionada, O SISTEMA DEVE usar essa
   função única para avaliar a trava.
3. QUANDO a rota de edição de contrato é acionada, O SISTEMA DEVE usar a mesma
   função única.
4. QUANDO um aluno `Mensalidade` está em atraso superior a `dia_vencimento + 5
   dias` E não possui `[ACORDO]` em `observacao_financeira`, O SISTEMA DEVE
   mudar o status para `Trancado` e prefixar `[TRAVA AUTOMÁTICA]` na observação.
5. QUANDO a trava é aplicada e existe uma sessão de tatame aberta, O SISTEMA DEVE
   encerrar a sessão imediatamente (`hora_saida = agora`).
6. SE `observacao_financeira` contém `[ACORDO]`, ENTÃO O SISTEMA NÃO DEVE
   bloquear o aluno mesmo em atraso.
7. O comportamento observável após a unificação DEVE permanecer equivalente ao
   comportamento correto atual (nenhuma regressão nas regras do steering).

### Requisito 3 — Rota de atualização de valor base

**História:** Como secretaria, quero salvar o valor base do contrato pela tela
de detalhe do aluno, para que a alteração persista corretamente.

#### Critérios de Aceitação

1. O SISTEMA DEVE expor um endpoint que atualize o `valor_base` do contrato de um
   aluno.
2. QUANDO o front-end chama a rota de valor base com um valor válido, O SISTEMA
   DEVE persistir o novo valor e retornar confirmação.
3. SE o aluno ou contrato não existir, ENTÃO O SISTEMA DEVE retornar um erro HTTP
   apropriado (404).
4. O contrato de rota (método, caminho, corpo) DEVE corresponder exatamente ao
   que o componente `admin-detail` já invoca.

### Requisito 4 — Soft Delete formalizado

**História:** Como gestor, quero desativar alunos sem perder o histórico, para
respeitar a regra de nunca excluir registros do banco.

#### Critérios de Aceitação

1. O SISTEMA NÃO DEVE oferecer nenhuma operação de exclusão física (hard delete)
   de alunos.
2. O SISTEMA DEVE oferecer uma operação de desativação que altera o
   `status_atividade` do aluno para `Inativo`.
3. QUANDO um aluno é desativado E possui sessão de tatame aberta, O SISTEMA DEVE
   encerrar essa sessão.
4. QUANDO listas operacionais (Tatame, chamada) são carregadas, O SISTEMA DEVE
   omitir alunos `Inativo`.
5. QUANDO um aluno é desativado, O SISTEMA DEVE preservar seus registros
   históricos (sessões, pagamentos, presenças).

### Requisito 5 — Configuração de URL da API por ambiente (front-end)

**História:** Como desenvolvedor, quero que o front-end use a URL da API a partir
do arquivo de environment, para que o mesmo código funcione em dev e em produção.

#### Critérios de Aceitação

1. O SISTEMA (front-end) NÃO DEVE conter a URL da API escrita diretamente nos
   componentes.
2. O SISTEMA DEVE ler a URL base da API a partir dos arquivos de `environments`
   do Angular.
3. QUANDO compilado em modo desenvolvimento, O SISTEMA DEVE usar a URL local
   (`http://127.0.0.1:8000`).
4. QUANDO compilado em modo produção, O SISTEMA DEVE usar a URL de produção
   configurada.
5. Todos os componentes que hoje chamam a API DEVEM passar a usar a fonte única
   de configuração.

---

## Fase A — Produção

### Requisito 6 — Autenticação (usuário único, extensível)

**História:** Como gestão da escola, quero acessar o sistema com login protegido,
para que apenas pessoas autorizadas operem a plataforma.

#### Critérios de Aceitação

1. O SISTEMA DEVE oferecer um endpoint de login que valide credenciais e retorne
   um token JWT.
2. QUANDO uma rota protegida é acessada sem token válido, O SISTEMA DEVE retornar
   `401 Não Autorizado`.
3. QUANDO um token válido é fornecido, O SISTEMA DEVE permitir o acesso à rota.
4. O SISTEMA DEVE armazenar a senha de forma segura (hash), nunca em texto puro.
5. A estrutura de autenticação DEVE incluir um conceito de papel (role) no token,
   de modo que um papel `Sensei` restrito ao Tatame possa ser adicionado no
   futuro sem redesenho.
6. QUANDO o token expira, O SISTEMA DEVE exigir novo login.
7. O front-end DEVE armazenar o token e enviá-lo nas requisições às rotas
   protegidas.

### Requisito 7 — CORS restrito

**História:** Como responsável pela segurança, quero limitar as origens que
acessam a API, para reduzir a superfície de ataque em produção.

#### Critérios de Aceitação

1. O SISTEMA NÃO DEVE usar `allow_origins=["*"]` em produção.
2. O SISTEMA DEVE permitir origens a partir de configuração de ambiente.
3. QUANDO em desenvolvimento, O SISTEMA PODE permitir a origem local do Angular.

### Requisito 8 — Banco PostgreSQL com configuração por ambiente

**História:** Como responsável pela infraestrutura, quero que o banco seja
configurável por ambiente, para migrar de SQLite (dev) para PostgreSQL (produção)
sem alterar código.

#### Critérios de Aceitação

1. O SISTEMA DEVE ler a string de conexão do banco a partir de variável de
   ambiente.
2. QUANDO nenhuma variável é fornecida, O SISTEMA PODE usar SQLite local como
   padrão de desenvolvimento.
3. O SISTEMA DEVE ser compatível com PostgreSQL para o ambiente de produção.
4. O SISTEMA NÃO DEVE conter credenciais de banco escritas no código-fonte.

### Requisito 9 — Migrations de esquema (Alembic)

**História:** Como mantenedor, quero versionar mudanças de esquema, para migrar
com segurança de SQLite para PostgreSQL e evoluir o banco.

#### Critérios de Aceitação

1. O SISTEMA DEVE usar uma ferramenta de migration (Alembic) para gerenciar o
   esquema.
2. O SISTEMA DEVE ter uma migration inicial que represente o esquema atual.
3. O SISTEMA DEVE incluir uma migration que corrija `horas_franquia` de `4` para
   `3` nos contratos existentes.
4. O SISTEMA NÃO DEVE depender de `create_all` para evoluir o esquema em
   produção.

### Requisito 10 — Agendador da trava de inadimplência

**História:** Como gestor, quero que a trava de inadimplência seja aplicada
proativamente todo dia, para não depender de alguém abrir uma tela.

#### Critérios de Aceitação

1. O SISTEMA DEVE executar uma tarefa agendada diária que varre os contratos
   `Mensalidade` e aplica a trava conforme a regra unificada (Requisito 2).
2. A tarefa agendada DEVE reutilizar a mesma função única de avaliação de trava,
   sem duplicar a regra.
3. QUANDO a tarefa tranca um aluno com sessão aberta, O SISTEMA DEVE encerrar a
   sessão.
4. A avaliação sob demanda (lazy) DEVE continuar funcionando como rede de
   segurança, sem conflitar com o agendador.

### Requisito 11 — Preparação para deploy em nuvem

**História:** Como equipe, queremos publicar em plataformas de baixo custo, para
validar o sistema em produção com custo mínimo.

#### Critérios de Aceitação

1. O SISTEMA DEVE documentar as variáveis de ambiente necessárias.
2. O SISTEMA (back-end) DEVE declarar suas dependências de forma reproduzível
   (`requirements.txt` ou equivalente).
3. O SISTEMA DEVE poder ser iniciado por um comando padrão de produção
   (servidor ASGI).
4. O front-end DEVE gerar um build de produção consumível por hospedagem
   estática.
5. A documentação DEVE indicar opções de hospedagem de baixo/zero custo para
   back-end, front-end e banco.

### Requisito 12 — Documentação de API navegável

**História:** Como desenvolvedor e como avaliador do portfólio, quero uma
documentação de API interativa e clara, para entender e testar os endpoints sem
ler o código.

#### Critérios de Aceitação

1. O SISTEMA DEVE expor a documentação interativa do FastAPI (Swagger/OpenAPI).
2. Cada endpoint DEVE ter título e descrição legíveis (via `summary`/`tags`).
3. Os endpoints DEVEM estar agrupados por área (`tags`: alunos, tatame, presença,
   pagamentos, auth).
4. A documentação DEVE refletir os schemas de entrada e saída das rotas.
5. O README DEVE apontar como acessar a documentação (`/docs`).

### Requisito 13 — Integração Contínua (CI)

**História:** Como mantenedor, quero que os testes rodem automaticamente a cada
alteração, para garantir que nenhuma regra de negócio regrida e comunicar
maturidade de engenharia.

#### Critérios de Aceitação

1. O SISTEMA DEVE ter um workflow de CI (GitHub Actions) que roda a suíte de
   testes do back-end a cada push e pull request.
2. QUANDO um teste falha, O CI DEVE reportar falha na execução.
3. O workflow DEVE instalar as dependências a partir do arquivo de dependências
   versionado.
4. O README DEVE exibir um badge com o status do CI.
5. O workflow PODE incluir uma verificação de build do front-end Angular.
