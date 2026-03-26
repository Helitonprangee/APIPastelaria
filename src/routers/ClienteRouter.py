# Heliton
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from src.domain.schemas.ClienteSchema import (
    ClienteCreate,
    ClienteUpdate,
    ClienteResponse
)

from src.infra.orm.ClienteModel import ClienteDB
from src.infra.database import get_db

# 🔐 IMPORTANTE
from src.infra.dependencies import get_current_active_user
from src.domain.schemas.AuthSchema import FuncionarioAuth

router = APIRouter()


@router.get("/cliente/", response_model=List[ClienteResponse], tags=["Cliente"])
async def get_cliente(
    db: Session = Depends(get_db),
    current_user: FuncionarioAuth = Depends(get_current_active_user)
):
    return db.query(ClienteDB).all()


@router.get("/cliente/{id}", response_model=ClienteResponse, tags=["Cliente"])
async def get_cliente_id(
    id: int,
    db: Session = Depends(get_db),
    current_user: FuncionarioAuth = Depends(get_current_active_user)
):
    cliente = db.query(ClienteDB).filter(ClienteDB.id == id).first()

    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")

    return cliente


@router.post("/cliente/", response_model=ClienteResponse, tags=["Cliente"])
async def post_cliente(
    cliente_data: ClienteCreate,
    db: Session = Depends(get_db),
    current_user: FuncionarioAuth = Depends(get_current_active_user)
):
    existente = db.query(ClienteDB).filter(ClienteDB.cpf == cliente_data.cpf).first()

    if existente:
        raise HTTPException(status_code=400, detail="CPF já cadastrado")

    novo = ClienteDB(**cliente_data.model_dump())

    db.add(novo)
    db.commit()
    db.refresh(novo)

    return novo


@router.put("/cliente/{id}", response_model=ClienteResponse, tags=["Cliente"])
async def put_cliente(
    id: int,
    cliente_data: ClienteUpdate,
    db: Session = Depends(get_db),
    current_user: FuncionarioAuth = Depends(get_current_active_user)
):
    cliente = db.query(ClienteDB).filter(ClienteDB.id == id).first()

    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")

    for field, value in cliente_data.model_dump(exclude_unset=True).items():
        setattr(cliente, field, value)

    db.commit()
    db.refresh(cliente)

    return cliente


@router.delete("/cliente/{id}", tags=["Cliente"])
async def delete_cliente(
    id: int,
    db: Session = Depends(get_db),
    current_user: FuncionarioAuth = Depends(get_current_active_user)
):
    cliente = db.query(ClienteDB).filter(ClienteDB.id == id).first()

    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")

    db.delete(cliente)
    db.commit()

    return {"message": "Cliente deletado"}