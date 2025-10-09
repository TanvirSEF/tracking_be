from fastapi import APIRouter, Depends, HTTPException, status, Request
from typing import List, Optional

import models
import schemas
import crud
import auth_utils as auth
from config import settings

router = APIRouter()


@router.get("/registration-link", response_model=schemas.AdminRegistrationLinkResponse)
async def get_admin_registration_link(
    request: Request,
    current_user: models.User = Depends(auth.get_admin_user)
):
    """Get the fixed admin registration link"""
    admin_link = await crud.get_admin_registration_link()
    base_url = str(request.base_url).rstrip('/')
    
    return {
        "registration_link": admin_link,
        "full_url": f"{base_url}/register/{admin_link}"
    }


@router.get("/pending-requests", response_model=List[schemas.AffiliateRequestResponse])
async def get_pending_requests(
    current_user: models.User = Depends(auth.get_admin_user)
):
    """Get all pending affiliate requests"""
    return await crud.get_pending_requests()


@router.get("/all-requests", response_model=List[schemas.AffiliateRequestResponse])
async def get_all_requests(
    status: Optional[str] = None,
    current_user: models.User = Depends(auth.get_admin_user)
):
    """Get all affiliate requests, optionally filtered by status"""
    status_enum = None
    if status:
        try:
            status_enum = models.RequestStatus(status.lower())
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status. Must be one of: {[s.value for s in models.RequestStatus]}"
            )
    
    return await crud.get_all_requests(status_enum)


@router.post("/review-request")
async def review_affiliate_request(
    approval: schemas.ApprovalRequest,
    current_user: models.User = Depends(auth.get_admin_user)
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
    current_user: models.User = Depends(auth.get_admin_user)
):
    """Get all approved affiliates"""
    affiliates = await crud.get_all_affiliates()
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

