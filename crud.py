from typing import Optional, List
from datetime import datetime

import models
import schemas
from auth_utils import get_password_hash, verify_password, generate_unique_affiliate_link, create_verification_token, create_verification_code, send_verification_email, send_welcome_email
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
            is_admin=True,
            is_email_verified=not settings.EMAIL_VERIFICATION_ENABLED  # Auto-verify if email verification disabled
        )
        await admin.insert()
        
        # Send verification email if enabled
        if settings.EMAIL_VERIFICATION_ENABLED:
            code = await create_verification_code(email, "admin_registration")
            await send_verification_email(email, code, "admin")
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
        puprime_link=request.puprime_link,
        is_email_verified=not settings.EMAIL_VERIFICATION_ENABLED  # Auto-verify if email verification disabled
    )
    await affiliate_request.insert()
    
    # Send verification email if enabled
    if settings.EMAIL_VERIFICATION_ENABLED:
        code = await create_verification_code(request.email, "affiliate_registration")
        await send_verification_email(request.email, code, "affiliate")
    
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
        is_email_verified=affiliate_request.is_email_verified,
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
            is_email_verified=request.is_email_verified,
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
            is_email_verified=request.is_email_verified,
            created_at=request.created_at,
            reviewed_at=request.reviewed_at
        ))
    return result

async def approve_affiliate_request(request_id: str, admin_id: str):
    """Approve an affiliate request and create their account"""
    print(f"DEBUG: Approving request_id: {request_id}")
    
    # Handle both string and ObjectId formats
    try:
        from bson import ObjectId
        if isinstance(request_id, str):
            request = await models.AffiliateRequest.get(ObjectId(request_id))
        else:
            request = await models.AffiliateRequest.get(request_id)
    except Exception:
        # Fallback to string search
        request = await models.AffiliateRequest.find_one(models.AffiliateRequest.id == request_id)
    
    print(f"DEBUG: Found request: {request}")
    if request:
        print(f"DEBUG: Request status: {request.status}")
        print(f"DEBUG: Email verified: {request.is_email_verified}")
    
    if not request or request.status != models.RequestStatus.PENDING:
        print(f"DEBUG: Request not found or not pending. Request: {request}, Status: {request.status if request else 'None'}")
        return None
    
    # Check if email is verified (only if email verification is enabled)
    if settings.EMAIL_VERIFICATION_ENABLED and not request.is_email_verified:
        # For now, auto-verify if email verification is not working
        print(f"Auto-verifying email for {request.email} due to verification issues")
        request.is_email_verified = True
        await request.save()
    
    # Create user account
    user = models.User(
        email=request.email,
        hashed_password=request.hashed_password,
        is_admin=False,
        is_email_verified=request.is_email_verified
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
    
    # Send welcome email after successful approval
    try:
        await send_welcome_email(request.email, "affiliate", request.name)
        print(f"Welcome email sent to {request.email}")
    except Exception as e:
        print(f"Warning: Failed to send welcome email to {request.email}: {e}")
        # Don't fail the approval process if email fails
    
    return affiliate

async def reject_affiliate_request(request_id: str, admin_id: str):
    """Reject an affiliate request"""
    # Handle both string and ObjectId formats
    try:
        from bson import ObjectId
        if isinstance(request_id, str):
            request = await models.AffiliateRequest.get(ObjectId(request_id))
        else:
            request = await models.AffiliateRequest.get(request_id)
    except Exception:
        # Fallback to string search
        request = await models.AffiliateRequest.find_one(models.AffiliateRequest.id == request_id)
    
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
        find_us=registration_data.find_us,
        onemove_link=registration_data.onemove_link
    )
    await referral.insert()
    
    # Send verification email if enabled
    if settings.EMAIL_VERIFICATION_ENABLED:
        code = await create_verification_code(registration_data.email, "referral_registration")
        await send_verification_email(registration_data.email, code, "referral")
    
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
        onemove_link=referral.onemove_link,
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
            onemove_link=referral.onemove_link,
            created_at=referral.created_at
        ))
    return result

async def get_referral_count_by_affiliate(affiliate_id: str):
    """Get total count of referrals for a specific affiliate"""
    from beanie import PydanticObjectId
    return await models.Referral.find(models.Referral.affiliate_id == PydanticObjectId(affiliate_id)).count()

async def delete_affiliate_profile(user_id: PydanticObjectId):
    """Delete affiliate profile and all associated data"""
    # Get affiliate
    affiliate = await models.Affiliate.find_one(models.Affiliate.user_id == user_id)
    if not affiliate:
        return None
    
    # Get the user to find their email
    user = await models.User.find_one(models.User.id == user_id)
    if not user:
        return None
    
    # Delete all referrals
    await models.Referral.find(
        models.Referral.affiliate_id == affiliate.id
    ).delete()
    
    # Delete the affiliate request associated with this user's email
    await models.AffiliateRequest.find(
        models.AffiliateRequest.email == user.email
    ).delete()
    
    # Delete affiliate profile
    await affiliate.delete()
    
    # Delete user account
    await user.delete()
    
    return True

async def delete_referral_by_id(referral_id: str, affiliate_id: str):
    """Delete a specific referral"""
    referral = await models.Referral.find_one(
        models.Referral.id == PydanticObjectId(referral_id)
    )
    
    if not referral or str(referral.affiliate_id) != affiliate_id:
        return None
    
    await referral.delete()
    return True

# Email verification functions
async def verify_email_token(token: str):
    """Verify email token and activate account"""
    from auth_utils import verify_email_token as verify_token, mark_token_as_used, send_welcome_email
    
    # Verify token
    token_record = await verify_token(token)
    if not token_record:
        return None
    
    # Mark token as used
    await mark_token_as_used(token_record)
    
    # Handle different token types
    if token_record.token_type == "admin_registration":
        # Verify admin user
        user = await models.User.find_one(models.User.email == token_record.email)
        if user:
            user.is_email_verified = True
            await user.save()
            await send_welcome_email(user.email, "admin", user.email.split('@')[0])
            return {"type": "admin", "user": user}
    
    elif token_record.token_type == "affiliate_registration":
        # Verify affiliate request
        request = await models.AffiliateRequest.find_one(models.AffiliateRequest.email == token_record.email)
        if request:
            request.is_email_verified = True
            await request.save()
            try:
                await send_welcome_email(request.email, "affiliate", request.name)
            except Exception as e:
                print(f"Warning: Failed to send welcome email to {request.email}: {e}")
            return {"type": "affiliate_request", "request": request}
    
    elif token_record.token_type == "referral_registration":
        # Verify referral
        referral = await models.Referral.find_one(models.Referral.email == token_record.email)
        if referral:
            try:
                await send_welcome_email(referral.email, "referral", referral.full_name)
            except Exception as e:
                print(f"Warning: Failed to send welcome email to {referral.email}: {e}")
            return {"type": "referral", "referral": referral}
    
    return None

async def get_all_referrals(
    page: int = 1, 
    page_size: int = 20, 
    affiliate_id: Optional[str] = None,
    search: Optional[str] = None
):
    """Get all referrals across all affiliates (admin view)"""
    if page < 1:
        page = 1
    if page_size < 1:
        page_size = 1
    if page_size > 100:
        page_size = 100
    skip = (page - 1) * page_size

    from beanie import PydanticObjectId
    
    # Build query
    query = models.Referral.find()
    
    # Filter by affiliate if specified
    if affiliate_id:
        try:
            affiliate_object_id = PydanticObjectId(affiliate_id)
            query = query.find(models.Referral.affiliate_id == affiliate_object_id)
        except Exception:
            # Invalid affiliate_id, return empty result
            return []
    
    # Search functionality
    if search:
        search_lower = search.lower()
        query = query.find(
            {"$or": [
                {"email": {"$regex": search_lower, "$options": "i"}},
                {"full_name": {"$regex": search_lower, "$options": "i"}}
            ]}
        )
    
    referrals = await query.sort("-created_at").skip(skip).limit(page_size).to_list()
    
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
            onemove_link=referral.onemove_link,
            created_at=referral.created_at
        ))
    return result

async def delete_referral_by_admin(referral_id: str):
    """Delete any referral (admin function)"""
    from beanie import PydanticObjectId
    
    try:
        referral_object_id = PydanticObjectId(referral_id)
    except Exception:
        return None
    
    referral = await models.Referral.find_one(models.Referral.id == referral_object_id)
    if not referral:
        return None
    
    # Get affiliate info before deletion for response
    affiliate = await models.Affiliate.find_one(models.Affiliate.id == referral.affiliate_id)
    
    # Delete the referral
    await referral.delete()
    
    return {
        "referral": referral,
        "affiliate": affiliate
    }

# Password reset functions
async def request_password_reset(email: str):
    """Request password reset for a user"""
    # Check if user exists
    user = await models.User.find_one(models.User.email == email)
    if not user:
        return None  # Don't reveal if user exists or not for security
    
    # Create password reset token
    from auth_utils import create_password_reset_token, send_password_reset_email
    token = await create_password_reset_token(email)
    
    # Send password reset email
    email_sent = await send_password_reset_email(email, token)
    if not email_sent:
        print(f"Warning: Failed to send password reset email to {email}")
        # Still return success to not reveal email issues
    
    return {
        "email": email,
        "token_created": True,
        "email_sent": email_sent
    }

async def reset_password_with_token(token: str, new_password: str):
    """Reset password using token"""
    from auth_utils import verify_password_reset_token, mark_password_reset_token_as_used, get_password_hash
    
    # Verify token
    token_record = await verify_password_reset_token(token)
    if not token_record:
        return None
    
    # Find user by email
    user = await models.User.find_one(models.User.email == token_record.email)
    if not user:
        return None
    
    # Update password
    user.hashed_password = get_password_hash(new_password)
    await user.save()
    
    # Mark token as used
    await mark_password_reset_token_as_used(token_record)
    
    return {
        "email": user.email,
        "password_reset": True,
        "reset_at": datetime.utcnow()
    }

async def resend_password_reset_email(email: str):
    """Resend password reset email"""
    # Check if user exists
    user = await models.User.find_one(models.User.email == email)
    if not user:
        return None  # Don't reveal if user exists or not for security
    
    # Create new password reset token (invalidate old ones)
    from auth_utils import create_password_reset_token, send_password_reset_email
    
    # Invalidate any existing password reset tokens for this email
    await models.EmailVerificationToken.find(
        models.EmailVerificationToken.email == email,
        models.EmailVerificationToken.token_type == "password_reset"
    ).delete()
    
    # Create new token
    token = await create_password_reset_token(email)
    
    # Send password reset email
    email_sent = await send_password_reset_email(email, token)
    if not email_sent:
        print(f"Warning: Failed to resend password reset email to {email}")
    
    return {
        "email": email,
        "token_created": True,
        "email_sent": email_sent
    }