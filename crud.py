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
    
    # Return response format with string ID
    return schemas.AffiliateRequestResponse(
        id=str(affiliate_request.id),
        name=affiliate_request.name,
        email=affiliate_request.email,
        location=affiliate_request.location,
        language=affiliate_request.language,
        onemove_link=affiliate_request.onemove_link,
        puprime_link=affiliate_request.puprime_link,
        status=affiliate_request.status,
        created_at=affiliate_request.created_at,
        reviewed_at=affiliate_request.reviewed_at
    )

async def get_pending_requests():
    """Get all pending affiliate requests"""
    requests = await models.AffiliateRequest.find(
        models.AffiliateRequest.status == models.RequestStatus.PENDING
    ).sort("-created_at").to_list()
    
    # Convert to response format with string IDs
    result = []
    for request in requests:
        result.append(schemas.AffiliateRequestResponse(
            id=str(request.id),
            name=request.name,
            email=request.email,
            location=request.location,
            language=request.language,
            onemove_link=request.onemove_link,
            puprime_link=request.puprime_link,
            status=request.status,
            created_at=request.created_at,
            reviewed_at=request.reviewed_at
        ))
    return result

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
    
    requests = await query.sort("-created_at").skip(skip).limit(page_size).to_list()
    
    # Convert to response format with string IDs
    result = []
    for request in requests:
        result.append(schemas.AffiliateRequestResponse(
            id=str(request.id),
            name=request.name,
            email=request.email,
            location=request.location,
            language=request.language,
            onemove_link=request.onemove_link,
            puprime_link=request.puprime_link,
            status=request.status,
            created_at=request.created_at,
            reviewed_at=request.reviewed_at
        ))
    return result

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
    try:
        user = await models.User.find_one(models.User.email == email)
        if not user or not verify_password(password, user.hashed_password):
            return None
        return user
    except Exception as e:
        print(f"Database error during authentication: {e}")
        return None

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

async def create_referral_registration(unique_link: str, registration_data: schemas.ReferralRegistrationRequest):
    """Create a new referral registration"""
    # Find the affiliate by unique link
    affiliate = await models.Affiliate.find_one(models.Affiliate.unique_link == unique_link)
    if not affiliate:
        return None
    
    # Check if email already exists
    existing_referral = await models.Referral.find_one(models.Referral.email == registration_data.email)
    if existing_referral:
        return None
    
    # Hash the password
    hashed_password = get_password_hash(registration_data.password)
    
    # Create referral record
    referral = models.Referral(
        affiliate_id=affiliate.id,
        unique_link=unique_link,
        full_name=registration_data.full_name,
        email=registration_data.email,
        hashed_password=hashed_password,
        timezone=registration_data.timezone,
        location=registration_data.location,
        headline=registration_data.headline,
        bio=registration_data.bio,
        broker_id=registration_data.broker_id,
        invited_person=registration_data.invited_person,
        find_us=registration_data.find_us
    )
    await referral.insert()
    
    # Return response format with string IDs
    return schemas.ReferralResponse(
        id=str(referral.id),
        affiliate_id=str(referral.affiliate_id),
        unique_link=referral.unique_link,
        full_name=referral.full_name,
        email=referral.email,
        timezone=referral.timezone,
        location=referral.location,
        headline=referral.headline,
        bio=referral.bio,
        broker_id=referral.broker_id,
        invited_person=referral.invited_person,
        find_us=referral.find_us,
        created_at=referral.created_at
    )

async def get_referrals_by_affiliate(affiliate_id: str, page: int = 1, page_size: int = 20):
    """Get all referrals for a specific affiliate (paginated)"""
    if page < 1:
        page = 1
    if page_size < 1:
        page_size = 1
    if page_size > 100:
        page_size = 100
    skip = (page - 1) * page_size

    from beanie import PydanticObjectId
    referrals = await models.Referral.find(
        models.Referral.affiliate_id == PydanticObjectId(affiliate_id)
    ).sort("-created_at").skip(skip).limit(page_size).to_list()
    
    # Convert to response format with string IDs
    result = []
    for referral in referrals:
        result.append(schemas.ReferralResponse(
            id=str(referral.id),
            affiliate_id=str(referral.affiliate_id),
            unique_link=referral.unique_link,
            full_name=referral.full_name,
            email=referral.email,
            timezone=referral.timezone,
            location=referral.location,
            headline=referral.headline,
            bio=referral.bio,
            broker_id=referral.broker_id,
            invited_person=referral.invited_person,
            find_us=referral.find_us,
            created_at=referral.created_at
        ))
    return result

async def get_referral_count_by_affiliate(affiliate_id: str):
    """Get total count of referrals for a specific affiliate"""
    from beanie import PydanticObjectId
    return await models.Referral.find(models.Referral.affiliate_id == PydanticObjectId(affiliate_id)).count()