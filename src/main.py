from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn

from slowapi.errors import RateLimitExceeded

from settings import HOST, PORT, RELOAD, CORS_ORIGINS
from infra.rate_limit import limiter, rate_limit_exceeded_handler
from infra import database
from infra.middleware.IPAccessMiddleware import IPAccessMiddleware

from routers import AuditoriaRouter
from routers import AuthRouter
from routers import FuncionarioRouter
from routers import ClienteRouter
from routers import ProdutoRouter
from routers import ComandaRouter
from routers import HealthRouter


# lifespan - ciclo de vida da aplicação
@asynccontextmanager
async def lifespan(app: FastAPI):
    # executa no startup
    print("API has started")
    #await database.cria_tabelas()
    yield
    # executa no shutdown
    print("API is shutting down")


# cria a aplicação FastAPI com o contexto de vida
app = FastAPI(lifespan=lifespan)

# aplicar middleware de controle de acesso
app.add_middleware(IPAccessMiddleware, allowed_origins=CORS_ORIGINS)

# configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=False if "*" in CORS_ORIGINS else True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type", "Authorization"],
    expose_headers=["*"],
    max_age=600,
)

# configuração de Rate Limiting
app.state.limiter = limiter

# registrar handler personalizado ANTES de incluir rotas
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

print("Rate Limiting Handler registrado")


@app.get("/", tags=["Root"], status_code=200, summary="Informações da API - pública")
async def root():
    return {
        "detail": "API Comandas",
        "Swagger UI": "https://127.0.0.1:4443/docs",
        "ReDoc": "https://127.0.0.1:4443/redoc"
    }

# incluir as rotas/endpoints no FastAPI
app.include_router(AuditoriaRouter.router)
app.include_router(AuthRouter.router)
app.include_router(FuncionarioRouter.router)
app.include_router(ClienteRouter.router)
app.include_router(ProdutoRouter.router)
app.include_router(ComandaRouter.router)
# app.include_router(RecebimentoRouter.router)
app.include_router(HealthRouter.router)


if __name__ == "__main__":
    uvicorn.run("main:app", host=HOST, port=int(PORT), reload=RELOAD)