from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
import re

class SecretBase(BaseModel):
    key: str = Field(..., min_length=1, max_length=255, pattern=r'^[a-zA-Z0-9_-]+$')
    value: str = Field(..., min_length=1, max_length=4096)
    description: Optional[str] = Field(None, max_length=1000)

    @validator('key')
    def validate_key(cls, v):
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError('Key must contain only letters, numbers, underscores, and hyphens')
        return v

class SecretCreate(SecretBase):
    pass

class SecretUpdate(BaseModel):
    value: Optional[str] = Field(None, min_length=1, max_length=4096)
    description: Optional[str] = Field(None, max_length=1000)

class SecretResponse(SecretBase):
    id: int
    created_at: datetime
    updated_at: datetime
    is_deleted: bool
    deleted_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class SearchPayload(BaseModel):
    filters: Optional[Dict[str, Any]] = None
    sort_by: Optional[str] = Field(None, pattern=r'^(key|value|created_at|updated_at)$')
    sort_order: Optional[str] = Field("asc", pattern=r'^(asc|desc)$')
    include_deleted: Optional[bool] = False
    page: Optional[int] = Field(1, ge=1)
    page_size: Optional[int] = Field(10, ge=1, le=100)

    @validator('sort_by')
    def validate_sort_by(cls, v):
        if v and v not in ['key', 'value', 'created_at', 'updated_at']:
            raise ValueError('Invalid sort field')
        return v