from fastapi import APIRouter, HTTPException, status, Header
from datetime import timedelta
from typing import Optional
from pydantic import BaseModel

import schemas
import crud
import auth_utils as auth

router = APIRouter()


@router.post("/login", response_model=schemas.Token)
async def login(login_data: schemas.LoginForm):
    """Simple login endpoint for admin and affiliates"""
    # Use email directly from the custom form
    identifier = login_data.email.lower().strip()
    
    # Simple rate limiting (optional - can be removed for even more simplicity)
    if not auth.is_login_allowed(identifier):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Please try again later."
        )

    user = await crud.authenticate_user(identifier, login_data.password)
    if not user:
        auth.register_login_failure(identifier)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated"
        )
    
    auth.register_login_success(identifier)
    access_token_expires = timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


# Email verification endpoints
class ResendVerificationRequest(BaseModel):
    email: str
    user_type: str  # "admin", "affiliate", "referral"

class VerifyEmailRequest(BaseModel):
    email: str
    code: str

@router.post("/verify-email")
async def verify_email(request: VerifyEmailRequest):
    """Verify email address using 6-digit code"""
    try:
        result = await crud.verify_email_token(request.code)
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired verification code"
            )
        
        # Extract email based on user type
        user_email = None
        if result["type"] == "referral":
            user_email = result["referral"].email
        elif result["type"] == "affiliate_request":
            user_email = result["request"].email
        elif result["type"] == "admin":
            user_email = result["user"].email
        
        if not user_email:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Unable to process verification"
            )
        
        # Verify email matches
        if user_email != request.email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email does not match verification code"
            )
        
        return {
            "message": "Email verified successfully",
            "type": result["type"],
            "email": user_email,
            "status": "verified"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Unexpected error in verify_email: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during verification"
        )

@router.post("/resend-verification")
async def resend_verification_email(request: ResendVerificationRequest):
    """Resend verification email"""
    success = await crud.resend_verification_email(request.email, request.user_type)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email not found or already verified"
        )
    
    return {
        "message": "Verification email sent successfully",
        "email": request.email
    }

