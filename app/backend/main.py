import os
import time
from fastapi import FastAPI, HTTPException, Depends, Query
from sqlalchemy import create_engine, text, Column, Integer, String, DateTime
from sqlalchemy.orm import sessionmaker, Session, declarative_base
from sqlalchemy.exc import OperationalError
from datetime import datetime, timedelta
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from cache.redis_cache import RedisCache
from search.search_utils import SearchFilter, apply_search_filters

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

# Initialize Redis cache
redis_cache = RedisCache(
    host=os.getenv("REDIS_HOST", "localhost"),
    port=int(os.getenv("REDIS_PORT", 6379))
)

# Update SecretResponse to include cache control
class SecretResponse(SecretBase):
    id: int
    created_at: datetime
    updated_at: datetime
    cache_control: Optional[str] = None

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

# Updated CRUD APIs with caching and search
@app.post("/secrets/", response_model=SecretResponse)
def create_secret(secret: SecretCreate, db: Session = Depends(get_db)):
    db_secret = Secret(**secret.model_dump())
    try:
        db.add(db_secret)
        db.commit()
        db.refresh(db_secret)
        # Invalidate cache for all secrets
        redis_cache.clear_pattern("secrets:*")
        return db_secret
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Could not create secret: {str(e)}")

@app.get("/secrets/", response_model=List[SecretResponse])
def read_secrets(
    skip: int = 0,
    limit: int = 100,
    sort_by: Optional[str] = None,
    sort_order: Optional[str] = "asc",
    search: Optional[str] = None,
    filters: Optional[Dict[str, Any]] = None,
    db: Session = Depends(get_db)
):
    # Try to get from cache first
    cache_key = f"secrets:list:{skip}:{limit}:{sort_by}:{sort_order}:{search}:{filters}"
    cached_result = redis_cache.get(cache_key)
    if cached_result:
        return cached_result

    # Build query
    query = db.query(Secret)
    
    # Apply search if provided
    if search:
        search_filter = SearchFilter(query)
        search_filter.add_filter("key", "ilike", search)
        search_filter.add_filter("description", "ilike", search)
        query = search_filter.apply()
    
    # Apply custom filters if provided
    if filters:
        query = apply_search_filters(query, filters)
    
    # Apply sorting
    if sort_by:
        search_filter = SearchFilter(query)
        search_filter.add_sort(sort_by, sort_order)
        query = search_filter.apply()
    
    # Apply pagination
    secrets = query.offset(skip).limit(limit).all()
    
    # Cache the results
    redis_cache.set(cache_key, secrets, timedelta(minutes=5))
    
    return secrets

@app.get("/secrets/{secret_id}", response_model=SecretResponse)
def read_secret(secret_id: int, db: Session = Depends(get_db)):
    # Try to get from cache first
    cache_key = f"secrets:{secret_id}"
    cached_result = redis_cache.get(cache_key)
    if cached_result:
        return cached_result

    secret = db.query(Secret).filter(Secret.id == secret_id).first()
    if secret is None:
        raise HTTPException(status_code=404, detail="Secret not found")
    
    # Cache the result
    redis_cache.set(cache_key, secret, timedelta(minutes=5))
    
    return secret

@app.get("/secrets/key/{key}", response_model=SecretResponse)
def read_secret_by_key(key: str, db: Session = Depends(get_db)):
    # Try to get from cache first
    cache_key = f"secrets:key:{key}"
    cached_result = redis_cache.get(cache_key)
    if cached_result:
        return cached_result

    secret = db.query(Secret).filter(Secret.key == key).first()
    if secret is None:
        raise HTTPException(status_code=404, detail="Secret not found")
    
    # Cache the result
    redis_cache.set(cache_key, secret, timedelta(minutes=5))
    
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
        # Invalidate related caches
        redis_cache.delete(f"secrets:{secret_id}")
        redis_cache.delete(f"secrets:key:{db_secret.key}")
        redis_cache.clear_pattern("secrets:list:*")
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
        # Get the key before deleting for cache invalidation
        secret_key = db_secret.key
        db.delete(db_secret)
        db.commit()
        # Invalidate related caches
        redis_cache.delete(f"secrets:{secret_id}")
        redis_cache.delete(f"secrets:key:{secret_key}")
        redis_cache.clear_pattern("secrets:list:*")
        return {"message": "Secret deleted successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Could not delete secret: {str(e)}")