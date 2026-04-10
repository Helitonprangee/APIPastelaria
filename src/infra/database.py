from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from src.settings import STR_DATABASE, ASYNC_STR_DATABASE

# =========================
# ENGINE SÍNCRONO (legado)
# =========================
engine = create_engine(
    STR_DATABASE,
    echo=True,
    future=True
)

# =========================
# ENGINE ASSÍNCRONO
# =========================
async_engine = create_async_engine(
    ASYNC_STR_DATABASE,
    echo=True,
    future=True
)

# =========================
# SESSÃO SÍNCRONA (legado)
# =========================
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False
)

# =========================
# SESSÃO ASSÍNCRONA
# =========================
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# =========================
# BASE DOS MODELS
# =========================
Base = declarative_base()

# =========================
# CRIAR TABELAS
# =========================
async def cria_tabelas():
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

# =========================
# DEPENDÊNCIA SÍNCRONA (LEGADO)
# =========================
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# =========================
# DEPENDÊNCIA ASSÍNCRONA
# =========================
async def get_async_db():
    async with AsyncSessionLocal() as session:
        yield session