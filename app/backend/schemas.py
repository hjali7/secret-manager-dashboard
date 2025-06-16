from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

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

class SearchPayload(BaseModel):
    filters: Optional[Dict[str, Any]] = None
    sort_by: Optional[str] = None
    sort_order: Optional[str] = "asc"