from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional
from datetime import datetime
from enum import Enum

class RequestStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"

class UserBase(BaseModel):
    email: EmailStr

class UserCreate(UserBase):
    password: str = Field(..., min_length=6)

class User(UserBase):
    id: str
    is_admin: bool
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True

class AffiliateRequestCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    email: EmailStr
    password: str = Field(..., min_length=6)
    location: str = Field(..., min_length=1, max_length=255)
    language: str = Field(..., min_length=1, max_length=100)
    onemove_link: str = Field(..., min_length=1)
    puprime_link: str = Field(..., min_length=1)
    
    @validator('name', 'location', 'language')
    def strip_whitespace(cls, v):
        return v.strip()

class AffiliateRequestResponse(BaseModel):
    id: str
    name: str
    email: str
    location: str
    language: str
    onemove_link: str
    puprime_link: str
    status: RequestStatus
    created_at: datetime
    reviewed_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class AffiliateResponse(BaseModel):
    id: str
    name: str
    email: str
    location: str
    language: str
    onemove_link: str
    puprime_link: str
    unique_link: str
    created_at: datetime

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None

class LoginForm(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1)

class ApprovalRequest(BaseModel):
    request_id: str
    approve: bool
    reason: Optional[str] = None

class ReferralRegistrationRequest(BaseModel):
    full_name: str = Field(..., min_length=1, max_length=255)
    email: EmailStr
    password: str = Field(..., min_length=6)
    timezone: str = Field(..., min_length=1, max_length=100)
    location: str = Field(..., min_length=1, max_length=255)
    headline: str = Field(..., min_length=1, max_length=500)
    bio: str = Field(..., min_length=1, max_length=2000)
    broker_id: str = Field(..., min_length=1, max_length=100)
    invited_person: str = Field(..., min_length=1, max_length=255)
    find_us: str = Field(..., min_length=1, max_length=500)
    
    @validator('full_name', 'location', 'headline', 'bio', 'broker_id', 'invited_person', 'find_us')
    def strip_whitespace(cls, v):
        return v.strip()

class ReferralResponse(BaseModel):
    id: str
    affiliate_id: str
    unique_link: str
    full_name: str
    email: str
    timezone: str
    location: str
    headline: str
    bio: str
    broker_id: str
    invited_person: str
    find_us: str
    created_at: datetime

    class Config:
        from_attributes = True

class AdminRegistrationLinkResponse(BaseModel):
    registration_link: str
    full_url: str