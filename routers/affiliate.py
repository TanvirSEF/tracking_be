from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

import models
import schemas
import crud
import auth_utils as auth
from database import get_db
from config import settings

router = APIRouter()


@router.post("/register/{link_code}", response_model=schemas.AffiliateRequestResponse)
def register_affiliate(
    link_code: str,
    request: schemas.AffiliateRequestCreate,
    db: Session = Depends(get_db)
):
    """
    Register a new affiliate using the admin registration link.
    The link_code must match the fixed admin registration link.
    """
    # Verify registration link
    if not crud.verify_registration_link(db, link_code):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid registration link. Please contact admin for the correct link."
        )
    
    # Create affiliate request
    affiliate_request = crud.create_affiliate_request(db, request)
    if not affiliate_request:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered or pending approval"
        )
    
    return affiliate_request


@router.get("/affiliate/profile", response_model=schemas.AffiliateResponse)
def get_affiliate_profile(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """Get current affiliate's profile"""
    if current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin users don't have affiliate profiles"
        )
    
    affiliate = crud.get_affiliate_by_user(db, current_user.id)
    if not affiliate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Affiliate profile not found"
        )
    
    return schemas.AffiliateResponse(
        id=affiliate.id,
        name=affiliate.name,
        email=current_user.email,
        location=affiliate.location,
        language=affiliate.language,
        unique_link=f"{settings.BASE_URL}/ref/{affiliate.unique_link}",
        created_at=affiliate.created_at
    )


@router.get("/ref/{unique_link}")
def track_affiliate_link(unique_link: str, db: Session = Depends(get_db)):
    """Track clicks on affiliate links - this is the individual affiliate's unique link"""
    affiliate = db.query(models.Affiliate).filter(
        models.Affiliate.unique_link == unique_link
    ).first()
    
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
        "affiliate_id": affiliate.id,
        # Add redirect URL or tracking logic here
        "redirect_to": "https://your-landing-page.com"
    }


@router.get("/registration-info")
def get_registration_info():
    """Get information about the registration process"""
    return {
        "message": "To register as an affiliate, you need the admin registration link",
        "registration_url_format": "{base_url}/register/{admin_link}",
        "required_fields": [
            "name", "email", "password", "location", 
            "language", "onemove_link", "puprime_link"
        ]
    }

