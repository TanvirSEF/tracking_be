from fastapi import APIRouter, HTTPException, status, Header
from datetime import timedelta
from typing import Optional

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

