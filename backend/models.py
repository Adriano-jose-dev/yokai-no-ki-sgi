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
