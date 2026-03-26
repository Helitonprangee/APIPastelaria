# Heliton
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from src.domain.schemas.ProdutoSchema import (
    ProdutoCreate,
    ProdutoUpdate,
    ProdutoResponse
)

from src.infra.orm.ProdutoModel import ProdutoDB
from src.infra.database import get_db

#  IMPORTANTE
from src.infra.dependencies import get_current_active_user
from src.domain.schemas.AuthSchema import FuncionarioAuth

router = APIRouter()


#  ROTA PÚBLICA (IMPORTANTE PRA ATIVIDADE)
@router.get("/produto/publico", response_model=List[ProdutoResponse], tags=["Produto"])
async def get_produto_publico(db: Session = Depends(get_db)):
    return db.query(ProdutoDB).all()


# 🔒 PROTEGIDAS
@router.get("/produto/", response_model=List[ProdutoResponse], tags=["Produto"])
async def get_produto(
    db: Session = Depends(get_db),
    current_user: FuncionarioAuth = Depends(get_current_active_user)
):
    return db.query(ProdutoDB).all()


@router.get("/produto/{id}", response_model=ProdutoResponse, tags=["Produto"])
async def get_produto_id(
    id: int,
    db: Session = Depends(get_db),
    current_user: FuncionarioAuth = Depends(get_current_active_user)
):
    produto = db.query(ProdutoDB).filter(ProdutoDB.id == id).first()

    if not produto:
        raise HTTPException(status_code=404, detail="Produto não encontrado")

    return produto


@router.post("/produto/", response_model=ProdutoResponse, tags=["Produto"])
async def post_produto(
    produto_data: ProdutoCreate,
    db: Session = Depends(get_db),
    current_user: FuncionarioAuth = Depends(get_current_active_user)
):
    novo_produto = ProdutoDB(**produto_data.model_dump())

    db.add(novo_produto)
    db.commit()
    db.refresh(novo_produto)

    return novo_produto


@router.put("/produto/{id}", response_model=ProdutoResponse, tags=["Produto"])
async def put_produto(
    id: int,
    produto_data: ProdutoUpdate,
    db: Session = Depends(get_db),
    current_user: FuncionarioAuth = Depends(get_current_active_user)
):
    produto = db.query(ProdutoDB).filter(ProdutoDB.id == id).first()

    if not produto:
        raise HTTPException(status_code=404, detail="Produto não encontrado")

    for field, value in produto_data.model_dump(exclude_unset=True).items():
        setattr(produto, field, value)

    db.commit()
    db.refresh(produto)

    return produto


@router.delete("/produto/{id}", tags=["Produto"])
async def delete_produto(
    id: int,
    db: Session = Depends(get_db),
    current_user: FuncionarioAuth = Depends(get_current_active_user)
):
    produto = db.query(ProdutoDB).filter(ProdutoDB.id == id).first()

    if not produto:
        raise HTTPException(status_code=404, detail="Produto não encontrado")

    db.delete(produto)
    db.commit()

    return {"message": "Produto deletado"}