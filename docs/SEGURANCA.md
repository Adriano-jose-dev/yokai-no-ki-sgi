# Segurança — Levantamento e Plano de Ação (SGI-YKR)

> Levantamento das práticas de segurança usadas no mercado e o **recorte
> aplicado ao SGI-YKR**: o que já temos, o que falta, por quê e como fazer.
> Documento vivo — a cada item implementado, marcar como feito.
>
> **Contexto crítico:** o sistema trata **dados de saúde (anamnese)** de alunos,
> incluindo **menores de idade**. Isso eleva o nível de cuidado exigido (LGPD /
> dados sensíveis) acima de um CRUD comum.

---

## Parte 1 — Levantamento de mercado

### Frameworks e padrões de referência

- **OWASP Top 10** — as 10 categorias de vulnerabilidade web mais críticas.
  Mínimo esperado de qualquer time de desenvolvimento.
- **OWASP ASVS** — checklist de verificação por níveis (1–3); mede "quão seguro".
- **NIST CSF** e **ISO/IEC 27001** — frameworks organizacionais de governança e
  gestão de risco.
- **CIS Benchmarks** — guias de *hardening* de SO, Docker, banco e nuvem.
- **LGPD / GDPR** — leis de proteção de dados. **LGPD é obrigatória** aqui.

### Metodologias / processos

- **Secure SDLC / Shift-Left** — segurança desde o design (threat modeling,
  revisão com viés de segurança), não no fim.
- **DevSecOps** — segurança automatizada no pipeline CI/CD.
- **Menor privilégio** — cada ator com o acesso mínimo necessário.
- **Defense in depth** — camadas; se uma falha, outra segura.
- **Secure by default** — o estado padrão é o seguro.

### Medidas técnicas usuais

- **Auth/sessão:** hash forte (bcrypt/argon2), MFA, access token curto +
  refresh rotativo, rate limiting / lockout no login.
- **Autorização:** RBAC + checagem de **propriedade do recurso** (anti-IDOR).
- **Dados:** TLS/HTTPS em trânsito, criptografia em repouso, gestão de segredos
  (vault/secrets manager), minimização e retenção (LGPD).
- **Hardening app:** validação de entrada/saída (anti-injeção), security headers
  (CSP, HSTS...), CORS restrito, proteção XSS/CSRF.
- **Supply chain / operação:** SCA (`pip-audit`, `npm audit`, Dependabot), SAST
  (CodeQL, Bandit), logging/auditoria, backups testados, WAF/rate limit na borda.

---

## Parte 2 — Estado atual do SGI-YKR

### ✅ O que já está implementado

| Medida | Onde |
| --- | --- |
| Hash **bcrypt** de senha | `business/auth.py` |
| **JWT** com `role` no token (base de RBAC) | `business/auth.py` · `requer_papel` |
| Configuração por **variáveis de ambiente** | `config.py` + `.env.example` |
| **CORS** parametrizável por ambiente | `config.py` · `main.py` |
| **ORM parametrizado** (anti-SQL-injection) | SQLAlchemy em todos os routers |
| **Auditoria** de ações sensíveis | `business/auditoria.py` |
| Soft delete + **expurgo LGPD** + dossiê | `routers/encerramento.py` |
| Interceptor faz **logout no 401** | `auth.interceptor.ts` |
| `.env` fora do versionamento | `.gitignore` |

### ⚠️ O que falta ou está frágil

Priorizado por **risco × esforço**. Cada item mapeia uma categoria OWASP e/ou a
LGPD.

---

### 🔴 Prioridade ALTA — antes de qualquer acesso externo

#### S1. Segredos padrão / credenciais no código
- **Problema:** `config.py` tem `JWT_SECRET` padrão (`"dev-secret-inseguro..."`);
  `create_admin.py` tem usuário/senha fixos. Se o secret padrão for usado em
  produção, **qualquer um forja um token admin válido**.
- **Como:** aplicação **recusa subir** em produção se `JWT_SECRET` for o padrão
  (fail-safe); credenciais iniciais via variáveis de ambiente; confirmar `.env`
  no `.gitignore`.
- **OWASP:** A05 (Security Misconfiguration), A07 (Auth Failures).
- **Esforço:** baixo.

#### S2. Senhas de MVP fracas e sem política de troca
- **Problema:** os admins iniciais compartilham uma senha fraca; nada obriga a
  troca.
- **Como:** gerar senha forte no provisionamento; flag "troca obrigatória no 1º
  login" no modelo `Usuario`; validar comprimento/força mínimos.
- **OWASP:** A07.
- **Esforço:** baixo-médio.

#### S3. Sem rate limiting no login
- **Problema:** tentativas de senha ilimitadas → força bruta.
- **Como:** `slowapi` (ou middleware próprio) limitando `/auth/login` por IP/
  usuário, com bloqueio temporário; registrar tentativas na auditoria.
- **OWASP:** A07.
- **Esforço:** baixo.

#### S4. Token em `localStorage` + HTTPS não forçado
- **Problema:** token no `localStorage` é legível por XSS; sem HTTPS, token e
  senha trafegam em claro.
- **Como:** ideal de mercado é **cookie httpOnly + SameSite** (JS não lê) + CSRF
  token — mudança de arquitetura de auth, feita com cuidado. Alternativa mais
  barata: **access token curto + refresh token** (reduz a janela de dano). HTTPS
  é obrigatório no deploy.
- **OWASP:** A02 (Cryptographic Failures), A07.
- **Esforço:** médio-alto.

---

### 🟡 Prioridade MÉDIA

#### S5. Security headers
- **Como:** middleware adicionando HSTS, CSP, X-Content-Type-Options,
  X-Frame-Options, Referrer-Policy. Revisar `innerHTML` no Angular.
- **OWASP:** A05.
- **Esforço:** baixo.

#### S6. Autorização por propriedade de recurso (anti-IDOR) — pré-requisito da Fase 5
- **Problema:** hoje só há `admin`, então "todos veem tudo" é tolerável. Com
  `aluno`/`professor` (Fase 5), um aluno **não pode** ler dados de outro — erro
  fácil de cometer (IDOR).
- **Como:** padrão "o recurso pertence ao dono do token?" em cada endpoint
  sensível + **testes de autorização cruzada** (aluno A × dados de B → 403).
- **OWASP:** A01 (Broken Access Control) — a nº 1 da lista.
- **Esforço:** médio (parte da Fatia 5a).

#### S7. SCA + SAST no CI
- **Como:** adicionar `pip-audit` e `npm audit` + `bandit` ao GitHub Actions já
  existente; ligar o Dependabot no repositório.
- **OWASP:** A06 (Vulnerable & Outdated Components).
- **Esforço:** baixo. *(Excelente material para o artigo de portfólio.)*

#### S8. Criptografia em repouso de dados sensíveis
- **Problema:** anamnese = dado de saúde de menores.
- **Como:** em produção, banco gerenciado com *encryption-at-rest* ativada;
  opcionalmente, criptografar o campo de anamnese na aplicação.
- **LGPD.**
- **Esforço:** baixo (infra) a médio (cripto em app).

---

### 🟢 Prioridade de PRODUÇÃO (no deploy)

#### S9. Infraestrutura segura
- HTTPS/TLS obrigatório, WAF e rate limit na borda, **secrets manager**,
  **backups testados** + plano de recuperação, monitoramento/alertas, logs
  centralizados. Entra no momento de hospedar na nuvem.

---

## Parte 3 — Sequência recomendada

Pensada para **máximo valor com baixo risco** e para render boa narrativa no
artigo de portfólio.

1. **S1, S2, S3, S5, S7** — baixo esforço, alto impacto, com testes verdes.
   Juntos demonstram aplicação prática do **OWASP Top 10** num projeto real.
2. **S6** junto da **Fatia 5a** (quando os papéis `aluno`/`professor` entrarem).
3. **S4, S8, S9** — documentados como "arquitetura de produção" e implementados
   no deploy na nuvem.

> **Regra de ouro deste projeto:** nada de segurança **ofensiva**. Todo o escopo
> aqui é **defensivo** — proteger a aplicação, os dados dos alunos e a
> conformidade com a LGPD.

---

## Checklist de acompanhamento

- [ ] S1 — Remover segredos padrão / credenciais do código (fail-safe de produção)
- [ ] S2 — Política de senha + troca obrigatória no 1º login
- [ ] S3 — Rate limiting no login
- [ ] S4 — Revisar armazenamento do token (cookie httpOnly / refresh token) + HTTPS
- [ ] S5 — Security headers
- [ ] S6 — Autorização por propriedade de recurso + testes de 403 cruzado
- [ ] S7 — SCA (`pip-audit`/`npm audit`) + SAST (`bandit`) no CI + Dependabot
- [ ] S8 — Criptografia em repouso dos dados sensíveis
- [ ] S9 — Hardening de infraestrutura no deploy (HTTPS, WAF, secrets manager, backups)
