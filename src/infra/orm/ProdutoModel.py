# Heliton
from src.infra import database
from sqlalchemy import Column, VARCHAR, Integer, Float, LargeBinary

# ORM
class ProdutoDB(database.Base):
    __tablename__ = 'tb_produto'

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    nome = Column(VARCHAR(100), nullable=False)
    descricao = Column(VARCHAR(200), nullable=False)
    foto = Column(LargeBinary, nullable=True)
    valor_unitario = Column(Float, nullable=False)
