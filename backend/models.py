"""
Modelos SQLAlchemy — SGI-YKR.

Todas as entidades do domínio (Aluno, Contrato, Sessao, Pagamento, Presenca).
Comportamento e defaults idênticos ao monolito original.
"""

from datetime import date, datetime

from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    LargeBinary,
)

from database import Base


class Aluno(Base):
    __tablename__ = "alunos"
    id_matricula = Column(String, primary_key=True, index=True)
    nome = Column(String, nullable=False)
    status_atividade = Column(String, default="Ativo")
    data_inicio = Column(Date, default=date.today)
    graduacao_atual = Column(String, default="Ashigaru")
    data_ultima_graduacao = Column(Date, default=date.today)
    data_nascimento = Column(Date, nullable=True)
    whatsapp = Column(String, nullable=True)
    email = Column(String, nullable=True)
    endereco = Column(String, nullable=True)
    nacionalidade = Column(String, default="Brasileira")
    naturalidade = Column(String, nullable=True)
    nome_pai = Column(String, nullable=True)
    nome_mae = Column(String, nullable=True)
    contato_emergencia_nome = Column(String, nullable=True)
    contato_emergencia_parentesco = Column(String, nullable=True)
    contato_emergencia_telefone = Column(String, nullable=True)
    historico_marcial = Column(String, nullable=True)
    equipamento_proprio = Column(Boolean, default=False)
    termo_risco_assinado = Column(Boolean, default=False)
    restricao_medica = Column(String, nullable=True)
    autorizacao_imagem = Column(Boolean, default=False)
    hora_flexivel = Column(Boolean, default=False)
    diario_pedagogico = Column(String, default="[]")
    modo_treino = Column(String, default="Modo Dojo")
    acordo_contratual = Column(String, nullable=True)


class Contrato(Base):
    __tablename__ = "contratos"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    id_aluno = Column(String, ForeignKey("alunos.id_matricula"))
    modelo_plano = Column(String, default="Horas Livres")
    valor_base = Column(Float, default=20.0)
    valor_contratual_fixo = Column(Float, default=20.0)
    taxa_admissao_saldo = Column(Float, default=50.0)
    horas_franquia = Column(Integer, default=3)
    observacao_financeira = Column(String, nullable=True)
    inclui_shokubai = Column(Boolean, default=False)
    dia_vencimento = Column(Integer, default=10)


class Sessao(Base):
    __tablename__ = "sessoes"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    id_aluno = Column(String, ForeignKey("alunos.id_matricula"))
    hora_entrada = Column(DateTime, default=datetime.now)
    hora_saida = Column(DateTime, nullable=True)
    valor_apurado = Column(Float, default=0.0)
    desconto_aplicado = Column(Float, default=0.0)
    diario_sensei = Column(String, nullable=True)
    pago = Column(Boolean, default=False)


class Pagamento(Base):
    __tablename__ = "pagamentos"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    id_aluno = Column(String, ForeignKey("alunos.id_matricula"))
    data_pagamento = Column(DateTime, default=datetime.now)
    valor = Column(Float, nullable=False)
    metodo = Column(String, nullable=False)


class Presenca(Base):
    __tablename__ = "presencas"
    id = Column(Integer, primary_key=True, autoincrement=True)
    id_aluno = Column(String, ForeignKey("alunos.id_matricula"))
    data = Column(Date, default=date.today)
    status = Column(String, default="Ausente")


class Usuario(Base):
    """Usuário do sistema (autenticação). O `role` já viaja no token para
    permitir, no futuro, um papel `sensei` restrito ao Tatame sem redesenho."""

    __tablename__ = "usuarios"
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String, unique=True, index=True, nullable=False)
    senha_hash = Column(String, nullable=False)
    role = Column(String, default="admin", nullable=False)
    ativo = Column(Boolean, default=True, nullable=False)


class EncerramentoMatricula(Base):
    """Registro de **encerramento definitivo** de matrícula (fim de vínculo).

    Diferente da *suspensão* (soft, reversível, via `status_atividade`), o
    encerramento inicia uma janela de retenção de 30 dias durante a qual:
    - o dossiê PDF completo do aluno fica disponível para download;
    - a operação pode ser **revogada** por um admin, restaurando o aluno ao
      `estado_anterior`;
    - ao fim da janela, um job do APScheduler faz o **Hard Delete** do registro
      do aluno (conformidade com a LGPD: dados pessoais não são retidos sem
      vínculo ativo).

    O PDF é guardado aqui (`dossie_pdf`) para que o expurgo apague o registro do
    aluno e o próprio documento de uma vez só, sem arquivos órfãos no disco.

    Relação 1:1 com `Aluno` — enquanto existe este registro, o aluno está
    "encerrado" (status_atividade = 'Encerrado') e some das telas do dia a dia.
    """

    __tablename__ = "encerramentos_matricula"
    id = Column(Integer, primary_key=True, autoincrement=True)
    id_aluno = Column(
        String, ForeignKey("alunos.id_matricula"), unique=True, index=True
    )
    # Status em que o aluno estava antes do encerramento (p/ revogação).
    estado_anterior = Column(String, nullable=False)
    data_encerramento = Column(DateTime, default=datetime.now, nullable=False)
    # Data a partir da qual o expurgo (Hard Delete) pode ocorrer.
    data_expurgo = Column(Date, nullable=False)
    # Dossiê PDF completo, gerado no ato do encerramento.
    dossie_pdf = Column(LargeBinary, nullable=True)
    dossie_nome = Column(String, nullable=True)
    # Quem encerrou (username do admin), para auditoria.
    encerrado_por = Column(String, nullable=True)


# =============================================================================
# Domínio TURMAS (Fase 1 do roadmap de evolução).
#
# Modularização leve: os modelos novos vivem a partir daqui, agrupados por
# domínio, sem reorganizar os modelos legados acima.
# =============================================================================


class Turma(Base):
    """Turma = molde de uma aula recorrente.

    Base para o Modo Tatame (Fase 1d) e para o Financeiro (Fase 2, onde o
    `valor_base` da turma e as ocorrências do calendário geram as cobranças).

    - `tipo_pagamento`: 'Mensalidade' ou 'Hora-Aula' (define cronômetro e layout
      do Modo Tatame, e o modelo de cobrança).
    - `classe`: 'Dojo' ou 'Legado' — controle organizacional. Única regra
      funcional: um aluno de Legado pode assistir aulas de Dojo gratuitamente
      (participa como ocorrente, sem cobrança).
    - `valor_base`: valor da hora-aula desta turma (usado no cálculo financeiro).
    - `recorrencia_rrule`: regra de recorrência no padrão iCalendar/RRULE (ex.:
      'FREQ=WEEKLY;BYDAY=SA' para todo sábado). Suporta qualquer regra.
    - `recorrencia_descricao`: texto legível da recorrência, para exibição.
    - `hora_inicio` / `hora_fim`: janela da aula (define a duração prevista).
    """

    __tablename__ = "turmas"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    nome = Column(String, nullable=False)
    tipo_pagamento = Column(String, nullable=False, default="Mensalidade")
    classe = Column(String, nullable=False, default="Dojo")
    valor_base = Column(Float, nullable=False, default=20.0)
    recorrencia_rrule = Column(String, nullable=True)
    recorrencia_descricao = Column(String, nullable=True)
    hora_inicio = Column(String, nullable=True)  # "HH:MM"
    hora_fim = Column(String, nullable=True)      # "HH:MM"
    ativo = Column(Boolean, default=True, nullable=False)


class TurmaMatricula(Base):
    """Associação aluno↔turma, com o papel do aluno naquela turma.

    - `papel = 'matriculado'`: o aluno pertence à turma e é cobrado por ela.
    - `papel = 'ocorrente'`: o aluno participa sem ser o vínculo principal
      (ex.: aluno de Legado assistindo Dojo). `gratuito=True` nesse caso.

    Um aluno pode ter UMA matrícula principal e VÁRIAS participações como
    ocorrente em outras turmas.
    """

    __tablename__ = "turma_matriculas"
    id = Column(Integer, primary_key=True, autoincrement=True)
    id_turma = Column(Integer, ForeignKey("turmas.id"), index=True, nullable=False)
    id_aluno = Column(
        String, ForeignKey("alunos.id_matricula"), index=True, nullable=False
    )
    papel = Column(String, nullable=False, default="matriculado")
    gratuito = Column(Boolean, default=False, nullable=False)


class OcorrenciaAula(Base):
    """Ocorrência de aula = uma turma numa data específica (Fase 1b).

    É o que o **calendário** lista (com estado) e o que o **financeiro** (Fase 2)
    soma para calcular a mensalidade (somando as horas das ocorrências
    `prevista`/`realizada`, descartando as `cancelada`).

    - `estado`: 'prevista' (gerada e ainda não ocorreu), 'realizada' (aula
      aconteceu), 'cancelada' (escola cancelou — sai do cálculo financeiro).
    - `origem`: 'recorrencia' (gerada da RRULE da turma) ou 'avulsa' (criada à
      mão, ex.: remarcação de hora-aula).
    - `hora_inicio`/`hora_fim`: snapshot da janela (herdado da turma na geração,
      mas editável por ocorrência). Define a **duração prevista**.
    - `duracao_real_min`: minutos cronometrados no Modo Tatame (validação do
      professor; NÃO entra no cálculo financeiro da mensalidade).
    """

    __tablename__ = "ocorrencias_aula"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    id_turma = Column(Integer, ForeignKey("turmas.id"), index=True, nullable=False)
    data = Column(Date, nullable=False, index=True)
    hora_inicio = Column(String, nullable=True)  # "HH:MM"
    hora_fim = Column(String, nullable=True)      # "HH:MM"
    estado = Column(String, nullable=False, default="prevista")
    origem = Column(String, nullable=False, default="recorrencia")
    observacao = Column(String, nullable=True)
    duracao_real_min = Column(Integer, nullable=True)


# =============================================================================
# Domínio FINANCEIRO — Conta Corrente (Fase 2 do roadmap de evolução).
#
# A conta corrente do aluno é um razão (ledger) de lançamentos. Cada linha é um
# débito (o que o aluno deve) ou um crédito (o que o aluno pagou/tem a favor). O
# saldo da conta é a soma algébrica: crédito - débito aberto.
#
# Conceito-chave (steering, Fase 2):
# - A mensalidade NÃO é um pacote fixo: é gerada somando `valor_base × horas` das
#   ocorrências PREVISTAS/REALIZADAS do mês no calendário (aulas CANCELADAS pela
#   escola saem da conta e reduzem o valor). Falta do aluno NÃO altera o valor.
# - O débito só "existe" quando é GERADO (mensalidade no vencimento; hora-aula
#   realizada e não paga; taxa de admissão). Antes disso é só previsão.
# - Crédito (pago a mais) abate débito no momento em que o débito é gerado.
# =============================================================================


class Lancamento(Base):
    """Lançamento da conta corrente do aluno (uma linha do razão).

    - `tipo`: 'debito' (o aluno deve) ou 'credito' (pagamento/saldo a favor).
    - `categoria`: 'mensalidade', 'hora_aula', 'taxa_admissao', 'pagamento' ou
      'ajuste'.
    - `valor`: sempre positivo; o sinal é dado por `tipo`.
    - `valor_aberto`: parte ainda não quitada de um débito (0 quando quitado).
      Para créditos, representa o saldo ainda disponível para abater débitos.
    - `status`: 'aberto', 'parcial' ou 'quitado' (débitos); créditos usam
      'aberto' (saldo disponível) ou 'quitado' (crédito já consumido).
    - `mes_referencia`: 'YYYY-MM' da competência (mensalidade), para idempotência
      na geração mensal.
    - `id_ocorrencia`: ocorrência de origem (hora-aula), quando aplicável.
    - `data_vencimento`: quando o débito vence (dispara a trava de inadimplência).
    """

    __tablename__ = "lancamentos"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    id_aluno = Column(
        String, ForeignKey("alunos.id_matricula"), index=True, nullable=False
    )
    tipo = Column(String, nullable=False)  # 'debito' | 'credito'
    categoria = Column(String, nullable=False, default="ajuste")
    valor = Column(Float, nullable=False, default=0.0)
    valor_aberto = Column(Float, nullable=False, default=0.0)
    status = Column(String, nullable=False, default="aberto")
    descricao = Column(String, nullable=True)
    data_competencia = Column(Date, default=date.today, nullable=False)
    data_vencimento = Column(Date, nullable=True)
    mes_referencia = Column(String, nullable=True, index=True)  # 'YYYY-MM'
    id_ocorrencia = Column(
        Integer, ForeignKey("ocorrencias_aula.id"), nullable=True, index=True
    )
    metodo = Column(String, nullable=True)  # método do pagamento (créditos)
    criado_em = Column(DateTime, default=datetime.now, nullable=False)


class AbonoFalta(Base):
    """Abono de falta justificada — SOMENTE mensalistas (steering, Fase 2).

    É puramente sobre presença/penalidade: permite que o aluno falte de forma
    justificada sem penalidade. **NÃO altera o valor da mensalidade** (a única
    coisa que reduz o valor é o cancelamento de aula pela escola).
    """

    __tablename__ = "abonos_falta"
    id = Column(Integer, primary_key=True, autoincrement=True)
    id_aluno = Column(
        String, ForeignKey("alunos.id_matricula"), index=True, nullable=False
    )
    id_ocorrencia = Column(
        Integer, ForeignKey("ocorrencias_aula.id"), nullable=True, index=True
    )
    data = Column(Date, default=date.today, nullable=False)
    justificativa = Column(String, nullable=True)
    autor = Column(String, nullable=True)  # username do admin que abonou
    criado_em = Column(DateTime, default=datetime.now, nullable=False)
