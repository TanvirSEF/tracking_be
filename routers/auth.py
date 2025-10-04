from fastapi import APIRouter, Depends, HTTPException, status
from datetime import timedelta

import schemas
import crud
import auth_utils as auth

router = APIRouter()


@router.post("/login", response_model=schemas.Token)
async def login(form_data: schemas.LoginForm):
    """Login endpoint for admin and affiliates"""
    user = await crud.authenticate_user(form_data.email, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated"
        )
    
    access_token_expires = timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

