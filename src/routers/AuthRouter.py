from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import timedelta

from domain.schemas.AuthSchema import (
    LoginRequest,
    TokenResponse,
    RefreshTokenRequest,
    FuncionarioAuth
)
from infra.orm.FuncionarioModel import FuncionarioDB
from infra.database import get_async_db
from infra.security import (
    verify_password,
    create_access_token,
    create_refresh_token,
    verify_refresh_token
)
from infra.dependencies import get_current_active_user
from settings import ACCESS_TOKEN_EXPIRE_MINUTES, REFRESH_TOKEN_EXPIRE_DAYS

router = APIRouter()


# =========================
# LOGIN (JSON - IGUAL ANEXO 2)
# =========================
@router.post(
    "/auth/login",
    response_model=TokenResponse,
    tags=["Autenticação"],
    summary="Login de funcionário - pública - retorna access e refresh token"
)
async def login(
    login_data: LoginRequest,
    db: AsyncSession = Depends(get_async_db)
):
    try:
        result = await db.execute(
            select(FuncionarioDB).where(FuncionarioDB.cpf == login_data.cpf)
        )
        funcionario = result.scalars().first()

        if not funcionario:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="CPF ou senha inválidos",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not verify_password(login_data.senha, funcionario.senha):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="CPF ou senha inválidos",
                headers={"WWW-Authenticate": "Bearer"},
            )

        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={
                "sub": funcionario.cpf,
                "id": funcionario.id,
                "grupo": funcionario.grupo
            },
            expires_delta=access_token_expires
        )

        refresh_token = create_refresh_token(
            data={
                "sub": funcionario.cpf,
                "id": funcionario.id,
                "grupo": funcionario.grupo
            }
        )

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            refresh_expires_in=REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao realizar login: {str(e)}"
        )


# =========================
# REFRESH TOKEN
# =========================
@router.post(
    "/auth/refresh",
    response_model=TokenResponse,
    tags=["Autenticação"],
    summary="Refresh token - pública - renova access token"
)
async def refresh_token(
    refresh_data: RefreshTokenRequest,
    db: AsyncSession = Depends(get_async_db)
):
    try:
        payload = verify_refresh_token(refresh_data.refresh_token)
        cpf = payload.get("sub")

        result = await db.execute(
            select(FuncionarioDB).where(FuncionarioDB.cpf == cpf)
        )
        funcionario = result.scalars().first()

        if not funcionario:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Funcionário não encontrado",
                headers={"WWW-Authenticate": "Bearer"},
            )

        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={
                "sub": funcionario.cpf,
                "id": funcionario.id,
                "grupo": funcionario.grupo
            },
            expires_delta=access_token_expires
        )

        new_refresh_token = create_refresh_token(
            data={
                "sub": funcionario.cpf,
                "id": funcionario.id,
                "grupo": funcionario.grupo
            }
        )

        return TokenResponse(
            access_token=access_token,
            refresh_token=new_refresh_token,
            token_type="bearer",
            expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            refresh_expires_in=REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Erro ao renovar token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )


# =========================
# USUÁRIO ATUAL
# =========================
@router.get(
    "/auth/me",
    response_model=FuncionarioAuth,
    tags=["Autenticação"],
    summary="Dados do usuário atual - protegida"
)
async def get_current_user_info(
    current_user: FuncionarioAuth = Depends(get_current_active_user)
):
    return current_user


# =========================
# LOGOUT
# =========================
@router.post(
    "/auth/logout",
    tags=["Autenticação"],
    summary="Logout - pública"
)
async def logout():
    return {"message": "Logout realizado com sucesso"}