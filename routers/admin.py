from fastapi import APIRouter, HTTPException, status, Request, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import List, Optional
from datetime import datetime

import models
import schemas
import crud
import auth_utils as auth
from config import settings

router = APIRouter()
security = HTTPBearer()


# Dependency to verify admin user
async def get_current_admin(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Dependency to get current admin user"""
    token = credentials.credentials
    current_user = await auth.get_current_user(token)
    
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    return current_user


@router.post("/create-admin", response_model=schemas.AdminCreateResponse)
async def create_admin_user(
    admin_data: schemas.AdminCreateRequest,
    current_user: models.User = Depends(get_current_admin)
):
    """
    Create a new admin user with the same permissions.
    Only existing admins can create new admins.
    The new admin will have full access to all admin endpoints and the same registration link.
    """
    # Check if email already exists
    existing_user = await models.User.find_one(models.User.email == admin_data.email.lower().strip())
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists"
        )
    
    # Create the admin user
    try:
        new_admin = await crud.create_admin_user(admin_data.email.lower().strip(), admin_data.password)
        
        return schemas.AdminCreateResponse(
            message="Admin user created successfully",
            admin_id=str(new_admin.id),
            email=new_admin.email,
            is_admin=new_admin.is_admin,
            is_active=new_admin.is_active,
            created_at=new_admin.created_at,
            created_by=current_user.email
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create admin user: {str(e)}"
        )


@router.get("/admins", response_model=List[schemas.AdminResponse])
async def get_all_admins(
    page: int = 1,
    page_size: int = 50,
    current_user: models.User = Depends(get_current_admin)
):
    """
    Get all admin users (paginated).
    Only admins can view the list of other admins.
    """
    if page < 1:
        page = 1
    if page_size < 1:
        page_size = 1
    if page_size > 100:
        page_size = 100
    
    skip = (page - 1) * page_size
    
    # Get all admin users
    admin_users = await models.User.find(
        models.User.is_admin == True
    ).sort("-created_at").skip(skip).limit(page_size).to_list()
    
    # Convert to response format
    result = []
    for admin in admin_users:
        result.append(schemas.AdminResponse(
            id=str(admin.id),
            email=admin.email,
            is_admin=admin.is_admin,
            is_active=admin.is_active,
            is_email_verified=admin.is_email_verified,
            created_at=admin.created_at
        ))
    
    return result


@router.get("/registration-link", response_model=schemas.AdminRegistrationLinkResponse)
async def get_admin_registration_link(
    request: Request,
    current_user: models.User = Depends(get_current_admin)
):
    """Get the fixed admin registration link"""
    admin_link = await crud.get_admin_registration_link()
    base_url = str(request.base_url).rstrip('/')
    
    return {
        "registration_link": admin_link,
        "full_url": f"{base_url}/register/{admin_link}"
    }


@router.get("/pending-requests", response_model=List[schemas.AffiliateRequestResponse])
async def get_pending_requests(current_user: models.User = Depends(get_current_admin)):
    """Get all pending affiliate requests"""
    return await crud.get_pending_requests()





@router.post("/review-request")
async def review_affiliate_request(
    approval: schemas.ApprovalRequest,
    current_user: models.User = Depends(get_current_admin)
):
    """Approve or reject an affiliate request"""
    if approval.approve:
        try:
            affiliate = await crud.approve_affiliate_request(approval.request_id, str(current_user.id))
            if not affiliate:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Request not found or already processed"
                )
        except ValueError as e:
            # Handle validation errors
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
        
        # Get user email for response
        user = await models.User.find_one(models.User.id == affiliate.user_id)
        
        return {
            "message": "Affiliate approved successfully",
            "affiliate_id": str(affiliate.id),
            "unique_link": f"{settings.BASE_URL}/ref/{affiliate.unique_link}",
            "affiliate_email": user.email,
            "status": "approved",
            "admin_reviewer": current_user.email,
            "reviewed_at": datetime.utcnow().isoformat()
        }
    else:
        request_info = await crud.reject_affiliate_request(approval.request_id, str(current_user.id))
        if not request_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Request not found or already processed"
            )
        return {
            "message": "Affiliate request rejected and removed from database",
            "reason": approval.reason if approval.reason else "No reason provided",
            "request_id": request_info["id"],
            "email": request_info["email"],
            "name": request_info["name"],
            "status": "rejected",
            "admin_reviewer": current_user.email,
            "reviewed_at": request_info["reviewed_at"].isoformat()
        }


@router.get("/affiliates", response_model=List[schemas.AffiliateResponse])
async def get_all_affiliates(
    page: int = 1,
    page_size: int = 20,
    current_user: models.User = Depends(get_current_admin)
):
    """Get all approved affiliates"""
    affiliates = await crud.get_all_affiliates(page=page, page_size=page_size)
    result = []
    for affiliate in affiliates:
        user = await models.User.find_one(models.User.id == affiliate.user_id)
        if user and user.is_active:
            result.append(schemas.AffiliateResponse(
                id=str(affiliate.id),
                name=affiliate.name,
                email=user.email,
                location=affiliate.location,
                language=affiliate.language,
                puprime_referral_code=affiliate.puprime_referral_code,
                puprime_link=affiliate.puprime_link,
                unique_link=f"{settings.BASE_URL}/ref/{affiliate.unique_link}",
                created_at=affiliate.created_at
            ))
    return result


@router.delete("/affiliates/{affiliate_id}")
async def delete_affiliate_profile(
    affiliate_id: str,
    current_user: models.User = Depends(get_current_admin)
):
    """Delete an affiliate profile and all associated data"""
    from beanie import PydanticObjectId
    
    try:
        # Convert string to ObjectId
        affiliate_object_id = PydanticObjectId(affiliate_id)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid affiliate ID format"
        )
    
    # Find the affiliate
    affiliate = await models.Affiliate.find_one(models.Affiliate.id == affiliate_object_id)
    if not affiliate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Affiliate not found"
        )
    
    # Get the user associated with this affiliate
    user = await models.User.find_one(models.User.id == affiliate.user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Associated user not found"
        )
    
    # Delete all referrals associated with this affiliate
    referrals_result = await models.Referral.find(
        models.Referral.affiliate_id == affiliate.id
    ).delete()
    
    # Delete the affiliate request associated with this user's email
    affiliate_request_result = await models.AffiliateRequest.find(
        models.AffiliateRequest.email == user.email
    ).delete()
    
    # Delete the affiliate profile
    await affiliate.delete()
    
    # Delete the user account
    await user.delete()
    
    return {
        "message": "Affiliate profile and account deleted successfully",
        "deleted_affiliate_id": str(affiliate.id),
        "deleted_user_id": str(user.id),
        "deleted_referrals_count": referrals_result.deleted_count,
        "deleted_affiliate_requests_count": affiliate_request_result.deleted_count,
        "deleted_by_admin": current_user.email,
        "deleted_at": datetime.utcnow().isoformat()
    }


@router.get("/referrals", response_model=List[schemas.ReferralResponse])
async def get_all_referrals(
    page: int = 1,
    page_size: int = 20,
    affiliate_id: Optional[str] = None,
    search: Optional[str] = None,
    current_user: models.User = Depends(get_current_admin)
):
    """Get all referrals across all affiliates (admin view)"""
    referrals = await crud.get_all_referrals(
        page=page, 
        page_size=page_size,
        affiliate_id=affiliate_id,
        search=search
    )
    return referrals


@router.delete("/referrals/{referral_id}")
async def delete_referral(
    referral_id: str,
    current_user: models.User = Depends(get_current_admin)
):
    """Delete any referral (admin function)"""
    result = await crud.delete_referral_by_admin(referral_id)
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Referral not found"
        )
    
    referral = result["referral"]
    affiliate = result["affiliate"]
    
    return {
        "message": "Referral deleted successfully",
        "deleted_referral_id": str(referral.id),
        "deleted_referral_email": referral.email,
        "deleted_referral_name": referral.full_name,
        "affiliate_id": str(affiliate.id) if affiliate else None,
        "affiliate_name": affiliate.name if affiliate else None,
        "deleted_by_admin": current_user.email,
        "deleted_at": datetime.utcnow().isoformat()
    }


@router.get("/top-affiliates", response_model=List[schemas.TopAffiliateResponse])
async def get_top_affiliates(
    limit: int = 10,
    current_user: models.User = Depends(get_current_admin)
):
    """Get top affiliates ranked by referral count"""
    # Validate limit
    if limit < 1:
        limit = 1
    if limit > 100:
        limit = 100
    
    top_affiliates = await crud.get_top_affiliates_by_referrals(limit=limit)
    return top_affiliates