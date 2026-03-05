from pydantic import BaseModel

#Heliton marcondes prange

class Produto(BaseModel):
    id_produto: int = None
    nome: str
    descricao: str
    foto: bytes = None
    valor_unitario: float
    