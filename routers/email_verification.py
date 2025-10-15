from fastapi import APIRouter, Depends, HTTPException, status
from datetime import datetime

import schemas
import crud
import models
import auth_utils as auth

router = APIRouter()

@router.post("/send-verification", response_model=schemas.EmailVerificationResponse)
async def send_verification_email(request: schemas.EmailVerificationRequest):
    """
    Send verification email to the provided email address.
    This is typically called before affiliate registration.
    """
    # Check if email is already verified
    if await crud.is_email_verified(request.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email is already verified"
        )
    
    # Check if email already exists in users or requests
    existing_user = await models.User.find_one(models.User.email == request.email)
    existing_request = await models.AffiliateRequest.find_one(
        models.AffiliateRequest.email == request.email
    )
    
    if existing_user or existing_request:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email is already registered"
        )
    
    # Send verification email
    success = await crud.send_verification_email(request.email)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send verification email. Please try again later."
        )
    
    # Get verification record for response
    verification = await models.EmailVerification.find_one(
        models.EmailVerification.email == request.email
    )
    
    return schemas.EmailVerificationResponse(
        message="Verification email sent successfully",
        email=request.email,
        expires_at=verification.expires_at if verification else datetime.utcnow()
    )

@router.post("/verify-email")
async def verify_email(request: schemas.EmailVerificationCode):
    """
    Verify email with the provided verification code.
    """
    # Check if email is already verified
    if await crud.is_email_verified(request.email):
        return {
            "message": "Email is already verified",
            "verified": True
        }
    
    # Verify the code
    is_valid = await crud.verify_email_code(request.email, request.verification_code)
    
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification code or code has expired"
        )
    
    return {
        "message": "Email verified successfully",
        "verified": True,
        "email": request.email
    }

@router.post("/resend-verification")
async def resend_verification_email(request: schemas.ResendVerificationRequest):
    """
    Resend verification email to the provided email address.
    """
    # Check if email is already verified
    if await crud.is_email_verified(request.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email is already verified"
        )
    
    # Check if email already exists in users or requests
    existing_user = await models.User.find_one(models.User.email == request.email)
    existing_request = await models.AffiliateRequest.find_one(
        models.AffiliateRequest.email == request.email
    )
    
    if existing_user or existing_request:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email is already registered"
        )
    
    # Resend verification email
    success = await crud.resend_verification_email(request.email)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to resend verification email. Please try again later."
        )
    
    return {
        "message": "Verification email resent successfully",
        "email": request.email
    }

@router.get("/check-verification/{email}")
async def check_verification_status(email: str):
    """
    Check if an email is verified.
    """
    is_verified = await crud.is_email_verified(email)
    
    return {
        "email": email,
        "verified": is_verified
    }
