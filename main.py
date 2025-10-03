from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from datetime import timedelta
import os
from dotenv import load_dotenv
from typing import List, Optional

import models, schemas, crud, auth
from database import engine, get_db

load_dotenv()

# Create tables
models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Affiliate Management System",
    description="API for managing affiliate registrations and approvals",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize system on startup
@app.on_event("startup")
def startup_event():
    db = next(get_db())
    crud.initialize_system(db)
    db.close()
    print("System initialized successfully")
    print(f"Admin registration link: {os.getenv('ADMIN_REGISTRATION_LINK')}")

# Public endpoints
@app.get("/")
def read_root():
    return {
        "message": "Affiliate Management System API",
        "documentation": "/docs",
        "registration_endpoint": "/register/{admin_link}"
    }

@app.get("/registration-info")
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

@app.post("/register/{link_code}", response_model=schemas.AffiliateRequestResponse)
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

# Authentication endpoints
@app.post("/login", response_model=schemas.Token)
def login(form_data: schemas.LoginForm, db: Session = Depends(get_db)):
    """Login endpoint for admin and affiliates"""
    user = crud.authenticate_user(db, form_data.email, form_data.password)
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

# Admin endpoints
@app.get("/admin/registration-link", response_model=schemas.AdminRegistrationLinkResponse)
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

@app.get("/admin/pending-requests", response_model=List[schemas.AffiliateRequestResponse])
def get_pending_requests(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_admin_user)
):
    """Get all pending affiliate requests"""
    return crud.get_pending_requests(db)

@app.get("/admin/all-requests", response_model=List[schemas.AffiliateRequestResponse])
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

@app.post("/admin/review-request")
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
        
        base_url = os.getenv("BASE_URL", "http://localhost:8000")
        return {
            "message": "Affiliate approved successfully",
            "affiliate_id": affiliate.id,
            "unique_link": f"{base_url}/ref/{affiliate.unique_link}",
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

@app.get("/admin/affiliates", response_model=List[schemas.AffiliateResponse])
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
            unique_link=f"http://localhost:8000/ref/{a.unique_link}",
            created_at=a.created_at
        )
        for a in affiliates
    ]

# Affiliate endpoints
@app.get("/affiliate/profile", response_model=schemas.AffiliateResponse)
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
    
    base_url = os.getenv("BASE_URL", "http://localhost:8000")
    return schemas.AffiliateResponse(
        id=affiliate.id,
        name=affiliate.name,
        email=current_user.email,
        location=affiliate.location,
        language=affiliate.language,
        unique_link=f"{base_url}/ref/{affiliate.unique_link}",
        created_at=affiliate.created_at
    )

@app.get("/ref/{unique_link}")
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

# Health check
@app.get("/health")
def health_check():
    return {"status": "healthy", "database": "postgresql"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
