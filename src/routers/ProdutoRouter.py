from fastapi import APIRouter
from domain.entities.Produto import Produto
router = APIRouter()
# Criar as rotas/endpoints: GET, POST, PUT, DELETE

@router.get("/Produto/", tags=["Produto"], status_code=200)
def get_funcionario():
    return {"msg": "Produto get todos executado"}

@router.get("/Produto/{id}", tags=["Produto"], status_code=200)
def get_funcionario(id: int):
    return {"msg": "Produto get um executado"}

@router.post("/Produto/", tags=["Produto"], status_code=200)
def post_funcionario(corpo: Produto):
    return {"msg": "Produto post executado", "nome": corpo.nome, "descricao": corpo.descricao, "valor_unitario": corpo.valor_unitario}

@router.put("/Produto/{id}", tags=["Produto"], status_code=200)
def put_funcionario(id: int, corpo: Produto):
    return {"msg": "Produto put executado", "id":id, "nome": corpo.nome, "descricao": corpo.descricao, "valor_unitario": corpo.valor_unitario}

@router.delete("/Produto/{id}", tags=["Produto"], status_code=200)
def delete_funcionario(id: int):
    return {"msg": "Produto delete executado", "id":id}
