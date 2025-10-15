from fastapi import APIRouter, HTTPException, status, Request, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import List, Optional

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
        affiliate = await crud.approve_affiliate_request(approval.request_id, str(current_user.id))
        if not affiliate:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Request not found or already processed"
            )
        
        # Get user email for response
        user = await models.User.find_one(models.User.id == affiliate.user_id)
        
        return {
            "message": "Affiliate approved successfully",
            "affiliate_id": str(affiliate.id),
            "unique_link": f"{settings.BASE_URL}/ref/{affiliate.unique_link}",
            "affiliate_email": user.email
        }
    else:
        request = await crud.reject_affiliate_request(approval.request_id, str(current_user.id))
        if not request:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Request not found or already processed"
            )
        return {
            "request": "Affiliate request rejected",
            "reason": approval.reason if approval.reason else "No reason provided"
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
                unique_link=f"{settings.BASE_URL}/ref/{affiliate.unique_link}",
                created_at=affiliate.created_at
            ))
    return result