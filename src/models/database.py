from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from src.config import config

Base = declarative_base()

engine = create_engine(
    config.DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in config.DATABASE_URL else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@contextmanager
def get_session() -> Session:
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

def init_database():
    config.create_directories()
    Base.metadata.create_all(bind=engine)