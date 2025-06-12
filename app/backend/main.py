import os
from fastapi import FastAPI, HTTPException
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError

app = FastAPI()

DB_USER = os.getenv("POSTGRES_USER")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_NAME = os.getenv("POSTGRES_DB")

@app.get("/")
def read_root():
    return {"status": "backend_is_running", "version": "1.3.0-simple-db"}

@app.get("/db-status")
def db_status_check():
    if not all([DB_USER, DB_PASSWORD, DB_HOST, DB_NAME]):
        raise HTTPException(status_code=500, detail="Database environment variables are not set.")

    DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:5432/{DB_NAME}"
    try:
        engine = create_engine(DATABASE_URL)
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1"))
            if result.scalar() == 1:
                return {"db_status": "connected_successfully_via_k8s_secret"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Database connection failed: {e}")