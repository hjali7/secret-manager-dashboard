import os
import time
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

DB_SECRET_FILE_PATH = "/vault/secrets/db-creds"

def get_db_credentials():
    retries = 15
    for i in range(retries):
        if os.path.exists(DB_SECRET_FILE_PATH):
            with open(DB_SECRET_FILE_PATH, 'r') as f:
                creds = {}
                for line in f:
                    if '=' in line:
                        key, value = line.strip().split('=', 1)
                        creds[key] = value
                return creds
        print(f"Secret file not found at '{DB_SECRET_FILE_PATH}', waiting... ({i+1}/{retries})")
        time.sleep(2)
    raise FileNotFoundError(f"Secret file not found at {DB_SECRET_FILE_PATH} after multiple retries.")


creds = get_db_credentials()
db_user = creds.get("DB_USER")
db_password = creds.get("DB_PASSWORD")
db_host = os.getenv("DB_HOST", "postgres-service")
db_name = os.getenv("DB_NAME", "secrets_db")

DATABASE_URL = f"postgresql://{db_user}:{db_password}@{db_host}:5432/{db_name}"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

from models import Base
Base.metadata.create_all(bind=engine)