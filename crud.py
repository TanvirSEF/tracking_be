from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime

import models
import schemas
from auth_utils import get_password_hash, verify_password, generate_unique_affiliate_link
from config import settings

def initialize_system(db: Session):
    """Initialize system with admin link configuration"""
    admin_link = settings.ADMIN_REGISTRATION_LINK
    
    # Check if config exists
    config = db.query(models.SystemConfig).first()
    if not config:
        config = models.SystemConfig(
            admin_registration_link=admin_link
        )
        db.add(config)
        db.commit()
        db.refresh(config)
    
    # Initialize admin user if specified in env
    admin_email = settings.ADMIN_EMAIL
    admin_password = settings.ADMIN_PASSWORD
    
    if admin_email and admin_password:
        create_admin_user(db, admin_email, admin_password)
    
    return config

def create_admin_user(db: Session, email: str, password: str):
    """Create an admin user if doesn't exist"""
    admin = db.query(models.User).filter(models.User.email == email).first()
    if not admin:
        hashed_password = get_password_hash(password)
        admin = models.User(
            email=email,
            hashed_password=hashed_password,
            is_admin=True
        )
        db.add(admin)
        db.commit()
        db.refresh(admin)
    return admin

def get_admin_registration_link(db: Session):
    """Get the fixed admin registration link"""
    config = db.query(models.SystemConfig).first()
    if config:
        return config.admin_registration_link
    return settings.ADMIN_REGISTRATION_LINK

def verify_registration_link(db: Session, link_code: str):
    """Verify if the provided link is the valid admin registration link"""
    admin_link = get_admin_registration_link(db)
    return link_code == admin_link

def create_affiliate_request(db: Session, request: schemas.AffiliateRequestCreate):
    """Create a new affiliate registration request"""
    # Check if email already exists in requests or users
    existing_request = db.query(models.AffiliateRequest).filter(
        models.AffiliateRequest.email == request.email
    ).first()
    
    existing_user = db.query(models.User).filter(
        models.User.email == request.email
    ).first()
    
    if existing_request or existing_user:
        return None
    
    hashed_password = get_password_hash(request.password)
    affiliate_request = models.AffiliateRequest(
        name=request.name,
        email=request.email,
        password=hashed_password,
        location=request.location,
        language=request.language,
        onemove_link=request.onemove_link,
        puprime_link=request.puprime_link
    )
    db.add(affiliate_request)
    db.commit()
    db.refresh(affiliate_request)
    return affiliate_request

def get_pending_requests(db: Session):
    """Get all pending affiliate requests"""
    return db.query(models.AffiliateRequest).filter(
        models.AffiliateRequest.status == models.RequestStatus.PENDING
    ).order_by(models.AffiliateRequest.created_at.desc()).all()

def get_all_requests(db: Session, status: Optional[models.RequestStatus] = None):
    """Get all affiliate requests, optionally filtered by status"""
    query = db.query(models.AffiliateRequest)
    if status:
        query = query.filter(models.AffiliateRequest.status == status)
    return query.order_by(models.AffiliateRequest.created_at.desc()).all()

def approve_affiliate_request(db: Session, request_id: int, admin_id: int):
    """Approve an affiliate request and create their account"""
    request = db.query(models.AffiliateRequest).filter(
        models.AffiliateRequest.id == request_id
    ).first()
    
    if not request or request.status != models.RequestStatus.PENDING:
        return None
    
    # Create user account
    user = models.User(
        email=request.email,
        hashed_password=request.password,
        is_admin=False
    )
    db.add(user)
    db.flush()
    
    # Create affiliate profile with unique link
    affiliate = models.Affiliate(
        user_id=user.id,
        name=request.name,
        location=request.location,
        language=request.language,
        onemove_link=request.onemove_link,
        puprime_link=request.puprime_link,
        unique_link=generate_unique_affiliate_link()
    )
    db.add(affiliate)
    
    # Update request status
    request.status = models.RequestStatus.APPROVED
    request.reviewed_at = datetime.utcnow()
    request.reviewed_by = admin_id
    
    db.commit()
    db.refresh(affiliate)
    return affiliate

def reject_affiliate_request(db: Session, request_id: int, admin_id: int):
    """Reject an affiliate request"""
    request = db.query(models.AffiliateRequest).filter(
        models.AffiliateRequest.id == request_id
    ).first()
    
    if not request or request.status != models.RequestStatus.PENDING:
        return None
    
    request.status = models.RequestStatus.REJECTED
    request.reviewed_at = datetime.utcnow()
    request.reviewed_by = admin_id
    db.commit()
    db.refresh(request)
    return request

def authenticate_user(db: Session, email: str, password: str):
    """Authenticate a user"""
    user = db.query(models.User).filter(models.User.email == email).first()
    if not user or not verify_password(password, user.hashed_password):
        return None
    return user

def get_affiliate_by_user(db: Session, user_id: int):
    """Get affiliate profile by user ID"""
    return db.query(models.Affiliate).filter(models.Affiliate.user_id == user_id).first()

def get_all_affiliates(db: Session):
    """Get all approved affiliates"""
    return db.query(models.Affiliate).join(models.User).filter(
        models.User.is_active == True
    ).order_by(models.Affiliate.created_at.desc()).all()
