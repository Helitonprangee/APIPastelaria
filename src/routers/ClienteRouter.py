from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from  domain.schemas.ClienteSchema import (
    ClienteCreate,
    ClienteUpdate,
    ClienteResponse
)
from  domain.schemas.AuthSchema import FuncionarioAuth

from  infra.orm.ClienteModel import ClienteDB
from  infra.database import get_async_db
from  infra.dependencies import get_current_active_user
from  infra.rate_limit import limiter, get_rate_limit
from  services.AuditoriaService import AuditoriaService

router = APIRouter()


# =========================
# GET ALL
# =========================
@router.get(
    "/cliente/",
    response_model=List[ClienteResponse],
    tags=["Cliente"],
    status_code=status.HTTP_200_OK
)
@limiter.limit(get_rate_limit("light"))
async def get_cliente(
    request: Request,
    db: AsyncSession = Depends(get_async_db),
    current_user: FuncionarioAuth = Depends(get_current_active_user)
):
    try:
        result = await db.execute(select(ClienteDB))
        clientes = result.scalars().all()

        return clientes

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao buscar clientes: {str(e)}"
        )


# =========================
# GET BY ID
# =========================
@router.get(
    "/cliente/{id}",
    response_model=ClienteResponse,
    tags=["Cliente"],
    status_code=status.HTTP_200_OK
)
@limiter.limit(get_rate_limit("light"))
async def get_cliente_id(
    request: Request,
    id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: FuncionarioAuth = Depends(get_current_active_user)
):
    try:
        result = await db.execute(select(ClienteDB).where(ClienteDB.id == id))
        cliente = result.scalar_one_or_none()

        if not cliente:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cliente não encontrado"
            )

        return cliente

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao buscar cliente: {str(e)}"
        )


# =========================
# POST
# =========================
@router.post(
    "/cliente/",
    response_model=ClienteResponse,
    tags=["Cliente"],
    status_code=status.HTTP_201_CREATED
)
@limiter.limit(get_rate_limit("moderate"))
async def post_cliente(
    request: Request,
    cliente_data: ClienteCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: FuncionarioAuth = Depends(get_current_active_user)
):
    try:
        result = await db.execute(
            select(ClienteDB).where(ClienteDB.cpf == cliente_data.cpf)
        )
        existente = result.scalar_one_or_none()

        if existente:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="CPF já cadastrado"
            )

        novo = ClienteDB(**cliente_data.model_dump())

        db.add(novo)
        await db.commit()
        await db.refresh(novo)

        return novo

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao criar cliente: {str(e)}"
        )


# =========================
# PUT
# =========================
@router.put(
    "/cliente/{id}",
    response_model=ClienteResponse,
    tags=["Cliente"],
    status_code=status.HTTP_200_OK
)
@limiter.limit(get_rate_limit("moderate"))
async def put_cliente(
    request: Request,
    id: int,
    cliente_data: ClienteUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_user: FuncionarioAuth = Depends(get_current_active_user)
):
    try:
        result = await db.execute(select(ClienteDB).where(ClienteDB.id == id))
        cliente = result.scalar_one_or_none()

        if not cliente:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cliente não encontrado"
            )

        if cliente_data.cpf and cliente_data.cpf != cliente.cpf:
            result = await db.execute(
                select(ClienteDB).where(ClienteDB.cpf == cliente_data.cpf)
            )
            existente = result.scalar_one_or_none()

            if existente:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="CPF já cadastrado para outro cliente"
                )

        for field, value in cliente_data.model_dump(exclude_unset=True).items():
            setattr(cliente, field, value)

        await db.commit()
        await db.refresh(cliente)

        return cliente

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao atualizar cliente: {str(e)}"
        )


# =========================
# DELETE
# =========================
@router.delete(
    "/cliente/{id}",
    tags=["Cliente"],
    status_code=status.HTTP_200_OK
)
@limiter.limit(get_rate_limit("critical"))
async def delete_cliente(
    request: Request,
    id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: FuncionarioAuth = Depends(get_current_active_user)
):
    try:
        result = await db.execute(select(ClienteDB).where(ClienteDB.id == id))
        cliente = result.scalar_one_or_none()

        if not cliente:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cliente não encontrado"
            )

        await db.delete(cliente)
        await db.commit()

        return {"message": "Cliente deletado"}

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao deletar cliente: {str(e)}"
        )