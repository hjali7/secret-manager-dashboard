# apps/backend/main.py
import os
from fastapi import FastAPI, HTTPException
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError

app = FastAPI()

DB_USER = os.getenv("DB_USER", "default_user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "default_password")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_NAME = os.getenv("DB_NAME", "default_db")

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:5432/{DB_NAME}"

engine = create_engine(DATABASE_URL)

@app.get("/")
def read_root():
    return {"status": "backend_is_running", "version": "1.1.0"}

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.get("/db-status")
def db_status_check():
    try:
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1"))
            if result.scalar() == 1:
                return {"db_status": "connected_successfully"}
    except OperationalError as e:
        raise HTTPException(status_code=503, detail=f"Database connection failed: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e}")