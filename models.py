from beanie import Document, PydanticObjectId
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
    is_email_verified: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "users"

class AffiliateRequest(Document):
    name: str
    email: str = Field(..., unique=True, index=True)
    hashed_password: str
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
    user_id: PydanticObjectId = Field(..., unique=True, index=True)
    name: str
    location: str
    language: str
    onemove_link: str
    puprime_link: str
    unique_link: str = Field(..., unique=True, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "affiliates"

class Referral(Document):
    affiliate_id: PydanticObjectId = Field(..., index=True)  # Which affiliate referred them
    unique_link: str = Field(..., index=True)  # The affiliate's unique link used
    full_name: str
    email: str = Field(..., unique=True, index=True)
    hashed_password: str
    timezone: str
    location: str
    headline: str
    bio: str
    broker_id: str
    invited_person: str
    find_us: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "referrals"

class SystemConfig(Document):
    admin_registration_link: str = Field(..., unique=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "system_config"

class EmailVerification(Document):
    email: str = Field(..., index=True)
    verification_code: str = Field(..., index=True)
    is_verified: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime
    verified_at: Optional[datetime] = None

    class Settings:
        name = "email_verifications"