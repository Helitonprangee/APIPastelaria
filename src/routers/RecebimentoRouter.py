import base64
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List
from datetime import datetime

from  domain.schemas.RecebimentoSchema import (
    RecebimentoDashboardItem,
    RecebimentoCompletoRequest,
    RecebimentoCompletoResponse,
    ComandaPagaResponse,
    RecebimentoListItem,
    RecebimentoUpdate,
)
from  domain.schemas.FuncionarioSchema import FuncionarioResponse
from  domain.schemas.ClienteSchema import ClienteResponse
from  domain.schemas.AuthSchema import FuncionarioAuth

from  infra.orm.ComandaModel import ComandaDB, ComandaProdutoDB
from  infra.orm.ProdutoModel import ProdutoDB
from  infra.orm.FuncionarioModel import FuncionarioDB
from  infra.orm.ClienteModel import ClienteDB
from  infra.orm.RecebimentoModel import RecebimentoDB, RecebimentoComandaDB
from  infra.database import get_async_db
from  infra.dependencies import require_group
from  infra.rate_limit import limiter
from  services.AuditoriaService import AuditoriaService

router = APIRouter()


async def _calcular_total_comanda(db: AsyncSession, comanda_id: int) -> tuple[float, int]:
    """Retorna (total, quantidade_itens) de uma comanda."""
    total_result = await db.execute(
        select(func.sum(ComandaProdutoDB.quantidade * ComandaProdutoDB.valor_unitario))
        .where(ComandaProdutoDB.comanda_id == comanda_id)
    )
    total = float(total_result.scalar() or 0.0)

    count_result = await db.execute(
        select(func.count(ComandaProdutoDB.id))
        .where(ComandaProdutoDB.comanda_id == comanda_id)
    )
    quantidade = count_result.scalar() or 0

    return total, quantidade


async def _produtos_da_comanda(db: AsyncSession, comanda_id: int) -> list:
    """Retorna lista de produtos detalhados de uma comanda."""
    result = await db.execute(
        select(ComandaProdutoDB, ProdutoDB)
        .outerjoin(ProdutoDB, ComandaProdutoDB.produto_id == ProdutoDB.id)
        .where(ComandaProdutoDB.comanda_id == comanda_id)
    )
    rows = result.all()

    produtos = []
    for cp, produto in rows:
        item_total = float(cp.quantidade) * float(cp.valor_unitario)

        foto_b64 = None
        if produto and produto.foto:
            foto_b64 = base64.b64encode(produto.foto).decode("utf-8")

        produtos.append({
            "id": cp.id,
            "produto_id": cp.produto_id,
            "nome": produto.nome if produto else "Produto removido",
            "descricao": produto.descricao if produto else "",
            "foto": foto_b64,
            "quantidade": cp.quantidade,
            "valor_unitario": float(cp.valor_unitario),
            "total_item": item_total,
        })

    return produtos


# ──────────────────────────────────────────────────────────────
# DASHBOARD - comandas abertas
# ──────────────────────────────────────────────────────────────
@router.get(
    "/recebimento/dashboard",
    response_model=List[RecebimentoDashboardItem],
    tags=["Recebimento"],
    summary="Dashboard com comandas abertas - grupos 1 e 3",
)
@limiter.limit("moderate")
async def get_dashboard(
    request: Request,
    db: AsyncSession = Depends(get_async_db),
    current_user: FuncionarioAuth = Depends(require_group([1, 3])),
):
    try:
        result = await db.execute(
            select(ComandaDB, ClienteDB)
            .outerjoin(ClienteDB, ClienteDB.id == ComandaDB.cliente_id)
            .where(ComandaDB.status == 0)
            .order_by(ComandaDB.data_hora.desc())
        )
        rows = result.all()

        items = []
        for comanda, cliente in rows:
            total, quantidade_produtos = await _calcular_total_comanda(db, comanda.id)

            items.append(
                RecebimentoDashboardItem(
                    id=comanda.id,
                    comanda=comanda.comanda,
                    status=comanda.status,
                    cliente=ClienteResponse(
                        id=cliente.id,
                        nome=cliente.nome,
                        cpf=cliente.cpf,
                        telefone=cliente.telefone,
                    ) if cliente else None,
                    total=total,
                    quantidade_produtos=quantidade_produtos,
                    data_hora=comanda.data_hora,
                )
            )

        return items

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao buscar dashboard: {str(e)}",
        )


# ──────────────────────────────────────────────────────────────
# DETALHE - produtos das comandas selecionadas
# ──────────────────────────────────────────────────────────────
@router.get(
    "/recebimento/comandas/detalhe/{comandas_ids}",
    tags=["Recebimento"],
    summary="Detalhar comandas para recebimento - grupos 1 e 3",
)
@limiter.limit("moderate")
async def get_detalhe_comandas(
    comandas_ids: str,
    request: Request,
    db: AsyncSession = Depends(get_async_db),
    current_user: FuncionarioAuth = Depends(require_group([1, 3])),
):
    try:
        try:
            ids = [int(i.strip()) for i in comandas_ids.split(",") if i.strip()]
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="IDs de comanda inválidos",
            )

        if not ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Informe pelo menos um ID de comanda",
            )

        comandas_detalhe = []

        for comanda_id in ids:
            result = await db.execute(
                select(ComandaDB, ClienteDB)
                .outerjoin(ClienteDB, ClienteDB.id == ComandaDB.cliente_id)
                .where(ComandaDB.id == comanda_id)
            )
            row = result.first()

            if not row:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Comanda {comanda_id} não encontrada",
                )

            comanda, cliente = row

            if comanda.status != 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Comanda '{comanda.comanda}' não está aberta",
                )

            produtos = await _produtos_da_comanda(db, comanda_id)
            subtotal = sum(p["total_item"] for p in produtos)

            comandas_detalhe.append({
                "id": comanda.id,
                "comanda": comanda.comanda,
                "data_hora": comanda.data_hora.isoformat(),
                "status": comanda.status,
                "cliente": {
                    "id": cliente.id,
                    "nome": cliente.nome,
                    "cpf": cliente.cpf,
                    "telefone": cliente.telefone,
                } if cliente else None,
                "produtos": produtos,
                "subtotal": subtotal,
            })

        total_geral = sum(c["subtotal"] for c in comandas_detalhe)

        return {"comandas": comandas_detalhe, "total_geral": total_geral}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao buscar detalhe das comandas: {str(e)}",
        )


# ──────────────────────────────────────────────────────────────
# RECEBIMENTO COMPLETO
# ──────────────────────────────────────────────────────────────
@router.post(
    "/recebimento/completo",
    response_model=RecebimentoCompletoResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Recebimento"],
    summary="Recebimento completo com desconto/acréscimo - grupos 1 e 3",
)
@limiter.limit("restrictive")
async def receber_completo(
    recebimento_data: RecebimentoCompletoRequest,
    request: Request,
    db: AsyncSession = Depends(get_async_db),
    current_user: FuncionarioAuth = Depends(require_group([1, 3])),
):
    try:
        if not recebimento_data.comandas_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Informe pelo menos uma comanda",
            )

        # Verificar funcionário
        result = await db.execute(
            select(FuncionarioDB).where(FuncionarioDB.id == recebimento_data.funcionario_id)
        )
        funcionario = result.scalar_one_or_none()
        if not funcionario:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Funcionário não encontrado",
            )

        # Verificar cliente (opcional)
        cliente = None
        if recebimento_data.cliente_id:
            result = await db.execute(
                select(ClienteDB).where(ClienteDB.id == recebimento_data.cliente_id)
            )
            cliente = result.scalar_one_or_none()
            if not cliente:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cliente não encontrado",
                )

        subtotal_geral = 0.0
        comandas_pagas = []
        comandas_db = []

        for comanda_id in recebimento_data.comandas_ids:
            result = await db.execute(
                select(ComandaDB).where(ComandaDB.id == comanda_id)
            )
            comanda = result.scalar_one_or_none()

            if not comanda:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Comanda {comanda_id} não encontrada",
                )

            if comanda.status != 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Comanda '{comanda.comanda}' não está aberta",
                )

            total, quantidade_produtos = await _calcular_total_comanda(db, comanda_id)
            subtotal_geral += total

            # Fechar comanda
            comanda.status = 1
            comanda.funcionario_id = recebimento_data.funcionario_id
            if recebimento_data.cliente_id:
                comanda.cliente_id = recebimento_data.cliente_id

            comandas_db.append(comanda)
            comandas_pagas.append(
                ComandaPagaResponse(
                    id=comanda.id,
                    comanda=comanda.comanda,
                    total=total,
                    quantidade_produtos=quantidade_produtos,
                )
            )

        desconto = float(recebimento_data.desconto_valor or 0)
        acrescimo = float(recebimento_data.acrescimo_valor or 0)
        valor_final = subtotal_geral - desconto + acrescimo

        novo_recebimento = RecebimentoDB(
            funcionario_id=recebimento_data.funcionario_id,
            cliente_id=recebimento_data.cliente_id,
            desconto_valor=desconto,
            acrescimo_valor=acrescimo,
            subtotal_geral=subtotal_geral,
            valor_final=valor_final,
            data_hora=datetime.now(),
        )

        db.add(novo_recebimento)
        await db.flush()

        for comanda in comandas_db:
            rel = RecebimentoComandaDB(
                recebimento_id=novo_recebimento.id,
                comanda_id=comanda.id,
            )
            db.add(rel)

        await db.commit()
        await db.refresh(novo_recebimento)

        await AuditoriaService.registrar_acao(
            db=db,
            funcionario_id=current_user.id,
            acao="CREATE",
            recurso="RECEBIMENTO",
            recurso_id=novo_recebimento.id,
            dados_novos={
                "recebimento_id": novo_recebimento.id,
                "comandas_ids": recebimento_data.comandas_ids,
                "valor_final": valor_final,
            },
            request=request,
        )

        return RecebimentoCompletoResponse(
            sucesso=True,
            mensagem="Recebimento realizado com sucesso",
            recebimento_id=novo_recebimento.id,
            comandas_pagas=comandas_pagas,
            subtotal_geral=subtotal_geral,
            desconto_total=desconto,
            acrescimo_total=acrescimo,
            valor_final=valor_final,
            cliente=ClienteResponse(
                id=cliente.id,
                nome=cliente.nome,
                cpf=cliente.cpf,
                telefone=cliente.telefone,
            ) if cliente else None,
            funcionario=FuncionarioResponse(
                id=funcionario.id,
                nome=funcionario.nome,
                matricula=funcionario.matricula,
                cpf=funcionario.cpf,
                telefone=funcionario.telefone,
                grupo=funcionario.grupo,
            ),
            data_hora=novo_recebimento.data_hora,
        )

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao realizar recebimento: {str(e)}",
        )


# ──────────────────────────────────────────────────────────────
# COMPROVANTE
# ──────────────────────────────────────────────────────────────
@router.get(
    "/recebimento/comprovante/{recebimento_id}",
    tags=["Recebimento"],
    summary="Gerar comprovante de recebimento - grupos 1 e 3",
)
@limiter.limit("moderate")
async def get_comprovante(
    recebimento_id: int,
    request: Request,
    db: AsyncSession = Depends(get_async_db),
    current_user: FuncionarioAuth = Depends(require_group([1, 3])),
):
    try:
        result = await db.execute(
            select(RecebimentoDB, FuncionarioDB, ClienteDB)
            .outerjoin(FuncionarioDB, FuncionarioDB.id == RecebimentoDB.funcionario_id)
            .outerjoin(ClienteDB, ClienteDB.id == RecebimentoDB.cliente_id)
            .where(RecebimentoDB.id == recebimento_id)
        )
        row = result.first()

        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Recebimento não encontrado",
            )

        recebimento, funcionario, cliente = row

        # Buscar comandas do recebimento
        rels_result = await db.execute(
            select(RecebimentoComandaDB).where(
                RecebimentoComandaDB.recebimento_id == recebimento_id
            )
        )
        rels = rels_result.scalars().all()

        comandas_detalhe = []

        for rel in rels:
            cmd_result = await db.execute(
                select(ComandaDB, ClienteDB)
                .outerjoin(ClienteDB, ClienteDB.id == ComandaDB.cliente_id)
                .where(ComandaDB.id == rel.comanda_id)
            )
            cmd_row = cmd_result.first()
            if not cmd_row:
                continue

            comanda, cmd_cliente = cmd_row
            produtos = await _produtos_da_comanda(db, comanda.id)
            subtotal = sum(p["total_item"] for p in produtos)

            comandas_detalhe.append({
                "id": comanda.id,
                "comanda": comanda.comanda,
                "data_hora": comanda.data_hora.isoformat(),
                "status": comanda.status,
                "cliente": {
                    "id": cmd_cliente.id,
                    "nome": cmd_cliente.nome,
                    "cpf": cmd_cliente.cpf,
                    "telefone": cmd_cliente.telefone,
                } if cmd_cliente else None,
                "produtos": produtos,
                "subtotal": subtotal,
            })

        return {
            "cabecalho": {
                "titulo": "COMPROVANTE DE RECEBIMENTO",
                "estabelecimento": "Comandas do Zé",
            },
            "cliente": {
                "id": cliente.id,
                "nome": cliente.nome,
                "cpf": cliente.cpf,
                "telefone": cliente.telefone,
            } if cliente else None,
            "funcionario": {
                "id": funcionario.id,
                "nome": funcionario.nome,
                "matricula": funcionario.matricula,
                "cpf": funcionario.cpf,
                "grupo": funcionario.grupo,
            },
            "comandas": comandas_detalhe,
            "resumo_valores": {
                "subtotal_geral": float(recebimento.subtotal_geral),
                "desconto": float(recebimento.desconto_valor or 0),
                "acrescimo": float(recebimento.acrescimo_valor or 0),
                "valor_final": float(recebimento.valor_final),
            },
            "recebimento": {
                "id": recebimento.id,
                "data_hora": recebimento.data_hora.isoformat(),
            },
            "rodape": {
                "mensagem": "Obrigado pela preferência!",
                "sistema": "Comandas do Zé",
            },
            "data_emissao": datetime.now().isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao gerar comprovante: {str(e)}",
        )


# ──────────────────────────────────────────────────────────────
# LISTAR TODOS OS RECEBIMENTOS - grupos 1 e 3
# ──────────────────────────────────────────────────────────────
@router.get(
    "/recebimento/",
    response_model=List[RecebimentoListItem],
    tags=["Recebimento"],
    summary="Listar todos os recebimentos - grupos 1 e 3",
)
@limiter.limit("moderate")
async def listar_recebimentos(
    request: Request,
    db: AsyncSession = Depends(get_async_db),
    current_user: FuncionarioAuth = Depends(require_group([1, 3])),
):
    try:
        result = await db.execute(
            select(RecebimentoDB, FuncionarioDB, ClienteDB)
            .outerjoin(FuncionarioDB, FuncionarioDB.id == RecebimentoDB.funcionario_id)
            .outerjoin(ClienteDB, ClienteDB.id == RecebimentoDB.cliente_id)
            .order_by(RecebimentoDB.data_hora.desc())
        )
        rows = result.all()

        items = []
        for recebimento, funcionario, cliente in rows:
            items.append(
                RecebimentoListItem(
                    id=recebimento.id,
                    funcionario_id=recebimento.funcionario_id,
                    funcionario=FuncionarioResponse(
                        id=funcionario.id,
                        nome=funcionario.nome,
                        matricula=funcionario.matricula,
                        cpf=funcionario.cpf,
                        telefone=funcionario.telefone,
                        grupo=funcionario.grupo,
                    ) if funcionario else None,
                    cliente_id=recebimento.cliente_id,
                    cliente=ClienteResponse(
                        id=cliente.id,
                        nome=cliente.nome,
                        cpf=cliente.cpf,
                        telefone=cliente.telefone,
                    ) if cliente else None,
                    desconto_valor=float(recebimento.desconto_valor or 0),
                    acrescimo_valor=float(recebimento.acrescimo_valor or 0),
                    subtotal_geral=float(recebimento.subtotal_geral),
                    valor_final=float(recebimento.valor_final),
                    data_hora=recebimento.data_hora,
                )
            )

        return items

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao listar recebimentos: {str(e)}",
        )


# ──────────────────────────────────────────────────────────────
# BUSCAR UM RECEBIMENTO - grupos 1 e 3
# ──────────────────────────────────────────────────────────────
@router.get(
    "/recebimento/{recebimento_id}",
    response_model=RecebimentoListItem,
    tags=["Recebimento"],
    summary="Buscar recebimento por ID - grupos 1 e 3",
)
@limiter.limit("moderate")
async def get_recebimento(
    recebimento_id: int,
    request: Request,
    db: AsyncSession = Depends(get_async_db),
    current_user: FuncionarioAuth = Depends(require_group([1, 3])),
):
    try:
        result = await db.execute(
            select(RecebimentoDB, FuncionarioDB, ClienteDB)
            .outerjoin(FuncionarioDB, FuncionarioDB.id == RecebimentoDB.funcionario_id)
            .outerjoin(ClienteDB, ClienteDB.id == RecebimentoDB.cliente_id)
            .where(RecebimentoDB.id == recebimento_id)
        )
        row = result.first()

        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Recebimento não encontrado",
            )

        recebimento, funcionario, cliente = row

        return RecebimentoListItem(
            id=recebimento.id,
            funcionario_id=recebimento.funcionario_id,
            funcionario=FuncionarioResponse(
                id=funcionario.id,
                nome=funcionario.nome,
                matricula=funcionario.matricula,
                cpf=funcionario.cpf,
                telefone=funcionario.telefone,
                grupo=funcionario.grupo,
            ) if funcionario else None,
            cliente_id=recebimento.cliente_id,
            cliente=ClienteResponse(
                id=cliente.id,
                nome=cliente.nome,
                cpf=cliente.cpf,
                telefone=cliente.telefone,
            ) if cliente else None,
            desconto_valor=float(recebimento.desconto_valor or 0),
            acrescimo_valor=float(recebimento.acrescimo_valor or 0),
            subtotal_geral=float(recebimento.subtotal_geral),
            valor_final=float(recebimento.valor_final),
            data_hora=recebimento.data_hora,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao buscar recebimento: {str(e)}",
        )


# ──────────────────────────────────────────────────────────────
# EDITAR RECEBIMENTO - grupo 1
# ──────────────────────────────────────────────────────────────
@router.put(
    "/recebimento/{recebimento_id}",
    response_model=RecebimentoListItem,
    tags=["Recebimento"],
    summary="Editar recebimento - grupo 1",
)
@limiter.limit("restrictive")
async def editar_recebimento(
    recebimento_id: int,
    data: RecebimentoUpdate,
    request: Request,
    db: AsyncSession = Depends(get_async_db),
    current_user: FuncionarioAuth = Depends(require_group([1])),
):
    try:
        result = await db.execute(
            select(RecebimentoDB).where(RecebimentoDB.id == recebimento_id)
        )
        recebimento = result.scalar_one_or_none()

        if not recebimento:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Recebimento não encontrado",
            )

        dados_antigos = {
            "desconto_valor": float(recebimento.desconto_valor or 0),
            "acrescimo_valor": float(recebimento.acrescimo_valor or 0),
            "cliente_id": recebimento.cliente_id,
        }

        if data.desconto_valor is not None:
            recebimento.desconto_valor = data.desconto_valor

        if data.acrescimo_valor is not None:
            recebimento.acrescimo_valor = data.acrescimo_valor

        if data.cliente_id is not None:
            recebimento.cliente_id = data.cliente_id if data.cliente_id != 0 else None

        recebimento.valor_final = (
            float(recebimento.subtotal_geral)
            - float(recebimento.desconto_valor or 0)
            + float(recebimento.acrescimo_valor or 0)
        )

        await db.commit()
        await db.refresh(recebimento)

        await AuditoriaService.registrar_acao(
            db=db,
            funcionario_id=current_user.id,
            acao="UPDATE",
            recurso="RECEBIMENTO",
            recurso_id=recebimento.id,
            dados_antigos=dados_antigos,
            dados_novos={"valor_final": recebimento.valor_final},
            request=request,
        )

        # Reload with joins for full response
        result = await db.execute(
            select(RecebimentoDB, FuncionarioDB, ClienteDB)
            .outerjoin(FuncionarioDB, FuncionarioDB.id == RecebimentoDB.funcionario_id)
            .outerjoin(ClienteDB, ClienteDB.id == RecebimentoDB.cliente_id)
            .where(RecebimentoDB.id == recebimento_id)
        )
        row = result.first()
        rec, func_db, cli = row

        return RecebimentoListItem(
            id=rec.id,
            funcionario_id=rec.funcionario_id,
            funcionario=FuncionarioResponse(
                id=func_db.id,
                nome=func_db.nome,
                matricula=func_db.matricula,
                cpf=func_db.cpf,
                telefone=func_db.telefone,
                grupo=func_db.grupo,
            ) if func_db else None,
            cliente_id=rec.cliente_id,
            cliente=ClienteResponse(
                id=cli.id,
                nome=cli.nome,
                cpf=cli.cpf,
                telefone=cli.telefone,
            ) if cli else None,
            desconto_valor=float(rec.desconto_valor or 0),
            acrescimo_valor=float(rec.acrescimo_valor or 0),
            subtotal_geral=float(rec.subtotal_geral),
            valor_final=float(rec.valor_final),
            data_hora=rec.data_hora,
        )

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao editar recebimento: {str(e)}",
        )


# ──────────────────────────────────────────────────────────────
# EXCLUIR RECEBIMENTO - grupo 1
# ──────────────────────────────────────────────────────────────
@router.delete(
    "/recebimento/{recebimento_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Recebimento"],
    summary="Excluir recebimento - grupo 1",
)
@limiter.limit("critical")
async def excluir_recebimento(
    recebimento_id: int,
    request: Request,
    db: AsyncSession = Depends(get_async_db),
    current_user: FuncionarioAuth = Depends(require_group([1])),
):
    try:
        result = await db.execute(
            select(RecebimentoDB).where(RecebimentoDB.id == recebimento_id)
        )
        recebimento = result.scalar_one_or_none()

        if not recebimento:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Recebimento não encontrado",
            )

        # Remover relações primeiro (CASCADE também faria isso, mas sendo explícito)
        rels = await db.execute(
            select(RecebimentoComandaDB).where(
                RecebimentoComandaDB.recebimento_id == recebimento_id
            )
        )
        for rel in rels.scalars().all():
            await db.delete(rel)

        await db.delete(recebimento)
        await db.commit()

        await AuditoriaService.registrar_acao(
            db=db,
            funcionario_id=current_user.id,
            acao="DELETE",
            recurso="RECEBIMENTO",
            recurso_id=recebimento_id,
            dados_antigos={"id": recebimento_id},
            request=request,
        )

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao excluir recebimento: {str(e)}",
        )
