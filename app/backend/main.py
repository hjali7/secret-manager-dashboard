import json
from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List
from datetime import timedelta

from database import SessionLocal
import models
import schemas
from cache.redis_cache import RedisCache
from search.search_utils import apply_search_filters

app = FastAPI()
cache = RedisCache(host=os.getenv("REDIS_HOST", "redis-service"))

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/")
def read_root():
    return {"status": "backend_is_running", "version": "v1.2.0-final"}

@app.post("/secrets/", response_model=schemas.SecretResponse)
def create_secret(secret: schemas.SecretCreate, db: Session = Depends(get_db)):
    db_secret = models.Secret(**secret.model_dump())
    db.add(db_secret)
    db.commit()
    db.refresh(db_secret)
    cache.clear_pattern("secrets:*")
    return db_secret

@app.get("/secrets/", response_model=List[schemas.SecretResponse])
def read_secrets(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    cache_key = f"secrets:list:{skip}:{limit}"
    
    cached_data = cache.get(cache_key)
    if cached_data:
        print("CACHE HIT!")
        return [schemas.SecretResponse.model_validate(item) for item in cached_data]

    print("CACHE MISS! Fetching from DB.")
    secrets_from_db = db.query(models.Secret).offset(skip).limit(limit).all()
    
    secrets_to_cache = [schemas.SecretResponse.from_orm(s).model_dump() for s in secrets_from_db]
    cache.set(cache_key, secrets_to_cache, ttl=timedelta(minutes=1))
    
    return secrets_from_db

@app.post("/secrets/search", response_model=List[schemas.SecretResponse])
def search_secrets(payload: schemas.SearchPayload, db: Session = Depends(get_db)):
    query = db.query(models.Secret)
    if payload.filters:
        query = apply_search_filters(query, payload.filters)
    if payload.sort_by:
        query = query.order_by(getattr(getattr(models.Secret, payload.sort_by), payload.sort_order)())
        
    secrets = query.all()
    return secrets