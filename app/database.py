from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker


# ============================================================
# PROJECT PATHS
# ============================================================

BASE_DIR = Path(
    __file__
).resolve().parent.parent


DATA_DIR = (
    BASE_DIR / "data"
)


DATA_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


DATABASE_PATH = (
    DATA_DIR / "vanta.db"
)


# ============================================================
# DATABASE URL
# ============================================================
#
# SQLite database stored locally at:
#
# data/vanta.db
#
# ============================================================

DATABASE_URL = (
    f"sqlite:///{DATABASE_PATH.as_posix()}"
)


# ============================================================
# SQLALCHEMY BASE
# ============================================================

class Base(DeclarativeBase):
    pass


# ============================================================
# DATABASE ENGINE
# ============================================================

engine = create_engine(

    DATABASE_URL,

    connect_args={
        "check_same_thread": False
    },

)


# ============================================================
# DATABASE SESSION
# ============================================================

SessionLocal = sessionmaker(

    bind=engine,

    autoflush=False,

    autocommit=False,

    expire_on_commit=False,

)


# ============================================================
# FASTAPI DATABASE DEPENDENCY
# ============================================================

def get_db():

    db = SessionLocal()

    try:

        yield db

    finally:

        db.close()
        # ============================================================
# DATABASE INITIALIZATION
# ============================================================

def init_db():

    # Import models here so SQLAlchemy knows
    # which tables need to exist.
    from . import models

    Base.metadata.create_all(
        bind=engine
    )