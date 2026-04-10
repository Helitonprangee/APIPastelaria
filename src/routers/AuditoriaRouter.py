from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import desc, select, func
from typing import List, Optional
from datetime import datetime, timedelta

from src.domain.schemas.AuditoriaSchema import AuditoriaResponse
from src.domain.schemas.AuthSchema import FuncionarioAuth
from src.infra.orm.AuditoriaModel import AuditoriaDB
from src.infra.orm.FuncionarioModel import FuncionarioDB
from src.infra.database import get_async_db
from src.infra.dependencies import require_group
from src.infra.rate_limit import limiter, get_rate_limit

router = APIRouter()


@router.get(
    "/auditoria",
    response_model=List[AuditoriaResponse],
    tags=["Auditoria"],
    summary="Listar registros de auditoria - protegida por JWT e grupo 1"
)
@limiter.limit(get_rate_limit("moderate"))
async def listar_auditoria(
    request: Request,
    funcionario_id: Optional[int] = Query(None, description="Filtrar por funcionário"),
    acao: Optional[str] = Query(None, description="Filtrar por ação (separar múltiplas com vírgula)"),
    recurso: Optional[str] = Query(None, description="Filtrar por recurso (separar múltiplos com vírgula)"),
    data_inicio: Optional[str] = Query(None, description="Data início (YYYY-MM-DD)"),
    data_fim: Optional[str] = Query(None, description="Data fim (YYYY-MM-DD)"),
    skip: int = Query(0, ge=0, description="Número de registros para pular"),
    limite: int = Query(100, ge=1, le=1000, description="Limite de registros"),
    db: AsyncSession = Depends(get_async_db),
    current_user: FuncionarioAuth = Depends(require_group([1]))
):
    """
    Lista registros de auditoria com filtros opcionais.
    - Apenas administradores podem acessar.
    """
    try:
        stmt = select(AuditoriaDB, FuncionarioDB).join(
            FuncionarioDB,
            FuncionarioDB.id == AuditoriaDB.funcionario_id
        )

        if funcionario_id:
            stmt = stmt.where(AuditoriaDB.funcionario_id == funcionario_id)

        if acao:
            acoes_list = [a.strip().upper() for a in acao.split(",")]
            stmt = stmt.where(AuditoriaDB.acao.in_(acoes_list))

        if recurso:
            recursos_list = [r.strip().upper() for r in recurso.split(",")]
            stmt = stmt.where(AuditoriaDB.recurso.in_(recursos_list))

        if data_inicio:
            try:
                data_inicio_dt = datetime.strptime(data_inicio, "%Y-%m-%d")
                stmt = stmt.where(AuditoriaDB.data_hora >= data_inicio_dt)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Data início inválida. Use formato YYYY-MM-DD"
                )

        if data_fim:
            try:
                data_fim_dt = datetime.strptime(data_fim, "%Y-%m-%d") + timedelta(days=1)
                stmt = stmt.where(AuditoriaDB.data_hora < data_fim_dt)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Data fim inválida. Use formato YYYY-MM-DD"
                )

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_result = await db.execute(count_stmt)
        total_count = total_result.scalar()

        result_query = stmt.order_by(desc(AuditoriaDB.data_hora)).offset(skip).limit(limite)
        result = await db.execute(result_query)
        auditorias = result.all()

        result_list = []

        for auditoria, funcionario in auditorias:
            result_list.append(
                AuditoriaResponse(
                    id=auditoria.id,
                    funcionario_id=auditoria.funcionario_id,
                    funcionario={
                        "id": funcionario.id,
                        "nome": funcionario.nome,
                        "matricula": funcionario.matricula,
                        "grupo": funcionario.grupo
                    },
                    acao=auditoria.acao,
                    recurso=auditoria.recurso,
                    recurso_id=auditoria.recurso_id,
                    dados_antigos=auditoria.dados_antigos,
                    dados_novos=auditoria.dados_novos,
                    ip_address=auditoria.ip_address,
                    user_agent=auditoria.user_agent,
                    data_hora=auditoria.data_hora
                )
            )

        return result_list

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao listar auditoria: {str(e)}"
        )


@router.get(
    "/auditoria/acoes",
    tags=["Auditoria"],
    summary="Listar tipos de ações disponíveis para filtro - protegida por JWT e grupo 1"
)
@limiter.limit(get_rate_limit("light"))
async def listar_acoes_disponiveis(
    request: Request,
    db: AsyncSession = Depends(get_async_db),
    current_user: FuncionarioAuth = Depends(require_group([1]))
):
    """
    Lista os tipos de ações e recursos disponíveis para filtro.
    """
    try:
        return {
            "acoes": [
                {"codigo": "LOGIN"},
                {"codigo": "LOGOUT"},
                {"codigo": "REFRESH_TOKEN"},
                {"codigo": "READ_ME"},
                {"codigo": "LIST"},
                {"codigo": "READ"},
                {"codigo": "CREATE"},
                {"codigo": "UPDATE"},
                {"codigo": "DELETE"},
                {"codigo": "CANCEL"}
            ],
            "recursos": [
                {"codigo": "AUTH"},
                {"codigo": "CLIENTE"},
                {"codigo": "FUNCIONARIO"},
                {"codigo": "PRODUTO"},
                {"codigo": "COMANDA"}
            ]
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao listar ações e recursos: {str(e)}"
        )