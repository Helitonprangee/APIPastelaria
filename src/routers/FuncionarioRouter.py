from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from services.AuditoriaService import AuditoriaService
from infra.rate_limit import limiter, get_rate_limit

# Domain Schemas
from domain.schemas.FuncionarioSchema import (
    FuncionarioCreate,
    FuncionarioUpdate,
    FuncionarioResponse
)
from domain.schemas.AuthSchema import FuncionarioAuth

# Infra
from infra.orm.FuncionarioModel import FuncionarioDB
from infra.database import get_async_db
from infra.security import get_password_hash
from infra.dependencies import require_group

router = APIRouter()


@router.get(
    "/funcionario/",
    response_model=List[FuncionarioResponse],
    tags=["Funcionário"],
    status_code=status.HTTP_200_OK
)
async def get_funcionarios(
    db: AsyncSession = Depends(get_async_db),
    current_user: FuncionarioAuth = Depends(require_group([1]))
):
    """Retorna todos os funcionários"""
    try:
        result = await db.execute(select(FuncionarioDB))
        funcionarios = result.scalars().all()
        return funcionarios

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao buscar funcionários: {str(e)}"
        )


@router.get(
    "/funcionario/{id}",
    response_model=FuncionarioResponse,
    tags=["Funcionário"],
    status_code=status.HTTP_200_OK
)
async def get_funcionario_por_id(
    id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: FuncionarioAuth = Depends(require_group([1]))
):
    """Retorna um funcionário específico pelo ID"""
    try:
        result = await db.execute(
            select(FuncionarioDB).where(FuncionarioDB.id == id)
        )
        funcionario = result.scalars().first()

        if not funcionario:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Funcionário não encontrado"
            )

        return funcionario

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao buscar funcionário: {str(e)}"
        )


@router.post(
    "/funcionario/",
    response_model=FuncionarioResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Funcionário"]
)
async def post_funcionario(
    request: Request,
    funcionario_data: FuncionarioCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: FuncionarioAuth = Depends(require_group([1]))
):
    """Cria um novo funcionário"""
    try:
        result = await db.execute(
            select(FuncionarioDB).where(FuncionarioDB.cpf == funcionario_data.cpf)
        )
        existing_funcionario = result.scalars().first()

        if existing_funcionario:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Já existe um funcionário com este CPF"
            )

        hashed_password = get_password_hash(funcionario_data.senha)

        novo_funcionario = FuncionarioDB(
            id=None,
            nome=funcionario_data.nome,
            matricula=funcionario_data.matricula,
            cpf=funcionario_data.cpf,
            telefone=funcionario_data.telefone,
            grupo=funcionario_data.grupo,
            senha=hashed_password
        )

        db.add(novo_funcionario)
        await db.commit()
        await db.refresh(novo_funcionario)

        await AuditoriaService.registrar_acao(
            db=db,
            funcionario_id=current_user.id,
            acao="CREATE",
            recurso="FUNCIONARIO",
            recurso_id=novo_funcionario.id,
            dados_antigos=None,
            dados_novos=novo_funcionario,
            request=request
        )

        return novo_funcionario

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao criar funcionário: {str(e)}"
        )


@router.put(
    "/funcionario/{id}",
    response_model=FuncionarioResponse,
    tags=["Funcionário"],
    status_code=status.HTTP_200_OK
)
@limiter.limit(get_rate_limit("moderate"))
async def put_funcionario(
    request: Request,
    id: int,
    funcionario_data: FuncionarioUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_user: FuncionarioAuth = Depends(require_group([1]))
):
    """Atualiza um funcionário existente"""
    try:
        result = await db.execute(
            select(FuncionarioDB).where(FuncionarioDB.id == id)
        )
        funcionario = result.scalars().first()

        if not funcionario:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Funcionário não encontrado"
            )

        dados_antigos_obj = funcionario.__dict__.copy()
        existing_funcionario = None

        if funcionario_data.cpf and funcionario_data.cpf != funcionario.cpf:
            result = await db.execute(
                select(FuncionarioDB).where(FuncionarioDB.cpf == funcionario_data.cpf)
            )
            existing_funcionario = result.scalars().first()

        if existing_funcionario:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Já existe um funcionário com este CPF"
            )

        if funcionario_data.senha:
            funcionario_data.senha = get_password_hash(funcionario_data.senha)

        if funcionario_data.grupo is not None:
            if funcionario_data.grupo not in [1, 2, 3]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Grupo inválido. Apenas grupos 1 (Admin), 2 (Atendimento Balcão) ou 3 (Atendimento Caixa) são permitidos."
                )

        update_data = funcionario_data.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            setattr(funcionario, field, value)

        await db.commit()
        await db.refresh(funcionario)

        await AuditoriaService.registrar_acao(
            db=db,
            funcionario_id=current_user.id,
            acao="UPDATE",
            recurso="FUNCIONARIO",
            recurso_id=funcionario.id,
            dados_antigos=dados_antigos_obj,
            dados_novos=funcionario,
            request=request
        )

        return funcionario

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao atualizar funcionário: {str(e)}"
        )


@router.delete(
    "/funcionario/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Funcionário"],
    summary="Remover funcionário"
)
@limiter.limit(get_rate_limit("critical"))
async def delete_funcionario(
    request: Request,
    id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: FuncionarioAuth = Depends(require_group([1]))
):
    """Remove um funcionário"""
    try:
        result = await db.execute(
            select(FuncionarioDB).where(FuncionarioDB.id == id)
        )
        funcionario = result.scalars().first()

        if not funcionario:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Funcionário não encontrado"
            )

        dados_antigos_obj = funcionario.__dict__.copy()
        funcionario_id_removido = funcionario.id

        await db.delete(funcionario)
        await db.commit()

        await AuditoriaService.registrar_acao(
            db=db,
            funcionario_id=current_user.id,
            acao="DELETE",
            recurso="FUNCIONARIO",
            recurso_id=funcionario_id_removido,
            dados_antigos=dados_antigos_obj,
            dados_novos=None,
            request=request
        )

        return None

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao deletar funcionário: {str(e)}"
        )