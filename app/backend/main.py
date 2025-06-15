# apps/backend/main.py (نسخه نهایی و صحیح برای والت)
import os
import time
from fastapi import FastAPI, HTTPException
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError

app = FastAPI()

# مسیر فایلی که ایجنت والت سکرت را در آن می‌نویسد
DB_SECRET_FILE_PATH = "/vault/secrets/db-creds"

def get_db_credentials():
    """این تابع منتظر می‌ماند تا فایل سکرت توسط ایجنت والت ساخته شود و آن را می‌خواند"""
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

@app.get("/")
def read_root():
    return {"status": "backend_is_running", "version": "1.4.0-final-CI/CD"}

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.get("/db-status")
def db_status_check():
    try:
        creds = get_db_credentials()
        db_user = creds.get("DB_USER")
        db_password = creds.get("DB_PASSWORD")
        
        db_host = os.getenv("DB_HOST", "postgres-service")
        db_name = os.getenv("DB_NAME", "secrets_db")

        if not all([db_user, db_password]):
            raise HTTPException(status_code=500, detail="Database credentials not found or incomplete in secret file.")

        database_url = f"postgresql://{db_user}:{db_password}@{db_host}:5432/{db_name}"
        engine = create_engine(database_url)

        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1"))
            if result.scalar() == 1:
                return {"db_status": "connected_successfully_via_vault"}
    except (FileNotFoundError, OperationalError) as e:
        raise HTTPException(status_code=503, detail=f"Database connection failed: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e}")