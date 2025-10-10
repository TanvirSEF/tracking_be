from typing import Optional, List
from datetime import datetime

import models
import schemas
from auth_utils import get_password_hash, verify_password, generate_unique_affiliate_link
from config import settings
from beanie import PydanticObjectId
from typing import Optional

async def initialize_system():
    """Initialize system with admin link configuration"""
    admin_link = settings.ADMIN_REGISTRATION_LINK
    
    # Check if config exists
    config = await models.SystemConfig.find_one()
    if not config:
        config = models.SystemConfig(
            admin_registration_link=admin_link
        )
        await config.insert()
    
    # Initialize admin user if specified in env
    admin_email = settings.ADMIN_EMAIL
    admin_password = settings.ADMIN_PASSWORD
    
    if admin_email and admin_password:
        await create_admin_user(admin_email, admin_password)
    
    return config

async def create_admin_user(email: str, password: str):
    """Create an admin user if doesn't exist"""
    admin = await models.User.find_one(models.User.email == email)
    if not admin:
        hashed_password = get_password_hash(password)
        admin = models.User(
            email=email,
            hashed_password=hashed_password,
            is_admin=True
        )
        await admin.insert()
    return admin

async def get_admin_registration_link():
    """Get the fixed admin registration link"""
    config = await models.SystemConfig.find_one()
    if config:
        return config.admin_registration_link
    return settings.ADMIN_REGISTRATION_LINK

async def verify_registration_link(link_code: str):
    """Verify if the provided link is the valid admin registration link"""
    admin_link = await get_admin_registration_link()
    return link_code == admin_link

async def create_affiliate_request(request: schemas.AffiliateRequestCreate):
    """Create a new affiliate registration request"""
    # Check if email already exists in requests or users
    existing_request = await models.AffiliateRequest.find_one(
        models.AffiliateRequest.email == request.email
    )
    
    existing_user = await models.User.find_one(
        models.User.email == request.email
    )
    
    if existing_request or existing_user:
        return None
    
    hashed_password = get_password_hash(request.password)
    affiliate_request = models.AffiliateRequest(
        name=request.name,
        email=request.email,
        hashed_password=hashed_password,
        location=request.location,
        language=request.language,
        onemove_link=request.onemove_link,
        puprime_link=request.puprime_link
    )
    await affiliate_request.insert()
    return affiliate_request

async def get_pending_requests():
    """Get all pending affiliate requests"""
    return await models.AffiliateRequest.find(
        models.AffiliateRequest.status == models.RequestStatus.PENDING
    ).sort("-created_at").to_list()

async def get_all_requests(
    status: Optional[models.RequestStatus] = None,
    page: int = 1,
    page_size: int = 20,
):
    """Get all affiliate requests, optionally filtered by status, paginated"""
    if page < 1:
        page = 1
    if page_size < 1:
        page_size = 1
    if page_size > 100:
        page_size = 100

    skip = (page - 1) * page_size
    query = models.AffiliateRequest.find()
    if status:
        query = query.find(models.AffiliateRequest.status == status)
    return await query.sort("-created_at").skip(skip).limit(page_size).to_list()

async def approve_affiliate_request(request_id: str, admin_id: str):
    """Approve an affiliate request and create their account"""
    request = await models.AffiliateRequest.get(request_id)
    
    if not request or request.status != models.RequestStatus.PENDING:
        return None
    
    # Create user account
    user = models.User(
        email=request.email,
        hashed_password=request.hashed_password,
        is_admin=False
    )
    await user.insert()
    
    # Create affiliate profile with unique link
    # Ensure unique_link collision retry before insert
    max_attempts = 5
    unique_link = None
    for _ in range(max_attempts):
        candidate = generate_unique_affiliate_link()
        existing = await models.Affiliate.find_one(models.Affiliate.unique_link == candidate)
        if not existing:
            unique_link = candidate
            break
    if unique_link is None:
        # Fallback last attempt
        unique_link = generate_unique_affiliate_link()

    affiliate = models.Affiliate(
        user_id=user.id,
        name=request.name,
        location=request.location,
        language=request.language,
        onemove_link=request.onemove_link,
        puprime_link=request.puprime_link,
        unique_link=unique_link
    )
    await affiliate.insert()
    
    # Update request status
    request.status = models.RequestStatus.APPROVED
    request.reviewed_at = datetime.utcnow()
    request.reviewed_by = admin_id
    await request.save()
    
    return affiliate

async def reject_affiliate_request(request_id: str, admin_id: str):
    """Reject an affiliate request"""
    request = await models.AffiliateRequest.get(request_id)
    
    if not request or request.status != models.RequestStatus.PENDING:
        return None
    
    request.status = models.RequestStatus.REJECTED
    request.reviewed_at = datetime.utcnow()
    request.reviewed_by = admin_id
    await request.save()
    return request

async def authenticate_user(email: str, password: str):
    """Authenticate a user"""
    user = await models.User.find_one(models.User.email == email)
    if not user or not verify_password(password, user.hashed_password):
        return None
    return user

async def get_affiliate_by_user(user_id: PydanticObjectId):
    """Get affiliate profile by user ID"""
    return await models.Affiliate.find_one(models.Affiliate.user_id == user_id)

async def get_all_affiliates(page: int = 1, page_size: int = 20):
    """Get all approved affiliates (paginated)"""
    if page < 1:
        page = 1
    if page_size < 1:
        page_size = 1
    if page_size > 100:
        page_size = 100
    skip = (page - 1) * page_size

    affiliates = await models.Affiliate.find().sort("-created_at").skip(skip).limit(page_size).to_list()
    result = []
    for affiliate in affiliates:
        user = await models.User.find_one(models.User.id == affiliate.user_id)
        if user and user.is_active:
            result.append(affiliate)
    return result