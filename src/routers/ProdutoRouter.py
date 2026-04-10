from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from src.domain.schemas.ProdutoSchema import (
    ProdutoCreate,
    ProdutoUpdate,
    ProdutoResponse
)

from src.infra.orm.ProdutoModel import ProdutoDB
from src.infra.database import get_async_db
from src.infra.dependencies import get_current_active_user
from src.domain.schemas.AuthSchema import FuncionarioAuth
from src.infra.rate_limit import limiter, get_rate_limit
from src.services.AuditoriaService import AuditoriaService

router = APIRouter()


# ROTA PÚBLICA
@router.get(
    "/produto/publico",
    response_model=List[ProdutoResponse],
    tags=["Produto"],
    status_code=status.HTTP_200_OK
)
@limiter.limit(get_rate_limit("light"))
async def get_produto_publico(
    request: Request,
    db: AsyncSession = Depends(get_async_db)
):
    try:
        result = await db.execute(select(ProdutoDB))
        produtos = result.scalars().all()
        return produtos

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao buscar produtos públicos: {str(e)}"
        )


# ROTAS PROTEGIDAS
@router.get(
    "/produto/",
    response_model=List[ProdutoResponse],
    tags=["Produto"],
    status_code=status.HTTP_200_OK
)
@limiter.limit(get_rate_limit("light"))
async def get_produto(
    request: Request,
    db: AsyncSession = Depends(get_async_db),
    current_user: FuncionarioAuth = Depends(get_current_active_user)
):
    try:
        result = await db.execute(select(ProdutoDB))
        produtos = result.scalars().all()

        await AuditoriaService.registrar_acao(
            db=db,
            funcionario_id=current_user.id,
            acao="LIST",
            recurso="PRODUTO",
            recurso_id=None,
            dados_antigos=None,
            dados_novos=None,
            request=request
        )

        return produtos

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao buscar produtos: {str(e)}"
        )


@router.get(
    "/produto/{id}",
    response_model=ProdutoResponse,
    tags=["Produto"],
    status_code=status.HTTP_200_OK
)
@limiter.limit(get_rate_limit("light"))
async def get_produto_id(
    request: Request,
    id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: FuncionarioAuth = Depends(get_current_active_user)
):
    try:
        result = await db.execute(select(ProdutoDB).filter(ProdutoDB.id == id))
        produto = result.scalars().first()

        if not produto:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Produto não encontrado"
            )

        await AuditoriaService.registrar_acao(
            db=db,
            funcionario_id=current_user.id,
            acao="READ",
            recurso="PRODUTO",
            recurso_id=produto.id,
            dados_antigos=None,
            dados_novos=produto,
            request=request
        )

        return produto

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao buscar produto: {str(e)}"
        )


@router.post(
    "/produto/",
    response_model=ProdutoResponse,
    tags=["Produto"],
    status_code=status.HTTP_201_CREATED
)
@limiter.limit(get_rate_limit("moderate"))
async def post_produto(
    request: Request,
    produto_data: ProdutoCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: FuncionarioAuth = Depends(get_current_active_user)
):
    try:
        novo_produto = ProdutoDB(**produto_data.model_dump())

        db.add(novo_produto)
        await db.commit()
        await db.refresh(novo_produto)

        await AuditoriaService.registrar_acao(
            db=db,
            funcionario_id=current_user.id,
            acao="CREATE",
            recurso="PRODUTO",
            recurso_id=novo_produto.id,
            dados_antigos=None,
            dados_novos=novo_produto,
            request=request
        )

        return novo_produto

    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao criar produto: {str(e)}"
        )


@router.put(
    "/produto/{id}",
    response_model=ProdutoResponse,
    tags=["Produto"],
    status_code=status.HTTP_200_OK
)
@limiter.limit(get_rate_limit("moderate"))
async def put_produto(
    request: Request,
    id: int,
    produto_data: ProdutoUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_user: FuncionarioAuth = Depends(get_current_active_user)
):
    try:
        result = await db.execute(select(ProdutoDB).filter(ProdutoDB.id == id))
        produto = result.scalars().first()

        if not produto:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Produto não encontrado"
            )

        dados_antigos_obj = produto.__dict__.copy()

        for field, value in produto_data.model_dump(exclude_unset=True).items():
            setattr(produto, field, value)

        await db.commit()
        await db.refresh(produto)

        await AuditoriaService.registrar_acao(
            db=db,
            funcionario_id=current_user.id,
            acao="UPDATE",
            recurso="PRODUTO",
            recurso_id=produto.id,
            dados_antigos=dados_antigos_obj,
            dados_novos=produto,
            request=request
        )

        return produto

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao atualizar produto: {str(e)}"
        )


@router.delete(
    "/produto/{id}",
    tags=["Produto"],
    status_code=status.HTTP_200_OK
)
@limiter.limit(get_rate_limit("critical"))
async def delete_produto(
    request: Request,
    id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: FuncionarioAuth = Depends(get_current_active_user)
):
    try:
        result = await db.execute(select(ProdutoDB).filter(ProdutoDB.id == id))
        produto = result.scalars().first()

        if not produto:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Produto não encontrado"
            )

        dados_antigos_obj = produto.__dict__.copy()

        await db.delete(produto)
        await db.commit()

        await AuditoriaService.registrar_acao(
            db=db,
            funcionario_id=current_user.id,
            acao="DELETE",
            recurso="PRODUTO",
            recurso_id=id,
            dados_antigos=dados_antigos_obj,
            dados_novos=None,
            request=request
        )

        return {"message": "Produto deletado"}

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao deletar produto: {str(e)}"
        )