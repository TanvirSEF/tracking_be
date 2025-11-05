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
            is_email_verified=True  # Auto-verify emails (OTP verification removed)
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
        is_email_verified=True  # Auto-verify emails (OTP verification removed)
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
    
    # Create user account (emails are auto-verified, OTP verification removed)
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
    
    # Send welcome email after referral registration
    try:
        await send_welcome_email(registration_data.email, "referral", registration_data.full_name)
    except Exception as e:
        print(f"Warning: Failed to send welcome email to {registration_data.email}: {e}")
    
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