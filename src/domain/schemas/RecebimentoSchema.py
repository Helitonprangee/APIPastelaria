from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime

from  domain.schemas.FuncionarioSchema import FuncionarioResponse
from  domain.schemas.ClienteSchema import ClienteResponse


class RecebimentoCompletoRequest(BaseModel):
    comandas_ids: List[int]
    cliente_id: Optional[int] = None
    funcionario_id: int
    desconto_valor: Optional[float] = None
    acrescimo_valor: Optional[float] = None


class ComandaPagaResponse(BaseModel):
    id: int
    comanda: str
    total: float
    quantidade_produtos: int


class RecebimentoCompletoResponse(BaseModel):
    sucesso: bool
    mensagem: str
    recebimento_id: int
    comandas_pagas: List[ComandaPagaResponse]
    subtotal_geral: float
    desconto_total: float
    acrescimo_total: float
    valor_final: float
    cliente: Optional[ClienteResponse] = None
    funcionario: FuncionarioResponse
    data_hora: datetime


class RecebimentoDashboardItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    comanda: str
    status: int
    cliente: Optional[ClienteResponse] = None
    total: float
    quantidade_produtos: int
    data_hora: datetime


class RecebimentoListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    funcionario_id: int
    funcionario: Optional[FuncionarioResponse] = None
    cliente_id: Optional[int] = None
    cliente: Optional[ClienteResponse] = None
    desconto_valor: Optional[float] = None
    acrescimo_valor: Optional[float] = None
    subtotal_geral: float
    valor_final: float
    data_hora: datetime


class RecebimentoUpdate(BaseModel):
    desconto_valor: Optional[float] = None
    acrescimo_valor: Optional[float] = None
    cliente_id: Optional[int] = None
