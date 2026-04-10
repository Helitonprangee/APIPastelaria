from dotenv import load_dotenv, find_dotenv
import os

# localiza o arquivo de .env
dotenv_file = find_dotenv()

# Carrega o arquivo .env
load_dotenv(dotenv_file)

# ==============================
# CONFIG API
# ==============================
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))
RELOAD = os.getenv("RELOAD", "True").lower() == "true"

# ==============================
# CONFIG DATABASE
# ==============================
DB_SGDB = os.getenv("DB_SGDB", "sqlite")
DB_NAME = os.getenv("DB_NAME", "apiDatabase")

# Caso seja diferente de sqlite
DB_HOST = os.getenv("DB_HOST")
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")

# ==============================
# STRING SÍNCRONA
# ==============================
if DB_SGDB == 'sqlite':
    # SQLite
    STR_DATABASE = f"sqlite:///{DB_NAME}.db?check_same_thread=False"

elif DB_SGDB == 'mysql':
    STR_DATABASE = f"mysql+pymysql://{DB_USER}:{DB_PASS}@{DB_HOST}/{DB_NAME}?charset=utf8mb4"

elif DB_SGDB == 'mssql':
    STR_DATABASE = f"mssql+pymssql://{DB_USER}:{DB_PASS}@{DB_HOST}/{DB_NAME}?charset=utf8"

elif DB_SGDB == 'postgresql':
    STR_DATABASE = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}/{DB_NAME}"

else:
    STR_DATABASE = "sqlite:///apiDatabase.db?check_same_thread=False"

# ==============================
# STRING ASSÍNCRONA (IMPORTANTE)
# ==============================
if DB_SGDB == 'sqlite':
    ASYNC_STR_DATABASE = f"sqlite+aiosqlite:///{DB_NAME}.db"

elif DB_SGDB == 'mysql':
    ASYNC_STR_DATABASE = f"mysql+aiomysql://{DB_USER}:{DB_PASS}@{DB_HOST}/{DB_NAME}"

elif DB_SGDB == 'postgresql':
    ASYNC_STR_DATABASE = f"postgresql+asyncpg://{DB_USER}:{DB_PASS}@{DB_HOST}/{DB_NAME}"

elif DB_SGDB == 'mssql':
    # MSSQL não tem suporte async oficial simples
    ASYNC_STR_DATABASE = STR_DATABASE

else:
    ASYNC_STR_DATABASE = STR_DATABASE

# ==============================
# JWT
# ==============================
SECRET_KEY = os.getenv("SECRET_KEY", "sua-chave-secreta-super-forte-mudar-em-producao")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))

# ==============================
# CORS
# ==============================
cors_env = os.getenv("CORS_ORIGINS")

if cors_env:
    CORS_ORIGINS = cors_env.split(",")
else:
    CORS_ORIGINS = ["*"]