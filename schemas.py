from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, List
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
    puprime_referral_code: str = Field(..., min_length=1)
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
    puprime_referral_code: Optional[str] = None
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
    puprime_referral_code: Optional[str] = None
    puprime_link: str
    unique_link: str
    created_at: datetime

    class Config:
        from_attributes = True

class AffiliateProfileUpdate(BaseModel):
    """Schema for updating affiliate profile"""
    name: str = Field(..., min_length=1, max_length=255)
    location: str = Field(..., min_length=1, max_length=255)
    language: str = Field(..., min_length=1, max_length=100)
    puprime_referral_code: str = Field(..., min_length=1)
    puprime_link: str = Field(..., min_length=1)
    
    @validator('name', 'location', 'language', 'puprime_referral_code', 'puprime_link')
    def strip_whitespace(cls, v):
        if v is not None:
            return v.strip()
        return v

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
    puprime_verification: bool
    created_at: datetime

    class Config:
        from_attributes = True

class ReferralProfileUpdate(BaseModel):
    """Schema for updating referral/member profile"""
    full_name: Optional[str] = Field(None, min_length=1, max_length=255)
    timezone: Optional[str] = Field(None, min_length=1, max_length=100)
    location: Optional[str] = Field(None, min_length=1, max_length=255)
    headline: Optional[str] = Field(None, min_length=0, max_length=500)
    bio: Optional[str] = Field(None, min_length=0, max_length=2000)
    broker_id: Optional[str] = Field(None, min_length=0, max_length=100)
    onemove_link: Optional[str] = Field(None, min_length=1)
    
    @validator('full_name', 'timezone', 'location', 'headline', 'bio', 'broker_id', 'onemove_link')
    def strip_whitespace(cls, v):
        if v is not None:
            return v.strip()
        return v

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

class AdminCreateRequest(BaseModel):
    """Schema for creating a new admin user"""
    email: EmailStr
    password: str = Field(..., min_length=6, description="Password must be at least 6 characters")

class AdminCreateResponse(BaseModel):
    """Response schema for admin creation"""
    message: str
    admin_id: str
    email: str
    is_admin: bool
    is_active: bool
    created_at: datetime
    created_by: str  # Email of the admin who created this admin

class AdminResponse(BaseModel):
    """Schema for admin user information"""
    id: str
    email: str
    is_admin: bool
    is_active: bool
    is_email_verified: bool
    created_at: datetime

class NoteCreate(BaseModel):
    """Schema for creating a note"""
    title: str = Field(..., min_length=1, max_length=200)
    note: str = Field(..., min_length=1, max_length=5000)
    
    @validator('title', 'note')
    def strip_whitespace(cls, v):
        return v.strip()

class NoteUpdate(BaseModel):
    """Schema for updating a note"""
    title: str = Field(..., min_length=1, max_length=200)
    note: str = Field(..., min_length=1, max_length=5000)
    
    @validator('title', 'note')
    def strip_whitespace(cls, v):
        return v.strip()

class NoteResponse(BaseModel):
    """Schema for note responses"""
    id: str
    affiliate_id: str
    referral_id: str
    title: str
    note: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class TopAffiliateResponse(BaseModel):
    """Schema for top affiliate by referral count"""
    id: str
    name: str
    email: str
    location: str
    language: str
    unique_link: str
    referral_count: int
    created_at: datetime
    
    class Config:
        from_attributes = True

# ==================== Support Ticket Schemas ====================

class TicketPriorityEnum(str, Enum):
    AVERAGE = "average"
    MEDIUM = "medium"
    HIGH = "high"

class TicketStatusEnum(str, Enum):
    OPEN = "open"
    ONGOING = "ongoing"
    CLOSED = "closed"

class TicketTypeEnum(str, Enum):
    AFFILIATE_TO_ADMIN = "affiliate_to_admin"
    MEMBER_TO_AFFILIATE = "member_to_affiliate"

class TicketCreateRequest(BaseModel):
    """Schema for creating a new support ticket"""
    subject: str = Field(..., min_length=1, max_length=200)
    message: str = Field(..., min_length=1, max_length=5000)
    priority: TicketPriorityEnum = Field(default=TicketPriorityEnum.AVERAGE)
    name: str = Field(..., min_length=1, max_length=255)
    email: EmailStr
    
    @validator('subject', 'message', 'name')
    def strip_whitespace(cls, v):
        return v.strip() if v else v

class TicketReplyRequest(BaseModel):
    """Schema for adding a reply to a ticket"""
    message: str = Field(..., min_length=1, max_length=5000)
    
    @validator('message')
    def strip_whitespace(cls, v):
        return v.strip() if v else v

class TicketUpdateRequest(BaseModel):
    """Schema for updating ticket status or priority"""
    status: Optional[TicketStatusEnum] = None
    priority: Optional[TicketPriorityEnum] = None

class TicketReplyResponse(BaseModel):
    """Schema for ticket reply response"""
    id: str
    ticket_id: str
    sender_id: str
    sender_email: str
    sender_name: str
    sender_type: str  # "admin", "affiliate", or "member"
    message: str
    image_url: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True

class TicketResponse(BaseModel):
    """Schema for ticket response"""
    id: str
    ticket_type: str
    creator_id: str
    creator_email: str
    creator_name: str
    assigned_to_id: Optional[str] = None
    subject: str
    message: str
    priority: str
    status: str
    image_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    last_reply_at: Optional[datetime] = None
    reply_count: int = 0  # Number of replies
    
    class Config:
        from_attributes = True

class TicketWithRepliesResponse(BaseModel):
    """Schema for ticket with all replies"""
    id: str
    ticket_type: str
    creator_id: str
    creator_email: str
    creator_name: str
    assigned_to_id: Optional[str] = None
    subject: str
    message: str
    priority: str
    status: str
    image_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    last_reply_at: Optional[datetime] = None
    replies: List[TicketReplyResponse] = []
    
    class Config:
        from_attributes = True

class TicketStatsResponse(BaseModel):
    """Schema for ticket statistics"""
    total_tickets: int
    open: int
    ongoing: int
    closed: int
    by_priority: dict  # {"high": 5, "medium": 10, "average": 15}
    tickets_today: int = 0

# ==================== Custom Email Schemas ====================

class CustomEmailRequest(BaseModel):
    """Schema for sending custom email to referral"""
    referral_id: str = Field(..., description="ID of the referral to send email to")
    subject: str = Field(..., min_length=1, max_length=200, description="Email subject")
    message: str = Field(..., min_length=1, max_length=5000, description="Email message content (HTML supported)")
    
    @validator('subject', 'message')
    def strip_whitespace(cls, v):
        return v.strip() if v else v

class CustomEmailResponse(BaseModel):
    """Response schema for custom email sending"""
    message: str
    referral_email: str
    referral_name: str
    sent_at: datetime

# ==================== Affiliate Email Template Schemas ====================

class EmailTemplateCreate(BaseModel):
    """Schema for creating an affiliate email template"""
    subject: str = Field(..., min_length=1, max_length=200, description="Email subject line")
    html_content: str = Field(..., min_length=1, max_length=10000, description="HTML email body (supports template variables)")
    text_content: Optional[str] = Field(None, max_length=10000, description="Plain text fallback (optional)")
    is_active: bool = Field(default=True, description="Enable/disable template")
    
    @validator('subject', 'html_content', 'text_content')
    def strip_whitespace(cls, v):
        return v.strip() if v else v

class EmailTemplateUpdate(BaseModel):
    """Schema for updating an affiliate email template"""
    subject: Optional[str] = Field(None, min_length=1, max_length=200, description="Email subject line")
    html_content: Optional[str] = Field(None, min_length=1, max_length=10000, description="HTML email body")
    text_content: Optional[str] = Field(None, max_length=10000, description="Plain text fallback")
    is_active: Optional[bool] = Field(None, description="Enable/disable template")
    
    @validator('subject', 'html_content', 'text_content')
    def strip_whitespace(cls, v):
        return v.strip() if v else v

class EmailTemplateResponse(BaseModel):
    """Schema for email template response"""
    id: str
    affiliate_id: str
    subject: str
    html_content: str
    text_content: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
