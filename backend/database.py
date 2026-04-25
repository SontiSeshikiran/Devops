import os
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()

# Default to SQLite for 'Zero Config' local execution.
# Use an absolute path anchored to this file so the DB location doesn't
# depend on the process working directory (which can differ between
# running via `uvicorn`, Docker, IDEs, etc.).
_DEFAULT_SQLITE_PATH = (Path(__file__).resolve().parent / "blutor_identity_v4.db").as_posix()
DEFAULT_DB = f"sqlite:///{_DEFAULT_SQLITE_PATH}"
DATABASE_URL = os.getenv("DATABASE_URL", DEFAULT_DB)

# Fallback check: if the URL is postgres but the driver (psycopg2) is missing, force SQLite
if "postgresql" in DATABASE_URL:
    try:
        import psycopg2  # noqa: F401
    except ImportError:
        print("Warning: PostgreSQL driver (psycopg2) not found. Falling back to local SQLite.")
        DATABASE_URL = DEFAULT_DB

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
