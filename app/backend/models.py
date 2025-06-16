from sqlalchemy import Column, Integer, String, DateTime, Boolean, Index
from sqlalchemy.orm import declarative_base
from datetime import datetime

Base = declarative_base()

class Secret(Base):
    __tablename__ = "secrets"
    
    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(255), unique=True, index=True, nullable=False)
    value = Column(String(4096), nullable=False)  # Increased length for larger secrets
    description = Column(String(1000), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    is_deleted = Column(Boolean, default=False, nullable=False)
    deleted_at = Column(DateTime, nullable=True)

    # Composite index for common search patterns
    __table_args__ = (
        Index('idx_secrets_key_value', 'key', 'value'),
        Index('idx_secrets_created_updated', 'created_at', 'updated_at'),
        Index('idx_secrets_deleted', 'is_deleted', 'deleted_at'),
    )

    def soft_delete(self):
        self.is_deleted = True
        self.deleted_at = datetime.utcnow()

    def restore(self):
        self.is_deleted = False
        self.deleted_at = None