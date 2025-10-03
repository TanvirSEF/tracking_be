from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import List, Optional

import models
import schemas
import crud
import auth_utils as auth
from database import get_db
from config import settings

router = APIRouter()


@router.get("/registration-link", response_model=schemas.AdminRegistrationLinkResponse)
def get_admin_registration_link(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_admin_user)
):
    """Get the fixed admin registration link"""
    admin_link = crud.get_admin_registration_link(db)
    base_url = str(request.base_url).rstrip('/')
    
    return {
        "registration_link": admin_link,
        "full_url": f"{base_url}/register/{admin_link}"
    }


@router.get("/pending-requests", response_model=List[schemas.AffiliateRequestResponse])
def get_pending_requests(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_admin_user)
):
    """Get all pending affiliate requests"""
    return crud.get_pending_requests(db)


@router.get("/all-requests", response_model=List[schemas.AffiliateRequestResponse])
def get_all_requests(
    status: Optional[str] = None,
    db: Session = Depends(get_db),
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
    
    return crud.get_all_requests(db, status_enum)


@router.post("/review-request")
def review_affiliate_request(
    approval: schemas.ApprovalRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_admin_user)
):
    """Approve or reject an affiliate request"""
    if approval.approve:
        affiliate = crud.approve_affiliate_request(db, approval.request_id, current_user.id)
        if not affiliate:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Request not found or already processed"
            )
        
        return {
            "message": "Affiliate approved successfully",
            "affiliate_id": affiliate.id,
            "unique_link": f"{settings.BASE_URL}/ref/{affiliate.unique_link}",
            "affiliate_email": affiliate.user.email
        }
    else:
        request = crud.reject_affiliate_request(db, approval.request_id, current_user.id)
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
def get_all_affiliates(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_admin_user)
):
    """Get all approved affiliates"""
    affiliates = crud.get_all_affiliates(db)
    return [
        schemas.AffiliateResponse(
            id=a.id,
            name=a.name,
            email=a.user.email,
            location=a.location,
            language=a.language,
            unique_link=f"{settings.BASE_URL}/ref/{a.unique_link}",
            created_at=a.created_at
        )
        for a in affiliates
    ]

