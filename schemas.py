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
    is_email_verified: bool
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
    is_email_verified: bool
    created_at: datetime
    reviewed_at: Optional[datetime] = None
    reviewed_by: Optional[str] = None

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
    headline: Optional[str] = Field(None, min_length=0, max_length=500)
    bio: Optional[str] = Field(None, min_length=0, max_length=2000)
    broker_id: Optional[str] = Field(None, min_length=0, max_length=100)
    invited_person: str = Field(..., min_length=1, max_length=255)
    find_us: str = Field(..., min_length=1, max_length=500)
    onemove_link: str = Field(..., min_length=1)
    
    @validator('full_name', 'location', 'headline', 'bio', 'broker_id', 'invited_person', 'find_us', 'onemove_link')
    def strip_whitespace(cls, v):
        if v is not None:
            return v.strip()
        return v

class ReferralResponse(BaseModel):
    id: str
    affiliate_id: str
    unique_link: str
    full_name: str
    email: str
    timezone: str
    location: str
    headline: Optional[str] = None
    bio: Optional[str] = None
    broker_id: Optional[str] = None
    invited_person: str
    find_us: str
    onemove_link: str
    created_at: datetime

    class Config:
        from_attributes = True

class AdminRegistrationLinkResponse(BaseModel):
    registration_link: str
    full_url: str

class PasswordResetRequest(BaseModel):
    email: EmailStr

class PasswordResetConfirm(BaseModel):
    token: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=6)

class PasswordResetResponse(BaseModel):
    message: str
    email: str
    expires_in_hours: int = 24

class AdminLoginForm(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1)

class AffiliateLoginForm(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1)

class ReferralLoginForm(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1)

class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    user_type: str
    email: str
    is_admin: bool