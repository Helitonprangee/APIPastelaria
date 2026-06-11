# Heliton
from sqlalchemy import Column, Integer, DECIMAL, DateTime, ForeignKey
from  infra.database import Base


class RecebimentoDB(Base):
    __tablename__ = "tb_recebimento"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    funcionario_id = Column(Integer, ForeignKey("tb_funcionario.id", ondelete="RESTRICT"), nullable=False)
    cliente_id = Column(Integer, ForeignKey("tb_cliente.id", ondelete="RESTRICT"), nullable=True)
    desconto_valor = Column(DECIMAL(10, 2), nullable=True, default=0)
    acrescimo_valor = Column(DECIMAL(10, 2), nullable=True, default=0)
    subtotal_geral = Column(DECIMAL(10, 2), nullable=False)
    valor_final = Column(DECIMAL(10, 2), nullable=False)
    data_hora = Column(DateTime, nullable=False)


class RecebimentoComandaDB(Base):
    __tablename__ = "tb_recebimento_comanda"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    recebimento_id = Column(Integer, ForeignKey("tb_recebimento.id", ondelete="CASCADE"), nullable=False)
    comanda_id = Column(Integer, ForeignKey("tb_comanda.id", ondelete="RESTRICT"), nullable=False)
