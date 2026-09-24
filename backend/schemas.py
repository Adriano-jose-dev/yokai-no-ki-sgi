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
