import os
import time
from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy import create_engine, text, Column, Integer, String, DateTime
from sqlalchemy.orm import sessionmaker, Session, declarative_base
from sqlalchemy.exc import OperationalError
from datetime import datetime
from pydantic import BaseModel
from typing import Optional, List

app = FastAPI()

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
    return {"status": "backend_is_running", "version": "2.0.0-CRUD"}

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

# SQLAlchemy setup
Base = declarative_base()

class Secret(Base):
    __tablename__ = "secrets"
    
    id = Column(Integer, primary_key=True, index=True)
    key = Column(String, unique=True, index=True)
    value = Column(String)
    description = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# Pydantic models for request/response
class SecretBase(BaseModel):
    key: str
    value: str
    description: Optional[str] = None

class SecretCreate(SecretBase):
    pass

class SecretUpdate(BaseModel):
    value: Optional[str] = None
    description: Optional[str] = None

class SecretResponse(SecretBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# Database session dependency
def get_db():
    creds = get_db_credentials()
    db_user = creds.get("DB_USER")
    db_password = creds.get("DB_PASSWORD")
    db_host = os.getenv("DB_HOST", "postgres-service")
    db_name = os.getenv("DB_NAME", "secrets_db")
    
    database_url = f"postgresql://{db_user}:{db_password}@{db_host}:5432/{db_name}"
    engine = create_engine(database_url)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    # Create tables if they don't exist
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# CRUD APIs
@app.post("/secrets/", response_model=SecretResponse)
def create_secret(secret: SecretCreate, db: Session = Depends(get_db)):
    db_secret = Secret(**secret.model_dump())
    try:
        db.add(db_secret)
        db.commit()
        db.refresh(db_secret)
        return db_secret
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Could not create secret: {str(e)}")

@app.get("/secrets/", response_model=List[SecretResponse])
def read_secrets(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    secrets = db.query(Secret).offset(skip).limit(limit).all()
    return secrets

@app.get("/secrets/{secret_id}", response_model=SecretResponse)
def read_secret(secret_id: int, db: Session = Depends(get_db)):
    secret = db.query(Secret).filter(Secret.id == secret_id).first()
    if secret is None:
        raise HTTPException(status_code=404, detail="Secret not found")
    return secret

@app.get("/secrets/key/{key}", response_model=SecretResponse)
def read_secret_by_key(key: str, db: Session = Depends(get_db)):
    secret = db.query(Secret).filter(Secret.key == key).first()
    if secret is None:
        raise HTTPException(status_code=404, detail="Secret not found")
    return secret

@app.put("/secrets/{secret_id}", response_model=SecretResponse)
def update_secret(secret_id: int, secret: SecretUpdate, db: Session = Depends(get_db)):
    db_secret = db.query(Secret).filter(Secret.id == secret_id).first()
    if db_secret is None:
        raise HTTPException(status_code=404, detail="Secret not found")
    
    update_data = secret.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_secret, key, value)
    
    try:
        db.commit()
        db.refresh(db_secret)
        return db_secret
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Could not update secret: {str(e)}")

@app.delete("/secrets/{secret_id}")
def delete_secret(secret_id: int, db: Session = Depends(get_db)):
    db_secret = db.query(Secret).filter(Secret.id == secret_id).first()
    if db_secret is None:
        raise HTTPException(status_code=404, detail="Secret not found")
    
    try:
        db.delete(db_secret)
        db.commit()
        return {"message": "Secret deleted successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Could not delete secret: {str(e)}")