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
            detail="Email already registered or pending approval"
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
        onemove_link=affiliate.onemove_link,
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
    await models.Referral.find(
        models.Referral.affiliate_id == affiliate.id
    ).delete()
    
    # Delete the affiliate profile
    await affiliate.delete()
    
    # Delete the user account
    await current_user.delete()
    
    return {
        "message": "Affiliate profile and account deleted successfully",
        "deleted_affiliate_id": str(affiliate.id),
        "deleted_user_id": str(current_user.id)
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


@router.get("/debug/check-affiliate-match")
async def debug_affiliate_match(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Debug endpoint to check if affiliate IDs match"""
    current_user = await auth.get_current_user(credentials.credentials)
    
    # Get the affiliate profile
    affiliate = await crud.get_affiliate_by_user(current_user.id)
    if not affiliate:
        return {"error": "Affiliate profile not found", "user_id": str(current_user.id)}
    
    # Get all referrals in database
    all_referrals = await models.Referral.find().to_list()
    
    # Check which referrals match this affiliate
    matching_referrals = []
    for referral in all_referrals:
        if str(referral.affiliate_id) == str(affiliate.id):
            matching_referrals.append({
                "id": str(referral.id),
                "email": referral.email,
                "full_name": referral.full_name,
                "created_at": referral.created_at
            })
    
    return {
        "current_user_id": str(current_user.id),
        "current_user_email": current_user.email,
        "affiliate_id": str(affiliate.id),
        "affiliate_name": affiliate.name,
        "affiliate_unique_link": affiliate.unique_link,
        "total_referrals_in_db": len(all_referrals),
        "matching_referrals_count": len(matching_referrals),
        "matching_referrals": matching_referrals,
        "all_referrals_affiliate_ids": [str(r.affiliate_id) for r in all_referrals]
    }





