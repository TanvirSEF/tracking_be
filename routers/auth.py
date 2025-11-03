from fastapi import APIRouter, HTTPException, status, Header
from datetime import timedelta
from typing import Optional
from pydantic import BaseModel

import schemas
import crud
import auth_utils as auth

router = APIRouter()


@router.post("/admin/login", response_model=schemas.LoginResponse)
async def admin_login(login_data: schemas.AdminLoginForm):
    """Admin-only login endpoint with role validation"""
    identifier = login_data.email.lower().strip()
    
    # Rate limiting
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
            detail="Invalid admin credentials"
        )
    
    # Check if user is admin
    if not user.is_admin:
        auth.register_login_failure(identifier)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required. Please use affiliate login endpoint."
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
    
    return schemas.LoginResponse(
        access_token=access_token,
        token_type="bearer",
        user_type="admin",
        email=user.email,
        is_admin=True
    )


@router.post("/affiliate/login", response_model=schemas.LoginResponse)
async def affiliate_login(login_data: schemas.AffiliateLoginForm):
    """Affiliate-only login endpoint with role validation"""
    identifier = login_data.email.lower().strip()
    
    # Rate limiting
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
            detail="Invalid affiliate credentials"
        )
    
    # Check if user is NOT admin (affiliate)
    if user.is_admin:
        auth.register_login_failure(identifier)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin users should use admin login endpoint"
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
    
    return schemas.LoginResponse(
        access_token=access_token,
        token_type="bearer",
        user_type="affiliate",
        email=user.email,
        is_admin=False
    )


@router.post("/referral/login", response_model=schemas.LoginResponse)
async def referral_login(login_data: schemas.ReferralLoginForm):
    """Referral-only login endpoint with role validation"""
    identifier = login_data.email.lower().strip()
    
    # Rate limiting
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
            detail="Invalid referral credentials"
        )
    
    # Check if user is NOT admin (referral)
    if user.is_admin:
        auth.register_login_failure(identifier)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin users should use admin login endpoint"
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
    
    return schemas.LoginResponse(
        access_token=access_token,
        token_type="bearer",
        user_type="referral",
        email=user.email,
        is_admin=False
    )


@router.post("/login", response_model=schemas.Token)
async def login(login_data: schemas.LoginForm):
    """Legacy login endpoint - kept for backward compatibility"""
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


# Password reset endpoints
@router.post("/forgot-password", response_model=schemas.PasswordResetResponse)
async def forgot_password(request: schemas.PasswordResetRequest):
    """Request password reset"""
    result = await crud.request_password_reset(request.email)
    
    if not result:
        # Always return success for security (don't reveal if email exists)
        return schemas.PasswordResetResponse(
            message="If the email exists, a password reset link has been sent",
            email=request.email,
            expires_in_hours=24
        )
    
    return schemas.PasswordResetResponse(
        message="Password reset email sent successfully",
        email=request.email,
        expires_in_hours=24
    )


@router.post("/reset-password")
async def reset_password(request: schemas.PasswordResetConfirm):
    """Reset password using token"""
    result = await crud.reset_password_with_token(request.token, request.new_password)
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )
    
    return {
        "message": "Password reset successfully",
        "email": result["email"],
        "reset_at": result["reset_at"]
    }


@router.post("/resend-password-reset", response_model=schemas.PasswordResetResponse)
async def resend_password_reset(request: schemas.PasswordResetRequest):
    """Resend password reset email"""
    result = await crud.resend_password_reset_email(request.email)
    
    if not result:
        # Always return success for security (don't reveal if email exists)
        return schemas.PasswordResetResponse(
            message="If the email exists, a new password reset link has been sent",
            email=request.email,
            expires_in_hours=24
        )
    
    return schemas.PasswordResetResponse(
        message="Password reset email resent successfully",
        email=request.email,
        expires_in_hours=24
    )
