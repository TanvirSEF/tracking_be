from beanie import Document, PydanticObjectId
from pydantic import Field, ConfigDict
from typing import Optional
from datetime import datetime, timedelta
from enum import Enum
import secrets

class RequestStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"

class TicketPriority(str, Enum):
    AVERAGE = "average"
    MEDIUM = "medium"
    HIGH = "high"

class TicketStatus(str, Enum):
    OPEN = "open"
    ONGOING = "ongoing"
    CLOSED = "closed"

class TicketType(str, Enum):
    AFFILIATE_TO_ADMIN = "affiliate_to_admin"
    MEMBER_TO_AFFILIATE = "member_to_affiliate"

class User(Document):
    email: str = Field(..., unique=True, index=True)
    hashed_password: str
    is_admin: bool = Field(default=False)
    is_active: bool = Field(default=True)
    is_email_verified: bool = Field(default=True)  # Auto-verified, no OTP required
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "users"

class AffiliateRequest(Document):
    model_config = ConfigDict(populate_by_name=True)
    
    name: str
    email: str = Field(..., unique=True, index=True)
    hashed_password: str
    location: str
    language: str
    puprime_referral_code: Optional[str] = Field(None, alias="onemove_link", serialization_alias="onemove_link")
    puprime_link: str
    status: RequestStatus = Field(default=RequestStatus.PENDING)
    is_email_verified: bool = Field(default=True)  # Auto-verified, no OTP required
    created_at: datetime = Field(default_factory=datetime.utcnow)
    reviewed_at: Optional[datetime] = None
    reviewed_by: Optional[str] = None

    class Settings:
        name = "affiliate_requests"

class Affiliate(Document):
    model_config = ConfigDict(populate_by_name=True)
    
    user_id: PydanticObjectId = Field(..., unique=True, index=True)
    name: str
    location: str
    language: str
    puprime_referral_code: Optional[str] = Field(None, alias="onemove_link", serialization_alias="onemove_link")
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
    headline: Optional[str] = None
    bio: Optional[str] = None
    broker_id: Optional[str] = None
    invited_person: str
    find_us: str
    onemove_link: Optional[str] = None
    puprime_verification: Optional[bool] = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "referrals"

class EmailVerificationToken(Document):
    email: str = Field(..., index=True)
    token: str = Field(..., unique=True, index=True)
    token_type: str = Field(..., index=True)  # "admin_registration", "affiliate_registration", "referral_registration"
    expires_at: datetime
    is_used: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    used_at: Optional[datetime] = None

    class Settings:
        name = "email_verification_tokens"

class AffiliateNote(Document):
    affiliate_id: PydanticObjectId = Field(..., index=True)  # Which affiliate created the note
    referral_id: PydanticObjectId = Field(..., index=True)   # Which referral the note is about
    title: str
    note: str  # The note content
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Settings:
        name = "affiliate_notes"

class AffiliateEmailTemplate(Document):
    """Email template that affiliates can customize for new member welcome emails"""
    affiliate_id: PydanticObjectId = Field(..., unique=True, index=True)  # One template per affiliate
    subject: str = Field(..., min_length=1, max_length=200)
    html_content: str = Field(..., min_length=1, max_length=10000)  # HTML email body
    text_content: Optional[str] = Field(None, max_length=10000)  # Plain text fallback
    is_active: bool = Field(default=True)  # Enable/disable template
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Settings:
        name = "affiliate_email_templates"


class SystemConfig(Document):
    admin_registration_link: str = Field(..., unique=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "system_config"

class SupportTicket(Document):
    """Support ticket model for both Affiliate->Admin and Member->Affiliate tickets"""
    ticket_type: TicketType  # "affiliate_to_admin" or "member_to_affiliate"
    
    # Creator information (who created the ticket)
    creator_id: PydanticObjectId = Field(..., index=True)  # Affiliate ID or Referral ID
    creator_email: str
    creator_name: str
    
    # Assignment (who should respond)
    # For AFFILIATE_TO_ADMIN: can be None (any admin) or specific admin_id
    # For MEMBER_TO_AFFILIATE: the affiliate_id
    assigned_to_id: Optional[PydanticObjectId] = Field(None, index=True)
    
    # Ticket content
    subject: str = Field(..., min_length=1, max_length=200)
    message: str = Field(..., min_length=1, max_length=5000)
    priority: TicketPriority = Field(default=TicketPriority.AVERAGE)
    status: TicketStatus = Field(default=TicketStatus.OPEN)
    image_url: Optional[str] = None  # Cloudinary URL
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    last_reply_at: Optional[datetime] = None  # Track when last reply was added
    
    class Settings:
        name = "support_tickets"

class TicketReply(Document):
    """Reply/message in a support ticket conversation"""
    ticket_id: PydanticObjectId = Field(..., index=True)  # Reference to SupportTicket
    
    # Sender information
    sender_id: PydanticObjectId  # User ID, Affiliate ID, or Referral ID
    sender_email: str
    sender_name: str
    sender_type: str  # "admin", "affiliate", or "member"
    
    # Reply content
    message: str = Field(..., min_length=1, max_length=5000)
    image_url: Optional[str] = None  # Cloudinary URL
    
    # Timestamp
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    
    class Settings:
        name = "ticket_replies"