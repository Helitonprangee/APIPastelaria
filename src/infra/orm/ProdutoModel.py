from sqlalchemy import Column, Integer, String, Float, LargeBinary
from infra.database import Base

class ProdutoDB(Base):
    __tablename__ = "produto"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    nome = Column(String(255), nullable=False, index=True)
    descricao = Column(String(255), nullable=False)
    foto = Column(LargeBinary, nullable=True)
    valor_unitario = Column(Float, nullable=False)