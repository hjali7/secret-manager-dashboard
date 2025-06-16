import os
import time
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from contextlib import contextmanager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DB_SECRET_FILE_PATH = "/vault/secrets/db-creds"

def get_db_credentials():
    retries = 15
    for i in range(retries):
        try:
            if os.path.exists(DB_SECRET_FILE_PATH):
                with open(DB_SECRET_FILE_PATH, 'r') as f:
                    creds = {}
                    for line in f:
                        if '=' in line:
                            key, value = line.strip().split('=', 1)
                            creds[key] = value
                    return creds
            logger.warning(f"Secret file not found at '{DB_SECRET_FILE_PATH}', waiting... ({i+1}/{retries})")
            time.sleep(2)
        except Exception as e:
            logger.error(f"Error reading credentials: {str(e)}")
            raise
    raise FileNotFoundError(f"Secret file not found at {DB_SECRET_FILE_PATH} after multiple retries.")

try:
    creds = get_db_credentials()
    db_user = creds.get("DB_USER")
    db_password = creds.get("DB_PASSWORD")
    db_host = os.getenv("DB_HOST", "postgres-service")
    db_name = os.getenv("DB_NAME", "secrets_db")

    DATABASE_URL = f"postgresql://{db_user}:{db_password}@{db_host}:5432/{db_name}"

    engine = create_engine(
        DATABASE_URL,
        pool_size=5,
        max_overflow=10,
        pool_timeout=30,
        pool_recycle=1800,
        pool_pre_ping=True,
        echo=False
    )
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    @contextmanager
    def get_db_session():
        session = SessionLocal()
        try:
            yield session
            session.commit()
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Database error: {str(e)}")
            raise
        finally:
            session.close()

    from models import Base
    Base.metadata.create_all(bind=engine)
    logger.info("Database connection established successfully")

except Exception as e:
    logger.error(f"Failed to initialize database: {str(e)}")
    raise