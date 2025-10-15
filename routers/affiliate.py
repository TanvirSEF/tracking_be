from fastapi import APIRouter, Depends, HTTPException, status
from typing import List

import models
import schemas
import crud
import auth_utils as auth
from config import settings

router = APIRouter()


@router.post("/register/{link_code}", response_model=schemas.AffiliateRequestResponse)
async def register_affiliate(
    link_code: str,
    request: schemas.AffiliateRequestCreate
):
    """
    Register a new affiliate using the admin registration link.
    The link_code must match the fixed admin registration link.
    Email must be verified before registration.
    """
    # Verify registration link
    if not await crud.verify_registration_link(link_code):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid registration link. Please contact admin for the correct link."
        )
    
    # Check if email is verified
    if not await crud.is_email_verified(request.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email must be verified before registration. Please verify your email first."
        )
    
    # Create affiliate request
    affiliate_request = await crud.create_affiliate_request(request)
    if not affiliate_request:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered or pending approval"
        )
    
    return affiliate_request


@router.get("/affiliate/profile", response_model=schemas.AffiliateResponse)
async def get_affiliate_profile(
    current_user: models.User = Depends(auth.get_current_user)
):
    """Get current affiliate's profile"""
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
        unique_link=f"{settings.BASE_URL}/ref/{affiliate.unique_link}",
        created_at=affiliate.created_at
    )


@router.get("/ref/{unique_link}")
async def track_affiliate_link(unique_link: str):
    """Track clicks on affiliate links - this is the individual affiliate's unique link"""
    affiliate = await models.Affiliate.find_one(
        models.Affiliate.unique_link == unique_link
    )
    
    if not affiliate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid affiliate link"
        )
    
    # Here you can add tracking logic, redirect to landing page, etc.
    # For now, just return affiliate information
    return {
        "message": "Valid affiliate link",
        "affiliate_name": affiliate.name,
        "affiliate_id": str(affiliate.id),
        # Add redirect URL or tracking logic here
        "redirect_to": "https://your-landing-page.com"
    }


@router.get("/registration-info")
def get_registration_info():
    """Get information about the registration process"""
    return {
        "message": "To register as an affiliate, you need the admin registration link and email verification",
        "registration_url_format": "{base_url}/register/{admin_link}",
        "required_fields": [
            "name", "email", "password", "location", 
            "language", "onemove_link", "puprime_link"
        ],
        "email_verification_required": True,
        "verification_endpoints": {
            "send_verification": "/email/send-verification",
            "verify_email": "/email/verify-email",
            "resend_verification": "/email/resend-verification",
            "check_verification": "/email/check-verification/{email}"
        }
    }

