# Heliton
from  infra import database
from sqlalchemy import Column, VARCHAR, CHAR, Integer

# ORM
class ClienteDB(database.Base):
    __tablename__ = 'tb_cliente'

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    nome = Column(VARCHAR(100), nullable=False)
    cpf = Column(CHAR(11), unique=True, nullable=False, index=True)
    telefone = Column(CHAR(11), nullable=False)


