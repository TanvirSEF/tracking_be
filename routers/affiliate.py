from fastapi import APIRouter, HTTPException, status, Header, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import RedirectResponse
from typing import List
import urllib.parse

import models
import schemas
import crud
import auth_utils as auth
from config import settings

router = APIRouter()
security = HTTPBearer()


@router.post("/register/{link_code}", response_model=schemas.AffiliateRequestResponse)
async def register_affiliate(
    link_code: str,
    request: schemas.AffiliateRequestCreate
):
    """
    Register a new affiliate using the admin registration link.
    The link_code must match the fixed admin registration link.
    """
    # Verify registration link
    if not await crud.verify_registration_link(link_code):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid registration link. Please contact admin for the correct link."
        )
    
    # Create affiliate request
    affiliate_request = await crud.create_affiliate_request(request)
    if not affiliate_request:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered or pending approval. Please check your email for verification or contact admin."
        )
    
    return affiliate_request


@router.get("/ref/{unique_link}")
async def redirect_to_frontend_registration(unique_link: str):
    """
    Redirect users to frontend registration form with affiliate info.
    This endpoint handles the redirect from affiliate links to the frontend.
    """
    # Find the affiliate by unique link
    affiliate = await models.Affiliate.find_one(
        models.Affiliate.unique_link == unique_link
    )
    
    if not affiliate:
        # If affiliate not found, redirect to frontend without affiliate info
        frontend_url = f"{settings.FRONTEND_URL}/register"
        return RedirectResponse(url=frontend_url, status_code=302)
    
    # Get the affiliate's user info to get their email/name
    user = await models.User.find_one(models.User.id == affiliate.user_id)
    
    if not user or not user.is_active:
        # If user not found or inactive, redirect without affiliate info
        frontend_url = f"{settings.FRONTEND_URL}/register"
        return RedirectResponse(url=frontend_url, status_code=302)
    
    # Create frontend URL with affiliate info as query parameters
    frontend_base_url = f"{settings.FRONTEND_URL}/register"
    
    # URL encode the affiliate name to handle special characters
    affiliate_name_encoded = urllib.parse.quote(affiliate.name)
    affiliate_email_encoded = urllib.parse.quote(user.email)
    
    # Add query parameters
    frontend_url = f"{frontend_base_url}?invited_by={affiliate_name_encoded}&affiliate_email={affiliate_email_encoded}&affiliate_link={unique_link}"
    
    return RedirectResponse(url=frontend_url, status_code=302)


@router.get("/affiliate/profile", response_model=schemas.AffiliateResponse)
async def get_affiliate_profile(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get current affiliate's profile"""
    current_user = await auth.get_current_user(credentials.credentials)
    
    if current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin users don't have affiliate profiles"
        )
    
    affiliate = await crud.get_affiliate_by_user(current_user.id)
    if not affiliate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Affiliate profile not found"
        )
    
    return schemas.AffiliateResponse(
        id=str(affiliate.id),
        name=affiliate.name,
        email=current_user.email,
        location=affiliate.location,
        language=affiliate.language,
        puprime_referral_code=affiliate.puprime_referral_code,
        puprime_link=affiliate.puprime_link,
        unique_link=f"{settings.BASE_URL}/ref/{affiliate.unique_link}",
        created_at=affiliate.created_at
    )


@router.put("/affiliate/profile", response_model=schemas.AffiliateResponse)
async def update_affiliate_profile(
    profile_data: schemas.AffiliateProfileUpdate,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Update current affiliate's profile information"""
    current_user = await auth.get_current_user(credentials.credentials)
    
    if current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin users don't have affiliate profiles"
        )
    
    # Update the affiliate profile
    affiliate = await crud.update_affiliate_profile(current_user.id, profile_data)
    if not affiliate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Affiliate profile not found"
        )
    
    return schemas.AffiliateResponse(
        id=str(affiliate.id),
        name=affiliate.name,
        email=current_user.email,
        location=affiliate.location,
        language=affiliate.language,
        puprime_referral_code=affiliate.puprime_referral_code,
        puprime_link=affiliate.puprime_link,
        unique_link=f"{settings.BASE_URL}/ref/{affiliate.unique_link}",
        created_at=affiliate.created_at
    )


@router.post("/ref/{unique_link}/register", response_model=schemas.ReferralResponse)
async def register_through_affiliate_link(
    unique_link: str,
    registration_data: schemas.ReferralRegistrationRequest
):
    """Register a new member through an affiliate's unique link"""
    # Verify the affiliate link exists
    affiliate = await models.Affiliate.find_one(
        models.Affiliate.unique_link == unique_link
    )
    
    if not affiliate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid affiliate link"
        )
    
    # Create the referral registration
    referral = await crud.create_referral_registration(unique_link, registration_data)
    
    if not referral:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered or invalid affiliate link"
        )
    
    return referral


@router.get("/affiliate/referrals", response_model=List[schemas.ReferralResponse])
async def get_affiliate_referrals(
    page: int = 1,
    page_size: int = 20,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Get all referrals for the current affiliate"""
    current_user = await auth.get_current_user(credentials.credentials)
    
    if current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin users don't have affiliate referrals"
        )
    
    # Get the affiliate profile
    affiliate = await crud.get_affiliate_by_user(current_user.id)
    if not affiliate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Affiliate profile not found"
        )
    
    # Get referrals for this affiliate
    referrals = await crud.get_referrals_by_affiliate(str(affiliate.id), page=page, page_size=page_size)
    return referrals


@router.get("/affiliate/referrals/count")
async def get_affiliate_referral_count(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Get total count of referrals for the current affiliate"""
    current_user = await auth.get_current_user(credentials.credentials)
    
    if current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin users don't have affiliate referrals"
        )
    
    # Get the affiliate profile
    affiliate = await crud.get_affiliate_by_user(current_user.id)
    if not affiliate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Affiliate profile not found"
        )
    
    # Get referral count for this affiliate
    count = await crud.get_referral_count_by_affiliate(str(affiliate.id))
    return {"total_referrals": count}


@router.delete("/affiliate/profile")
async def delete_affiliate_profile(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Delete current affiliate's profile and associated user account"""
    current_user = await auth.get_current_user(credentials.credentials)
    
    if current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin users don't have affiliate profiles"
        )
    
    # Get the affiliate profile
    affiliate = await crud.get_affiliate_by_user(current_user.id)
    if not affiliate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Affiliate profile not found"
        )
    
    # Delete all referrals associated with this affiliate
    referrals_result = await models.Referral.find(
        models.Referral.affiliate_id == affiliate.id
    ).delete()
    
    # Delete the affiliate request associated with this user's email
    affiliate_request_result = await models.AffiliateRequest.find(
        models.AffiliateRequest.email == current_user.email
    ).delete()
    
    # Delete the affiliate profile
    await affiliate.delete()
    
    # Delete the user account
    await current_user.delete()
    
    return {
        "message": "Affiliate profile and account deleted successfully",
        "deleted_affiliate_id": str(affiliate.id),
        "deleted_user_id": str(current_user.id),
        "deleted_referrals_count": referrals_result.deleted_count,
        "deleted_affiliate_requests_count": affiliate_request_result.deleted_count
    }


@router.delete("/affiliate/referrals/{referral_id}")
async def delete_affiliate_referral(
    referral_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Delete a specific referral user"""
    current_user = await auth.get_current_user(credentials.credentials)
    
    if current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin users don't have affiliate referrals"
        )
    
    # Get the affiliate profile
    affiliate = await crud.get_affiliate_by_user(current_user.id)
    if not affiliate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Affiliate profile not found"
        )
    
    # Find the referral
    from beanie import PydanticObjectId
    referral = await models.Referral.find_one(
        models.Referral.id == PydanticObjectId(referral_id)
    )
    
    if not referral:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Referral not found"
        )
    
    # Verify the referral belongs to this affiliate
    if str(referral.affiliate_id) != str(affiliate.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete your own referrals"
        )
    
    # Delete the referral
    await referral.delete()
    
    return {
        "message": "Referral deleted successfully",
        "deleted_referral_id": str(referral.id),
        "referral_email": referral.email
    }


# ==================== Affiliate Notes Endpoints ====================

@router.post("/affiliate/referrals/{referral_id}/notes", response_model=schemas.NoteResponse)
async def create_note(
    referral_id: str,
    note_data: schemas.NoteCreate,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Create a note for a specific referral"""
    current_user = await auth.get_current_user(credentials.credentials)
    
    if current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin users cannot create affiliate notes"
        )
    
    # Get the affiliate profile
    affiliate = await crud.get_affiliate_by_user(current_user.id)
    if not affiliate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Affiliate profile not found"
        )
    
    # Create the note
    note = await crud.create_affiliate_note(str(affiliate.id), referral_id, note_data)
    
    if not note:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Referral not found or doesn't belong to this affiliate"
        )
    
    return note


@router.get("/affiliate/referrals/{referral_id}/notes", response_model=List[schemas.NoteResponse])
async def get_referral_notes(
    referral_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Get all notes for a specific referral"""
    current_user = await auth.get_current_user(credentials.credentials)
    
    if current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin users cannot access affiliate notes"
        )
    
    # Get the affiliate profile
    affiliate = await crud.get_affiliate_by_user(current_user.id)
    if not affiliate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Affiliate profile not found"
        )
    
    # Get notes
    notes = await crud.get_notes_by_referral(str(affiliate.id), referral_id)
    
    if notes is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Referral not found or doesn't belong to this affiliate"
        )
    
    return notes


@router.get("/affiliate/notes", response_model=List[schemas.NoteResponse])
async def get_all_notes(
    page: int = 1,
    page_size: int = 50,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Get all notes created by the current affiliate"""
    current_user = await auth.get_current_user(credentials.credentials)
    
    if current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin users cannot access affiliate notes"
        )
    
    # Get the affiliate profile
    affiliate = await crud.get_affiliate_by_user(current_user.id)
    if not affiliate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Affiliate profile not found"
        )
    
    # Get all notes
    notes = await crud.get_all_notes_by_affiliate(str(affiliate.id), page=page, page_size=page_size)
    return notes


@router.put("/affiliate/notes/{note_id}", response_model=schemas.NoteResponse)
async def update_note(
    note_id: str,
    note_data: schemas.NoteUpdate,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Update an existing note"""
    current_user = await auth.get_current_user(credentials.credentials)
    
    if current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin users cannot update affiliate notes"
        )
    
    # Get the affiliate profile
    affiliate = await crud.get_affiliate_by_user(current_user.id)
    if not affiliate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Affiliate profile not found"
        )
    
    # Update the note
    note = await crud.update_affiliate_note(note_id, str(affiliate.id), note_data)
    
    if not note:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Note not found or doesn't belong to this affiliate"
        )
    
    return note


@router.delete("/affiliate/notes/{note_id}")
async def delete_note(
    note_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Delete a note"""
    current_user = await auth.get_current_user(credentials.credentials)
    
    if current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin users cannot delete affiliate notes"
        )
    
    # Get the affiliate profile
    affiliate = await crud.get_affiliate_by_user(current_user.id)
    if not affiliate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Affiliate profile not found"
        )
    
    # Delete the note
    result = await crud.delete_affiliate_note(note_id, str(affiliate.id))
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Note not found or doesn't belong to this affiliate"
        )
    
    return {
        "message": "Note deleted successfully",
        "note_id": note_id
    }


@router.get("/affiliate/status")
async def get_affiliate_status(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get affiliate registration status and workflow progress"""
    current_user = await auth.get_current_user(credentials.credentials)
    
    if current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin users don't have affiliate status"
        )
    
    # Check if user has affiliate profile
    affiliate = await crud.get_affiliate_by_user(current_user.id)
    
    if affiliate:
        # User is approved affiliate
        referrals_count = await crud.get_referral_count_by_affiliate(str(affiliate.id))
        return {
            "status": "approved",
            "message": "Your affiliate account is active",
            "affiliate_id": str(affiliate.id),
            "unique_link": f"{settings.BASE_URL}/ref/{affiliate.unique_link}",
            "total_referrals": referrals_count,
            "can_login": True
        }
    else:
        # Check if user has pending request
        request = await models.AffiliateRequest.find_one(
            models.AffiliateRequest.email == current_user.email
        )
        
        if request:
            return {
                "status": request.status,
                "message": f"Your request is {request.status}",
                "is_email_verified": request.is_email_verified,
                "created_at": request.created_at,
                "reviewed_at": request.reviewed_at,
                "can_login": request.status == "approved"
            }
        else:
            return {
                "status": "not_registered",
                "message": "You need to register as an affiliate first",
                "can_login": False
            }


@router.post("/affiliate/send-email", response_model=schemas.CustomEmailResponse)
async def send_custom_email_to_referral(
    email_data: schemas.CustomEmailRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """
    Send custom email to a referral
    
    This endpoint allows affiliates to send customized emails to their referrals.
    You can use HTML in the message field for rich formatting.
    """
    from datetime import datetime
    from beanie import PydanticObjectId
    from email_service import email_service
    
    current_user = await auth.get_current_user(credentials.credentials)
    
    if current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin users cannot send emails to referrals"
        )
    
    # Get the affiliate profile
    affiliate = await crud.get_affiliate_by_user(current_user.id)
    if not affiliate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Affiliate profile not found"
        )
    
    # Find the referral
    try:
        referral = await models.Referral.find_one(
            models.Referral.id == PydanticObjectId(email_data.referral_id)
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid referral ID format"
        )
    
    if not referral:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Referral not found"
        )
    
    # Verify the referral belongs to this affiliate
    if str(referral.affiliate_id) != str(affiliate.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only send emails to your own referrals"
        )
    
    # Send the custom email
    email_sent = await email_service.send_custom_email(
        to_email=referral.email,
        subject=email_data.subject,
        message=email_data.message,
        recipient_name=referral.full_name
    )
    
    if not email_sent:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send email. Please check email service configuration."
        )
    
    return schemas.CustomEmailResponse(
        message="Email sent successfully",
        referral_email=referral.email,
        referral_name=referral.full_name,
        sent_at=datetime.utcnow()
    )





