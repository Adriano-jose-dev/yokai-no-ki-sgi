"""
Schemas Pydantic (moldes de recepção) — SGI-YKR.

Modelos de entrada das rotas. Idênticos aos do monolito original.
"""

from datetime import date
from typing import Optional, List

from pydantic import BaseModel


class SessaoRequest(BaseModel):
    id_matricula: str


class StopSessaoRequest(BaseModel):
    id_matricula: str
    diario_sensei: Optional[str] = None
    desconto_aplicado: Optional[float] = 0.0


class NovoAlunoRequest(BaseModel):
    nome: str
    data_nascimento: Optional[date] = None
    whatsapp: Optional[str] = None
    email: Optional[str] = None
    endereco: Optional[str] = None
    nacionalidade: Optional[str] = "Brasileira"
    naturalidade: Optional[str] = None
    nome_pai: Optional[str] = None
    nome_mae: Optional[str] = None
    contato_emergencia_nome: Optional[str] = None
    contato_emergencia_parentesco: Optional[str] = None
    contato_emergencia_telefone: Optional[str] = None
    historico_marcial: Optional[str] = None
    equipamento_proprio: Optional[bool] = False
    termo_risco_assinado: Optional[bool] = False
    restricao_medica: Optional[str] = None
    autorizacao_imagem: Optional[bool] = False
    modelo_plano: str = "Horas Livres"
    valor_base_contrato: float = 20.0
    status_atividade: str = "Ativo"
    taxa_admissao_valor: float = 50.0
    inclui_shokubai: bool = False
    modo_treino: str = "Modo Dojo"
    dia_vencimento: Optional[int] = 10
    acordo_contratual: Optional[str] = None


class EditarFichaRequest(BaseModel):
    nome: str
    data_nascimento: Optional[date] = None
    whatsapp: Optional[str] = None
    email: Optional[str] = None
    endereco: Optional[str] = None
    nacionalidade: str
    naturalidade: Optional[str] = None
    nome_pai: Optional[str] = None
    nome_mae: Optional[str] = None
    equipamento_proprio: bool
    historico_marcial: Optional[str] = None
    restricao_medica: Optional[str] = None
    modo_treino: str
    graduacao_atual: str
    acordo_contratual: Optional[str] = None


class EditarContratoRequest(BaseModel):
    modelo_plano: str
    valor_base: float
    valor_contratual_fixo: float
    inclui_shokubai: bool
    dia_vencimento: int
    observacao_financeira: Optional[str] = None


class ChamadaRequest(BaseModel):
    id_aluno: str
    status: str


class ListarChamadaRequest(BaseModel):
    data: date


class PresencaItem(BaseModel):
    id_aluno: str
    status: str


class PresencaBulkRequest(BaseModel):
    data: date
    presencas: List[PresencaItem]


class ReceberPagamentoRequest(BaseModel):
    id_matricula: str
    valor_pago: float
    metodo: str


class PromoverRequest(BaseModel):
    nova_graduacao: str


class StatusRequest(BaseModel):
    novo_status: str


class UpdateNotaRequest(BaseModel):
    nota: Optional[str] = None


class AtualizarValorBaseRequest(BaseModel):
    valor_base: float


class LoginRequest(BaseModel):
    username: str
    senha: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# --- Turmas (Fase 1 do roadmap) ---


class MatriculaTurmaItem(BaseModel):
    id_aluno: str
    papel: str = "matriculado"  # 'matriculado' ou 'ocorrente'
    gratuito: bool = False


class NovaTurmaRequest(BaseModel):
    nome: str
    tipo_pagamento: str = "Mensalidade"  # 'Mensalidade' ou 'Hora-Aula'
    classe: str = "Dojo"  # 'Dojo' ou 'Legado'
    valor_base: float = 20.0
    recorrencia_rrule: Optional[str] = None
    recorrencia_descricao: Optional[str] = None
    hora_inicio: Optional[str] = None
    hora_fim: Optional[str] = None
    alunos: List[MatriculaTurmaItem] = []


class EditarTurmaRequest(BaseModel):
    nome: Optional[str] = None
    tipo_pagamento: Optional[str] = None
    classe: Optional[str] = None
    valor_base: Optional[float] = None
    recorrencia_rrule: Optional[str] = None
    recorrencia_descricao: Optional[str] = None
    hora_inicio: Optional[str] = None
    hora_fim: Optional[str] = None
    ativo: Optional[bool] = None


class VincularAlunoTurmaRequest(BaseModel):
    id_aluno: str
    papel: str = "matriculado"
    gratuito: bool = False


# --- Ocorrências de aula / Calendário (Fase 1b) ---


class GerarOcorrenciasRequest(BaseModel):
    """Intervalo para gerar ocorrências da recorrência de uma turma."""
    data_inicio: date
    data_fim: date


class NovaOcorrenciaAvulsaRequest(BaseModel):
    id_turma: int
    data: date
    hora_inicio: Optional[str] = None
    hora_fim: Optional[str] = None
    observacao: Optional[str] = None


class EditarOcorrenciaRequest(BaseModel):
    data: Optional[date] = None
    hora_inicio: Optional[str] = None
    hora_fim: Optional[str] = None
    estado: Optional[str] = None  # prevista | realizada | cancelada
    observacao: Optional[str] = None
    duracao_real_min: Optional[int] = None


# --- Modo Tatame por turma (Fase 1d) ---


class PresencaOcorrenciaRequest(BaseModel):
    """Marca presença/ausência de um aluno numa ocorrência (turma Mensalidade)."""
    id_aluno: str
    presente: bool
    diario_sensei: Optional[str] = None


class DuracaoRealRequest(BaseModel):
    """Registra a duração real cronometrada da ocorrência (cronômetro global).

    É validação do professor; NÃO entra no cálculo financeiro da mensalidade.
    """
    duracao_real_min: int
