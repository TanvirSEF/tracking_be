from beanie import Document
from pydantic import Field
from typing import Optional
from datetime import datetime
from enum import Enum

class RequestStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"

class User(Document):
    email: str = Field(..., unique=True, index=True)
    hashed_password: str
    is_admin: bool = Field(default=False)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "users"

class AffiliateRequest(Document):
    name: str
    email: str = Field(..., unique=True, index=True)
    password: str
    location: str
    language: str
    onemove_link: str
    puprime_link: str
    status: RequestStatus = Field(default=RequestStatus.PENDING)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    reviewed_at: Optional[datetime] = None
    reviewed_by: Optional[str] = None

    class Settings:
        name = "affiliate_requests"

class Affiliate(Document):
    user_id: str = Field(..., unique=True, index=True)
    name: str
    location: str
    language: str
    onemove_link: str
    puprime_link: str
    unique_link: str = Field(..., unique=True, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "affiliates"

class SystemConfig(Document):
    admin_registration_link: str = Field(..., unique=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "system_config"