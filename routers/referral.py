from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

import models
import schemas
import crud
import auth_utils as auth

router = APIRouter()
security = HTTPBearer()


# Dependency to verify referral user
async def get_current_referral_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Dependency to get current referral/member user"""
    token = credentials.credentials
    referral = await auth.get_current_referral(token)
    return referral


@router.get("/referral/profile", response_model=schemas.ReferralResponse)
async def get_referral_profile(
    current_referral: models.Referral = Depends(get_current_referral_user)
):
    """Get current referral/member profile"""
    profile = await crud.get_referral_by_id(current_referral.id)
    
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found"
        )
    
    return profile


@router.put("/referral/profile", response_model=schemas.ReferralResponse)
async def update_referral_profile(
    profile_data: schemas.ReferralProfileUpdate,
    current_referral: models.Referral = Depends(get_current_referral_user)
):
    """Update current referral/member profile"""
    updated_profile = await crud.update_referral_profile(current_referral.id, profile_data)
    
    if not updated_profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found"
        )
    
    return updated_profile


@router.delete("/referral/profile")
async def delete_referral_profile(
    current_referral: models.Referral = Depends(get_current_referral_user)
):
    """Delete current referral/member profile and all associated data"""
    result = await crud.delete_referral_profile(current_referral.id)
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found"
        )
    
    referral = result["referral"]
    affiliate = result["affiliate"]
    
    return {
        "message": "Referral profile deleted successfully",
        "deleted_referral_id": str(referral.id),
        "deleted_referral_email": referral.email,
        "deleted_referral_name": referral.full_name,
        "deleted_notes_count": result["deleted_notes_count"],
        "affiliate_name": affiliate.name if affiliate else "Unknown",
        "deleted_at": referral.created_at.isoformat()
    }


@router.get("/referral/affiliate", response_model=schemas.AffiliateResponse)
async def get_referral_affiliate(
    current_referral: models.Referral = Depends(get_current_referral_user)
):
    """Get information about the affiliate who referred this member"""
    affiliate = await crud.get_affiliate_by_referral(current_referral.id)
    
    if not affiliate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Affiliate not found"
        )
    
    return affiliate

