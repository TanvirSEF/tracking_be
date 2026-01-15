from typing import Optional, List
from datetime import datetime

import models
import schemas
from auth_utils import get_password_hash, verify_password, generate_unique_affiliate_link, send_welcome_email
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
            is_email_verified=True  # Auto-verified, no OTP required
        )
        await admin.insert()
        
        # Send welcome email
        try:
            await send_welcome_email(email, "admin", email.split('@')[0])
        except Exception as e:
            print(f"Warning: Failed to send welcome email to {email}: {e}")
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
        puprime_referral_code=request.puprime_referral_code,
        puprime_link=request.puprime_link,
        is_email_verified=True  # Auto-verified, no OTP required
    )
    await affiliate_request.insert()
    
    # Return response format with string ID
    return schemas.AffiliateRequestResponse(
        id=str(affiliate_request.id),
        name=affiliate_request.name,
        email=affiliate_request.email,
        location=affiliate_request.location,
        language=affiliate_request.language,
        puprime_referral_code=affiliate_request.puprime_referral_code,
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
            puprime_referral_code=request.puprime_referral_code,
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
            puprime_referral_code=request.puprime_referral_code,
            puprime_link=request.puprime_link,
            status=request.status,
            is_email_verified=request.is_email_verified,
            created_at=request.created_at,
            reviewed_at=request.reviewed_at
        ))
    return result

async def approve_affiliate_request(request_id: str, admin_id: str):
    """Approve an affiliate request and create their account"""
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
    
    # Create user account (emails are auto-verified, no OTP required)
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
        puprime_referral_code=request.puprime_referral_code,
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
    """Reject an affiliate request and delete it from database"""
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
    
    # Store request info before deletion for response
    request_info = {
        "id": str(request.id),
        "email": request.email,
        "name": request.name,
        "status": "rejected",
        "reviewed_by": admin_id,
        "reviewed_at": datetime.utcnow()
    }
    
    # Delete the request from database
    await request.delete()
    
    return request_info

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

async def authenticate_referral(email: str, password: str):
    """Authenticate a referral/member"""
    try:
        referral = await models.Referral.find_one(models.Referral.email == email)
        if not referral or not verify_password(password, referral.hashed_password):
            return None
        return referral
    except Exception as e:
        print(f"Database error during referral authentication: {e}")
        return None

async def get_affiliate_by_user(user_id: PydanticObjectId):
    """Get affiliate profile by user ID"""
    return await models.Affiliate.find_one(models.Affiliate.user_id == user_id)

async def update_affiliate_profile(user_id: PydanticObjectId, update_data: schemas.AffiliateProfileUpdate):
    """Update affiliate profile information"""
    # Get the affiliate by user_id
    affiliate = await models.Affiliate.find_one(models.Affiliate.user_id == user_id)
    if not affiliate:
        return None
    
    # Update the fields
    affiliate.name = update_data.name
    affiliate.location = update_data.location
    affiliate.language = update_data.language
    affiliate.puprime_referral_code = update_data.puprime_referral_code
    affiliate.puprime_link = update_data.puprime_link
    
    # Save the changes
    await affiliate.save()
    
    return affiliate

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
    
    # Send welcome email using affiliate's custom template if available
    try:
        # Get affiliate's email template
        email_template = await models.AffiliateEmailTemplate.find_one(
            models.AffiliateEmailTemplate.affiliate_id == affiliate.id,
            models.AffiliateEmailTemplate.is_active == True
        )
        
        # Get affiliate user for email
        affiliate_user = await models.User.find_one(models.User.id == affiliate.user_id)
        
        if email_template and affiliate_user:
            # Send using affiliate's custom template
            from email_service import email_service
            template_dict = {
                'subject': email_template.subject,
                'html_content': email_template.html_content,
                'text_content': email_template.text_content
            }
            
            await email_service.send_affiliate_template_email(
                to_email=referral.email,
                affiliate_template=template_dict,
                member_name=referral.full_name,
                member_email=referral.email,
                affiliate_name=affiliate.name,
                affiliate_email=affiliate_user.email,
                unique_link=f"{settings.BASE_URL}/ref/{unique_link}",
                registration_date=referral.created_at.strftime("%Y-%m-%d %H:%M:%S")
            )
            print(f"[INFO] Sent custom template email to {referral.email}")
        else:
            # Send default welcome email
            from email_service import email_service
            await email_service.send_welcome_email(
                to_email=referral.email,
                user_type="member",
                name=referral.full_name
            )
            print(f"[INFO] Sent default welcome email to {referral.email}")
    except Exception as e:
        print(f"[WARNING] Failed to send welcome email to {referral.email}: {e}")
        # Don't fail registration if email fails
    
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
        puprime_verification=referral.puprime_verification if referral.puprime_verification is not None else False,
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
            puprime_verification=referral.puprime_verification if referral.puprime_verification is not None else False,
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
            puprime_verification=referral.puprime_verification if referral.puprime_verification is not None else False,
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

async def get_referral_by_id(referral_id: PydanticObjectId):
    """Get referral profile by referral ID"""
    referral = await models.Referral.find_one(models.Referral.id == referral_id)
    if not referral:
        return None
    
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
        puprime_verification=referral.puprime_verification if referral.puprime_verification is not None else False,
        created_at=referral.created_at
    )

async def update_referral_profile(referral_id: PydanticObjectId, update_data: schemas.ReferralProfileUpdate):
    """Update referral profile information"""
    referral = await models.Referral.find_one(models.Referral.id == referral_id)
    if not referral:
        return None
    
    # Update only provided fields
    update_dict = update_data.dict(exclude_unset=True)
    
    for field, value in update_dict.items():
        setattr(referral, field, value)
    
    await referral.save()
    
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
        puprime_verification=referral.puprime_verification if referral.puprime_verification is not None else False,
        created_at=referral.created_at
    )

async def delete_referral_profile(referral_id: PydanticObjectId):
    """Delete referral profile"""
    referral = await models.Referral.find_one(models.Referral.id == referral_id)
    if not referral:
        return None
    
    # Delete all notes associated with this referral
    notes_result = await models.AffiliateNote.find(
        models.AffiliateNote.referral_id == referral_id
    ).delete()
    
    # Get affiliate info before deletion
    affiliate = await models.Affiliate.find_one(models.Affiliate.id == referral.affiliate_id)
    
    # Delete the referral
    await referral.delete()
    
    return {
        "referral": referral,
        "affiliate": affiliate,
        "deleted_notes_count": notes_result.deleted_count if notes_result else 0
    }

async def get_affiliate_by_referral(referral_id: PydanticObjectId):
    """Get affiliate information for a specific referral"""
    referral = await models.Referral.find_one(models.Referral.id == referral_id)
    if not referral:
        return None
    
    affiliate = await models.Affiliate.find_one(models.Affiliate.id == referral.affiliate_id)
    if not affiliate:
        return None
    
    # Get user info for email
    user = await models.User.find_one(models.User.id == affiliate.user_id)
    if not user:
        return None
    
    return schemas.AffiliateResponse(
        id=str(affiliate.id),
        name=affiliate.name,
        email=user.email,
        location=affiliate.location,
        language=affiliate.language,
        puprime_referral_code=affiliate.puprime_referral_code,
        puprime_link=affiliate.puprime_link,
        unique_link=affiliate.unique_link,
        created_at=affiliate.created_at
    )

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

# ==================== Affiliate Notes CRUD Functions ====================

async def create_affiliate_note(affiliate_id: str, referral_id: str, note_data: schemas.NoteCreate):
    """Create a new note for a referral"""
    from beanie import PydanticObjectId
    
    # Verify referral exists and belongs to this affiliate
    referral = await models.Referral.find_one(
        models.Referral.id == PydanticObjectId(referral_id)
    )
    if not referral:
        return None
    
    if str(referral.affiliate_id) != affiliate_id:
        return None  # Referral doesn't belong to this affiliate
    
    # Create the note
    note = models.AffiliateNote(
        affiliate_id=PydanticObjectId(affiliate_id),
        referral_id=PydanticObjectId(referral_id),
        title=note_data.title,
        note=note_data.note
    )
    await note.insert()
    
    return schemas.NoteResponse(
        id=str(note.id),
        affiliate_id=str(note.affiliate_id),
        referral_id=str(note.referral_id),
        title=note.title,
        note=note.note,
        created_at=note.created_at,
        updated_at=note.updated_at
    )

async def get_notes_by_referral(affiliate_id: str, referral_id: str):
    """Get all notes for a specific referral (by that affiliate)"""
    from beanie import PydanticObjectId
    
    # Verify referral belongs to affiliate
    referral = await models.Referral.find_one(
        models.Referral.id == PydanticObjectId(referral_id)
    )
    if not referral or str(referral.affiliate_id) != affiliate_id:
        return None  # Unauthorized or not found
    
    # Get all notes
    notes = await models.AffiliateNote.find(
        models.AffiliateNote.affiliate_id == PydanticObjectId(affiliate_id),
        models.AffiliateNote.referral_id == PydanticObjectId(referral_id)
    ).sort("-created_at").to_list()
    
    result = []
    for note in notes:
        result.append(schemas.NoteResponse(
            id=str(note.id),
            affiliate_id=str(note.affiliate_id),
            referral_id=str(note.referral_id),
            title=note.title,
            note=note.note,
            created_at=note.created_at,
            updated_at=note.updated_at
        ))
    return result

async def get_all_notes_by_affiliate(affiliate_id: str, page: int = 1, page_size: int = 50):
    """Get all notes created by an affiliate (across all referrals)"""
    from beanie import PydanticObjectId
    
    if page < 1:
        page = 1
    if page_size < 1:
        page_size = 1
    if page_size > 100:
        page_size = 100
    skip = (page - 1) * page_size
    
    notes = await models.AffiliateNote.find(
        models.AffiliateNote.affiliate_id == PydanticObjectId(affiliate_id)
    ).sort("-updated_at").skip(skip).limit(page_size).to_list()
    
    result = []
    for note in notes:
        result.append(schemas.NoteResponse(
            id=str(note.id),
            affiliate_id=str(note.affiliate_id),
            referral_id=str(note.referral_id),
            title=note.title,
            note=note.note,
            created_at=note.created_at,
            updated_at=note.updated_at
        ))
    return result

async def update_affiliate_note(note_id: str, affiliate_id: str, note_data: schemas.NoteUpdate):
    """Update an existing note"""
    from beanie import PydanticObjectId
    
    # Find the note
    note = await models.AffiliateNote.find_one(
        models.AffiliateNote.id == PydanticObjectId(note_id)
    )
    
    if not note:
        return None
    
    # Verify note belongs to this affiliate
    if str(note.affiliate_id) != affiliate_id:
        return None  # Unauthorized
    
    # Update the note
    note.title = note_data.title
    note.note = note_data.note
    note.updated_at = datetime.utcnow()
    await note.save()
    
    return schemas.NoteResponse(
        id=str(note.id),
        affiliate_id=str(note.affiliate_id),
        referral_id=str(note.referral_id),
        title=note.title,
        note=note.note,
        created_at=note.created_at,
        updated_at=note.updated_at
    )

async def delete_affiliate_note(note_id: str, affiliate_id: str):
    """Delete a note"""
    from beanie import PydanticObjectId
    
    # Find the note
    note = await models.AffiliateNote.find_one(
        models.AffiliateNote.id == PydanticObjectId(note_id)
    )
    
    if not note:
        return None
    
    # Verify note belongs to this affiliate
    if str(note.affiliate_id) != affiliate_id:
        return None  # Unauthorized
    
    # Delete the note
    await note.delete()
    return True

# ==================== Top Affiliates Analytics ====================

async def get_top_affiliates_by_referrals(limit: int = 10):
    """Get top affiliates ranked by referral count"""
    from beanie import PydanticObjectId
    
    # Get all affiliates
    affiliates = await models.Affiliate.find().to_list()
    
    # For each affiliate, get referral count
    affiliate_stats = []
    for affiliate in affiliates:
        count = await models.Referral.find(
            models.Referral.affiliate_id == affiliate.id
        ).count()
        
        # Get user email
        user = await models.User.find_one(
            models.User.id == affiliate.user_id
        )
        
        if user and user.is_active:
            affiliate_stats.append({
                "affiliate": affiliate,
                "user": user,
                "count": count
            })
    
    # Sort by count descending
    affiliate_stats.sort(key=lambda x: x["count"], reverse=True)
    
    # Take top N
    top_affiliates = affiliate_stats[:limit]
    
    # Build response
    result = []
    for stat in top_affiliates:
        result.append(schemas.TopAffiliateResponse(
            id=str(stat["affiliate"].id),
            name=stat["affiliate"].name,
            email=stat["user"].email,
            location=stat["affiliate"].location,
            language=stat["affiliate"].language,
            unique_link=f"{settings.BASE_URL}/ref/{stat['affiliate'].unique_link}",
            referral_count=stat["count"],
            created_at=stat["affiliate"].created_at
        ))
    
    return result

# ==================== Support Ticket CRUD Functions ====================

async def create_support_ticket(
    ticket_type: models.TicketType,
    creator_id: PydanticObjectId,
    creator_email: str,
    creator_name: str,
    subject: str,
    message: str,
    priority: models.TicketPriority,
    image_url: Optional[str] = None,
    assigned_to_id: Optional[PydanticObjectId] = None
):
    """Create a new support ticket"""
    ticket = models.SupportTicket(
        ticket_type=ticket_type,
        creator_id=creator_id,
        creator_email=creator_email,
        creator_name=creator_name,
        assigned_to_id=assigned_to_id,
        subject=subject,
        message=message,
        priority=priority,
        image_url=image_url
    )
    await ticket.insert()
    return ticket

async def get_ticket_by_id(ticket_id: str) -> Optional[models.SupportTicket]:
    """Get a ticket by ID"""
    try:
        ticket = await models.SupportTicket.get(PydanticObjectId(ticket_id))
        return ticket
    except Exception:
        return None

async def get_tickets_for_admin(
    status: Optional[models.TicketStatus] = None,
    priority: Optional[models.TicketPriority] = None,
    page: int = 1,
    page_size: int = 20
):
    """Get all affiliate->admin tickets (for admin view)"""
    if page < 1:
        page = 1
    if page_size < 1:
        page_size = 1
    if page_size > 100:
        page_size = 100
    skip = (page - 1) * page_size
    
    query = models.SupportTicket.find(
        models.SupportTicket.ticket_type == models.TicketType.AFFILIATE_TO_ADMIN
    )
    
    if status:
        query = query.find(models.SupportTicket.status == status)
    if priority:
        query = query.find(models.SupportTicket.priority == priority)
    
    # Sort by priority (high->medium->average) then by created_at (newest first)
    tickets = await query.sort([
        ("status", 1),  # Open first
        ("-priority", 1),  # High priority first
        ("-created_at", 1)  # Newest first
    ]).skip(skip).limit(page_size).to_list()
    
    # Get reply count for each ticket
    result = []
    for ticket in tickets:
        reply_count = await models.TicketReply.find(
            models.TicketReply.ticket_id == ticket.id
        ).count()
        
        ticket_dict = ticket.dict()
        ticket_dict['id'] = str(ticket.id)
        ticket_dict['creator_id'] = str(ticket.creator_id)
        ticket_dict['assigned_to_id'] = str(ticket.assigned_to_id) if ticket.assigned_to_id else None
        ticket_dict['reply_count'] = reply_count
        result.append(ticket_dict)
    
    return result

async def get_tickets_by_affiliate(
    affiliate_id: str,
    status: Optional[models.TicketStatus] = None,
    page: int = 1,
    page_size: int = 20
):
    """Get tickets created by a specific affiliate (to admin)"""
    if page < 1:
        page = 1
    if page_size < 1:
        page_size = 1
    if page_size > 100:
        page_size = 100
    skip = (page - 1) * page_size
    
    query = models.SupportTicket.find(
        models.SupportTicket.ticket_type == models.TicketType.AFFILIATE_TO_ADMIN,
        models.SupportTicket.creator_id == PydanticObjectId(affiliate_id)
    )
    
    if status:
        query = query.find(models.SupportTicket.status == status)
    
    tickets = await query.sort("-created_at").skip(skip).limit(page_size).to_list()
    
    # Get reply count for each ticket
    result = []
    for ticket in tickets:
        reply_count = await models.TicketReply.find(
            models.TicketReply.ticket_id == ticket.id
        ).count()
        
        ticket_dict = ticket.dict()
        ticket_dict['id'] = str(ticket.id)
        ticket_dict['creator_id'] = str(ticket.creator_id)
        ticket_dict['assigned_to_id'] = str(ticket.assigned_to_id) if ticket.assigned_to_id else None
        ticket_dict['reply_count'] = reply_count
        result.append(ticket_dict)
    
    return result

async def get_member_tickets_for_affiliate(
    affiliate_id: str,
    status: Optional[models.TicketStatus] = None,
    priority: Optional[models.TicketPriority] = None,
    page: int = 1,
    page_size: int = 20
):
    """Get tickets from members assigned to a specific affiliate"""
    if page < 1:
        page = 1
    if page_size < 1:
        page_size = 1
    if page_size > 100:
        page_size = 100
    skip = (page - 1) * page_size
    
    query = models.SupportTicket.find(
        models.SupportTicket.ticket_type == models.TicketType.MEMBER_TO_AFFILIATE,
        models.SupportTicket.assigned_to_id == PydanticObjectId(affiliate_id)
    )
    
    if status:
        query = query.find(models.SupportTicket.status == status)
    if priority:
        query = query.find(models.SupportTicket.priority == priority)
    
    tickets = await query.sort([
        ("status", 1),
        ("-priority", 1),
        ("-created_at", 1)
    ]).skip(skip).limit(page_size).to_list()
    
    # Get reply count for each ticket
    result = []
    for ticket in tickets:
        reply_count = await models.TicketReply.find(
            models.TicketReply.ticket_id == ticket.id
        ).count()
        
        ticket_dict = ticket.dict()
        ticket_dict['id'] = str(ticket.id)
        ticket_dict['creator_id'] = str(ticket.creator_id)
        ticket_dict['assigned_to_id'] = str(ticket.assigned_to_id) if ticket.assigned_to_id else None
        ticket_dict['reply_count'] = reply_count
        result.append(ticket_dict)
    
    return result

async def get_tickets_by_member(
    member_id: str,
    status: Optional[models.TicketStatus] = None,
    page: int = 1,
    page_size: int = 20
):
    """Get tickets created by a specific member (to their affiliate)"""
    if page < 1:
        page = 1
    if page_size < 1:
        page_size = 1
    if page_size > 100:
        page_size = 100
    skip = (page - 1) * page_size
    
    query = models.SupportTicket.find(
        models.SupportTicket.ticket_type == models.TicketType.MEMBER_TO_AFFILIATE,
        models.SupportTicket.creator_id == PydanticObjectId(member_id)
    )
    
    if status:
        query = query.find(models.SupportTicket.status == status)
    
    tickets = await query.sort("-created_at").skip(skip).limit(page_size).to_list()
    
    # Get reply count for each ticket
    result = []
    for ticket in tickets:
        reply_count = await models.TicketReply.find(
            models.TicketReply.ticket_id == ticket.id
        ).count()
        
        ticket_dict = ticket.dict()
        ticket_dict['id'] = str(ticket.id)
        ticket_dict['creator_id'] = str(ticket.creator_id)
        ticket_dict['assigned_to_id'] = str(ticket.assigned_to_id) if ticket.assigned_to_id else None
        ticket_dict['reply_count'] = reply_count
        result.append(ticket_dict)
    
    return result

async def add_ticket_reply(
    ticket_id: str,
    sender_id: PydanticObjectId,
    sender_email: str,
    sender_name: str,
    sender_type: str,
    message: str,
    image_url: Optional[str] = None
):
    """Add a reply to a ticket"""
    # Get the ticket
    ticket = await get_ticket_by_id(ticket_id)
    if not ticket:
        return None
    
    # Create reply
    reply = models.TicketReply(
        ticket_id=PydanticObjectId(ticket_id),
        sender_id=sender_id,
        sender_email=sender_email,
        sender_name=sender_name,
        sender_type=sender_type,
        message=message,
        image_url=image_url
    )
    await reply.insert()
    
    # Update ticket status to ONGOING if it's OPEN and this is not the creator replying
    if ticket.status == models.TicketStatus.OPEN and str(sender_id) != str(ticket.creator_id):
        ticket.status = models.TicketStatus.ONGOING
    
    # Update last_reply_at
    ticket.last_reply_at = datetime.utcnow()
    ticket.updated_at = datetime.utcnow()
    await ticket.save()
    
    return reply

async def get_ticket_with_replies(ticket_id: str):
    """Get a ticket with all its replies"""
    ticket = await get_ticket_by_id(ticket_id)
    if not ticket:
        return None
    
    # Get all replies
    replies = await models.TicketReply.find(
        models.TicketReply.ticket_id == PydanticObjectId(ticket_id)
    ).sort("created_at").to_list()
    
    # Convert to response format
    ticket_dict = ticket.dict()
    ticket_dict['id'] = str(ticket.id)
    ticket_dict['creator_id'] = str(ticket.creator_id)
    ticket_dict['assigned_to_id'] = str(ticket.assigned_to_id) if ticket.assigned_to_id else None
    
    replies_list = []
    for reply in replies:
        reply_dict = reply.dict()
        reply_dict['id'] = str(reply.id)
        reply_dict['ticket_id'] = str(reply.ticket_id)
        reply_dict['sender_id'] = str(reply.sender_id)
        replies_list.append(reply_dict)
    
    ticket_dict['replies'] = replies_list
    
    return ticket_dict

async def update_ticket_status_priority(
    ticket_id: str,
    status: Optional[models.TicketStatus] = None,
    priority: Optional[models.TicketPriority] = None
):
    """Update ticket status and/or priority"""
    ticket = await get_ticket_by_id(ticket_id)
    if not ticket:
        return None
    
    if status:
        ticket.status = status
    if priority:
        ticket.priority = priority
    
    ticket.updated_at = datetime.utcnow()
    await ticket.save()
    
    return ticket

async def get_ticket_stats_for_admin():
    """Get ticket statistics for admin dashboard"""
    # Count tickets by status
    total = await models.SupportTicket.find(
        models.SupportTicket.ticket_type == models.TicketType.AFFILIATE_TO_ADMIN
    ).count()
    
    open_count = await models.SupportTicket.find(
        models.SupportTicket.ticket_type == models.TicketType.AFFILIATE_TO_ADMIN,
        models.SupportTicket.status == models.TicketStatus.OPEN
    ).count()
    
    ongoing_count = await models.SupportTicket.find(
        models.SupportTicket.ticket_type == models.TicketType.AFFILIATE_TO_ADMIN,
        models.SupportTicket.status == models.TicketStatus.ONGOING
    ).count()
    
    closed_count = await models.SupportTicket.find(
        models.SupportTicket.ticket_type == models.TicketType.AFFILIATE_TO_ADMIN,
        models.SupportTicket.status == models.TicketStatus.CLOSED
    ).count()
    
    # Count by priority
    high_count = await models.SupportTicket.find(
        models.SupportTicket.ticket_type == models.TicketType.AFFILIATE_TO_ADMIN,
        models.SupportTicket.priority == models.TicketPriority.HIGH,
        models.SupportTicket.status != models.TicketStatus.CLOSED
    ).count()
    
    medium_count = await models.SupportTicket.find(
        models.SupportTicket.ticket_type == models.TicketType.AFFILIATE_TO_ADMIN,
        models.SupportTicket.priority == models.TicketPriority.MEDIUM,
        models.SupportTicket.status != models.TicketStatus.CLOSED
    ).count()
    
    average_count = await models.SupportTicket.find(
        models.SupportTicket.ticket_type == models.TicketType.AFFILIATE_TO_ADMIN,
        models.SupportTicket.priority == models.TicketPriority.AVERAGE,
        models.SupportTicket.status != models.TicketStatus.CLOSED
    ).count()
    
    # Count tickets created today
    from datetime import datetime, timedelta
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    tickets_today = await models.SupportTicket.find(
        models.SupportTicket.ticket_type == models.TicketType.AFFILIATE_TO_ADMIN,
        models.SupportTicket.created_at >= today_start
    ).count()
    
    return {
        "total_tickets": total,
        "open": open_count,
        "ongoing": ongoing_count,
        "closed": closed_count,
        "by_priority": {
            "high": high_count,
            "medium": medium_count,
            "average": average_count
        },
        "tickets_today": tickets_today
    }

async def get_ticket_stats_for_affiliate(affiliate_id: str):
    """Get ticket statistics for affiliate"""
    # Tickets TO admin
    my_tickets_total = await models.SupportTicket.find(
        models.SupportTicket.ticket_type == models.TicketType.AFFILIATE_TO_ADMIN,
        models.SupportTicket.creator_id == PydanticObjectId(affiliate_id)
    ).count()
    
    my_open = await models.SupportTicket.find(
        models.SupportTicket.ticket_type == models.TicketType.AFFILIATE_TO_ADMIN,
        models.SupportTicket.creator_id == PydanticObjectId(affiliate_id),
        models.SupportTicket.status == models.TicketStatus.OPEN
    ).count()
    
    my_ongoing = await models.SupportTicket.find(
        models.SupportTicket.ticket_type == models.TicketType.AFFILIATE_TO_ADMIN,
        models.SupportTicket.creator_id == PydanticObjectId(affiliate_id),
        models.SupportTicket.status == models.TicketStatus.ONGOING
    ).count()
    
    my_closed = await models.SupportTicket.find(
        models.SupportTicket.ticket_type == models.TicketType.AFFILIATE_TO_ADMIN,
        models.SupportTicket.creator_id == PydanticObjectId(affiliate_id),
        models.SupportTicket.status == models.TicketStatus.CLOSED
    ).count()
    
    # Tickets FROM members
    member_tickets_total = await models.SupportTicket.find(
        models.SupportTicket.ticket_type == models.TicketType.MEMBER_TO_AFFILIATE,
        models.SupportTicket.assigned_to_id == PydanticObjectId(affiliate_id)
    ).count()
    
    member_open = await models.SupportTicket.find(
        models.SupportTicket.ticket_type == models.TicketType.MEMBER_TO_AFFILIATE,
        models.SupportTicket.assigned_to_id == PydanticObjectId(affiliate_id),
        models.SupportTicket.status == models.TicketStatus.OPEN
    ).count()
    
    member_ongoing = await models.SupportTicket.find(
        models.SupportTicket.ticket_type == models.TicketType.MEMBER_TO_AFFILIATE,
        models.SupportTicket.assigned_to_id == PydanticObjectId(affiliate_id),
        models.SupportTicket.status == models.TicketStatus.ONGOING
    ).count()
    
    member_closed = await models.SupportTicket.find(
        models.SupportTicket.ticket_type == models.TicketType.MEMBER_TO_AFFILIATE,
        models.SupportTicket.assigned_to_id == PydanticObjectId(affiliate_id),
        models.SupportTicket.status == models.TicketStatus.CLOSED
    ).count()
    
    return {
        "my_tickets_to_admin": {
            "total": my_tickets_total,
            "open": my_open,
            "ongoing": my_ongoing,
            "closed": my_closed
        },
        "member_tickets": {
            "total": member_tickets_total,
            "open": member_open,
            "ongoing": member_ongoing,
            "closed": member_closed
        }
    }

# ==================== Affiliate Email Template CRUD Functions ====================

async def create_affiliate_email_template(affiliate_id: str, template_data: schemas.EmailTemplateCreate):
    """Create or update an affiliate's email template"""
    from beanie import PydanticObjectId
    
    # Check if template already exists for this affiliate
    existing_template = await models.AffiliateEmailTemplate.find_one(
        models.AffiliateEmailTemplate.affiliate_id == PydanticObjectId(affiliate_id)
    )
    
    if existing_template:
        # Update existing template
        existing_template.subject = template_data.subject
        existing_template.html_content = template_data.html_content
        existing_template.text_content = template_data.text_content
        existing_template.is_active = template_data.is_active
        existing_template.updated_at = datetime.utcnow()
        await existing_template.save()
        
        return schemas.EmailTemplateResponse(
            id=str(existing_template.id),
            affiliate_id=str(existing_template.affiliate_id),
            subject=existing_template.subject,
            html_content=existing_template.html_content,
            text_content=existing_template.text_content,
            is_active=existing_template.is_active,
            created_at=existing_template.created_at,
            updated_at=existing_template.updated_at
        )
    
    # Create new template
    template = models.AffiliateEmailTemplate(
        affiliate_id=PydanticObjectId(affiliate_id),
        subject=template_data.subject,
        html_content=template_data.html_content,
        text_content=template_data.text_content,
        is_active=template_data.is_active
    )
    await template.insert()
    
    return schemas.EmailTemplateResponse(
        id=str(template.id),
        affiliate_id=str(template.affiliate_id),
        subject=template.subject,
        html_content=template.html_content,
        text_content=template.text_content,
        is_active=template.is_active,
        created_at=template.created_at,
        updated_at=template.updated_at
    )

async def get_affiliate_email_template(affiliate_id: str):
    """Get an affiliate's email template"""
    from beanie import PydanticObjectId
    
    template = await models.AffiliateEmailTemplate.find_one(
        models.AffiliateEmailTemplate.affiliate_id == PydanticObjectId(affiliate_id)
    )
    
    if not template:
        return None
    
    return schemas.EmailTemplateResponse(
        id=str(template.id),
        affiliate_id=str(template.affiliate_id),
        subject=template.subject,
        html_content=template.html_content,
        text_content=template.text_content,
        is_active=template.is_active,
        created_at=template.created_at,
        updated_at=template.updated_at
    )

async def update_affiliate_email_template(affiliate_id: str, template_data: schemas.EmailTemplateUpdate):
    """Update an affiliate's email template"""
    from beanie import PydanticObjectId
    
    template = await models.AffiliateEmailTemplate.find_one(
        models.AffiliateEmailTemplate.affiliate_id == PydanticObjectId(affiliate_id)
    )
    
    if not template:
        return None
    
    # Update only provided fields
    update_dict = template_data.dict(exclude_unset=True)
    
    for field, value in update_dict.items():
        setattr(template, field, value)
    
    template.updated_at = datetime.utcnow()
    await template.save()
    
    return schemas.EmailTemplateResponse(
        id=str(template.id),
        affiliate_id=str(template.affiliate_id),
        subject=template.subject,
        html_content=template.html_content,
        text_content=template.text_content,
        is_active=template.is_active,
        created_at=template.created_at,
        updated_at=template.updated_at
    )

async def delete_affiliate_email_template(affiliate_id: str):
    """Delete an affiliate's email template"""
    from beanie import PydanticObjectId
    
    template = await models.AffiliateEmailTemplate.find_one(
        models.AffiliateEmailTemplate.affiliate_id == PydanticObjectId(affiliate_id)
    )
    
    if not template:
        return None
    
    await template.delete()
    return True

# ==================== Public Notes CRUD Functions ====================

async def create_public_note(admin_id: str, admin_email: str, note_data: schemas.PublicNoteCreate):
    """Create a new public note/announcement"""
    from beanie import PydanticObjectId
    
    note = models.PublicNote(
        title=note_data.title,
        content=note_data.content,
        author_id=PydanticObjectId(admin_id),
        author_email=admin_email,
        is_published=note_data.is_published,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    await note.insert()
    
    return schemas.PublicNoteResponse(
        id=str(note.id),
        title=note.title,
        content=note.content,
        author_id=str(note.author_id),
        author_email=note.author_email,
        is_published=note.is_published,
        created_at=note.created_at,
        updated_at=note.updated_at
    )

async def get_all_public_notes(page: int = 1, page_size: int = 20, include_unpublished: bool = False):
    """Get all public notes (paginated)"""
    if page < 1:
        page = 1
    if page_size < 1:
        page_size = 1
    if page_size > 100:
        page_size = 100
    skip = (page - 1) * page_size
    
    # Build query - only published notes for public, all for admin
    if include_unpublished:
        query = models.PublicNote.find()
    else:
        query = models.PublicNote.find(models.PublicNote.is_published == True)
    
    notes = await query.sort("-created_at").skip(skip).limit(page_size).to_list()
    
    result = []
    for note in notes:
        result.append(schemas.PublicNoteResponse(
            id=str(note.id),
            title=note.title,
            content=note.content,
            author_id=str(note.author_id),
            author_email=note.author_email,
            is_published=note.is_published,
            created_at=note.created_at,
            updated_at=note.updated_at
        ))
    return result

async def get_public_note_by_id(note_id: str):
    """Get a specific public note by ID"""
    from beanie import PydanticObjectId
    
    try:
        note = await models.PublicNote.find_one(
            models.PublicNote.id == PydanticObjectId(note_id)
        )
    except Exception:
        return None
    
    if not note:
        return None
    
    return schemas.PublicNoteResponse(
        id=str(note.id),
        title=note.title,
        content=note.content,
        author_id=str(note.author_id),
        author_email=note.author_email,
        is_published=note.is_published,
        created_at=note.created_at,
        updated_at=note.updated_at
    )

async def update_public_note(note_id: str, update_data: schemas.PublicNoteUpdate):
    """Update a public note"""
    from beanie import PydanticObjectId
    
    try:
        note = await models.PublicNote.find_one(
            models.PublicNote.id == PydanticObjectId(note_id)
        )
    except Exception:
        return None
    
    if not note:
        return None
    
    # Update only provided fields
    update_dict = update_data.dict(exclude_unset=True)
    
    for field, value in update_dict.items():
        setattr(note, field, value)
    
    note.updated_at = datetime.utcnow()
    await note.save()
    
    return schemas.PublicNoteResponse(
        id=str(note.id),
        title=note.title,
        content=note.content,
        author_id=str(note.author_id),
        author_email=note.author_email,
        is_published=note.is_published,
        created_at=note.created_at,
        updated_at=note.updated_at
    )

async def delete_public_note(note_id: str):
    """Delete a public note"""
    from beanie import PydanticObjectId
    
    try:
        note = await models.PublicNote.find_one(
            models.PublicNote.id == PydanticObjectId(note_id)
        )
    except Exception:
        return None
    
    if not note:
        return None
    
    await note.delete()
    return True

# ==================== Tutorial Video CRUD Functions ====================

async def create_tutorial_video(
    admin_id: str,
    admin_email: str,
    title: str,
    description: str,
    video_data: dict  # From Cloudinary upload
):
    """Create a new tutorial video"""
    from beanie import PydanticObjectId
    
    video = models.TutorialVideo(
        title=title,
        description=description,
        video_url=video_data['video_url'],
        cloudinary_public_id=video_data['public_id'],
        thumbnail_url=video_data.get('thumbnail_url'),
        duration=video_data.get('duration'),
        video_format=video_data.get('format', 'mp4'),
        file_size=video_data.get('size'),
        author_id=PydanticObjectId(admin_id),
        author_email=admin_email,
        is_published=True,
        view_count=0,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    await video.insert()
    
    return schemas.TutorialVideoResponse(
        id=str(video.id),
        title=video.title,
        description=video.description,
        video_url=video.video_url,
        cloudinary_public_id=video.cloudinary_public_id,
        thumbnail_url=video.thumbnail_url,
        duration=video.duration,
        video_format=video.video_format,
        file_size=video.file_size,
        author_id=str(video.author_id),
        author_email=video.author_email,
        is_published=video.is_published,
        view_count=video.view_count,
        created_at=video.created_at,
        updated_at=video.updated_at
    )

async def get_all_tutorial_videos(page: int = 1, page_size: int = 20, include_unpublished: bool = False):
    """Get all tutorial videos (paginated)"""
    if page < 1:
        page = 1
    if page_size < 1:
        page_size = 1
    if page_size > 100:
        page_size = 100
    skip = (page - 1) * page_size
    
    # Build query - only published videos for public, all for admin
    if include_unpublished:
        query = models.TutorialVideo.find()
    else:
        query = models.TutorialVideo.find(models.TutorialVideo.is_published == True)
    
    videos = await query.sort("-created_at").skip(skip).limit(page_size).to_list()
    
    result = []
    for video in videos:
        result.append(schemas.TutorialVideoResponse(
            id=str(video.id),
            title=video.title,
            description=video.description,
            video_url=video.video_url,
            cloudinary_public_id=video.cloudinary_public_id,
            thumbnail_url=video.thumbnail_url,
            duration=video.duration,
            video_format=video.video_format,
            file_size=video.file_size,
            author_id=str(video.author_id),
            author_email=video.author_email,
            is_published=video.is_published,
            view_count=video.view_count,
            created_at=video.created_at,
            updated_at=video.updated_at
        ))
    return result

async def get_tutorial_video_by_id(video_id: str, increment_view: bool = False):
    """Get a specific tutorial video by ID"""
    from beanie import PydanticObjectId
    
    try:
        video = await models.TutorialVideo.find_one(
            models.TutorialVideo.id == PydanticObjectId(video_id)
        )
    except Exception:
        return None
    
    if not video:
        return None
    
    # Increment view count if requested (for public viewing)
    if increment_view:
        video.view_count += 1
        await video.save()
    
    return schemas.TutorialVideoResponse(
        id=str(video.id),
        title=video.title,
        description=video.description,
        video_url=video.video_url,
        cloudinary_public_id=video.cloudinary_public_id,
        thumbnail_url=video.thumbnail_url,
        duration=video.duration,
        video_format=video.video_format,
        file_size=video.file_size,
        author_id=str(video.author_id),
        author_email=video.author_email,
        is_published=video.is_published,
        view_count=video.view_count,
        created_at=video.created_at,
        updated_at=video.updated_at
    )

async def update_tutorial_video(video_id: str, update_data: schemas.TutorialVideoUpdate):
    """Update a tutorial video metadata"""
    from beanie import PydanticObjectId
    
    try:
        video = await models.TutorialVideo.find_one(
            models.TutorialVideo.id == PydanticObjectId(video_id)
        )
    except Exception:
        return None
    
    if not video:
        return None
    
    # Update only provided fields
    update_dict = update_data.dict(exclude_unset=True)
    
    for field, value in update_dict.items():
        setattr(video, field, value)
    
    video.updated_at = datetime.utcnow()
    await video.save()
    
    return schemas.TutorialVideoResponse(
        id=str(video.id),
        title=video.title,
        description=video.description,
        video_url=video.video_url,
        cloudinary_public_id=video.cloudinary_public_id,
        thumbnail_url=video.thumbnail_url,
        duration=video.duration,
        video_format=video.video_format,
        file_size=video.file_size,
        author_id=str(video.author_id),
        author_email=video.author_email,
        is_published=video.is_published,
        view_count=video.view_count,
        created_at=video.created_at,
        updated_at=video.updated_at
    )

async def delete_tutorial_video(video_id: str):
    """Delete a tutorial video and remove from Cloudinary"""
    from beanie import PydanticObjectId
    import cloudinary_utils
    
    try:
        video = await models.TutorialVideo.find_one(
            models.TutorialVideo.id == PydanticObjectId(video_id)
        )
    except Exception:
        return None
    
    if not video:
        return None
    
    # Delete video from Cloudinary
    try:
        await cloudinary_utils.delete_cloudinary_video(video.cloudinary_public_id)
        print(f"Deleted video from Cloudinary: {video.cloudinary_public_id}")
    except Exception as e:
        print(f"Warning: Failed to delete video from Cloudinary: {e}")
        # Continue with database deletion even if Cloudinary deletion fails
    
    # Delete from database
    await video.delete()
    return True

