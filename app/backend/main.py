import os
import json
import logging
from fastapi import FastAPI, HTTPException, Depends, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import timedelta
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import time
from sqlalchemy import text
from database import SessionLocal, get_db_session
import models
import schemas
from cache.redis_cache import RedisCache
from search.search_utils import apply_search_filters

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)

# Initialize FastAPI app
app = FastAPI(
    title="Secret Manager API",
    description="A secure API for managing secrets",
    version="1.2.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add rate limiter to app state
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("ALLOWED_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize cache
cache = RedisCache(host=os.getenv("REDIS_HOST", "redis-service"))

@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global error handler caught: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"}
    )

@app.get("/health")
@limiter.limit("30/minute")
async def health_check(request: Request):
    try:
        # Check database connection
        with get_db_session() as db:
            db.execute(text("SELECT 1"))
        
        # Check Redis connection
        cache.ping()
        
        return {
            "status": "healthy",
            "database": "connected",
            "cache": "connected",
            "version": "1.2.0"
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service unhealthy"
        )

@app.get("/")
@limiter.limit("30/minute")
async def read_root(request: Request):
    return {"status": "backend_is_running", "version": "v1.2.0"}

@app.post("/secrets/", response_model=schemas.SecretResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("60/minute")
async def create_secret(
    request: Request,
    secret: schemas.SecretCreate,
    db: Session = Depends(get_db_session)
):
    try:
        # Check if secret with same key exists
        existing = db.query(models.Secret).filter(
            models.Secret.key == secret.key,
            models.Secret.is_deleted == False
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Secret with this key already exists"
            )

        db_secret = models.Secret(**secret.model_dump())
        db.add(db_secret)
        db.commit()
        db.refresh(db_secret)
        
        # Clear relevant cache entries
        cache.clear_pattern("secrets:*")
        logger.info(f"Created new secret with key: {secret.key}")
        
        return db_secret
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating secret: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create secret"
        )

@app.get("/secrets/", response_model=List[schemas.SecretResponse])
@limiter.limit("120/minute")
async def read_secrets(
    request: Request,
    skip: int = 0,
    limit: int = 100,
    include_deleted: bool = False,
    db: Session = Depends(get_db_session)
):
    try:
        cache_key = f"secrets:list:{skip}:{limit}:{include_deleted}"
        
        cached_data = cache.get(cache_key)
        if cached_data:
            logger.info("Cache hit for secrets list")
            return [schemas.SecretResponse.model_validate(item) for item in cached_data]

        logger.info("Cache miss, fetching from DB")
        query = db.query(models.Secret)
        if not include_deleted:
            query = query.filter(models.Secret.is_deleted == False)
            
        secrets_from_db = query.offset(skip).limit(limit).all()
        
        secrets_to_cache = [schemas.SecretResponse.from_orm(s).model_dump() for s in secrets_from_db]
        cache.set(cache_key, secrets_to_cache, ttl=timedelta(minutes=1))
        
        return secrets_from_db
    except Exception as e:
        logger.error(f"Error fetching secrets: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch secrets"
        )

@app.post("/secrets/search", response_model=List[schemas.SecretResponse])
@limiter.limit("60/minute")
def search_secrets(payload: schemas.SearchPayload, db: Session = Depends(database.get_db)):
    try:
        query = db.query(models.Secret)

        # اعمال فیلترهای داینامیک
        if payload.filters:
            query = apply_search_filters(query, payload.filters)
        
        # اعمال مرتب‌سازی (Sorting)
        if payload.sort_by:
            sort_column = getattr(models.Secret, payload.sort_by, None)
            if sort_column:
                if payload.sort_order.lower() == "desc":
                    query = query.order_by(sort_column.desc())
                else:
                    query = query.order_by(sort_column.asc())
        
        secrets = query.all()
        return secrets
    except AttributeError:
        # اگر کاربر یک فیلد نامعتبر برای sort_by فرستاد
        raise HTTPException(status_code=400, detail=f"Invalid sort field specified: {payload.sort_by}")
    except Exception as e:
        logger.error(f"Error during secret search: {str(e)}")
        raise HTTPException(status_code=500, detail="An error occurred while searching for secrets.")