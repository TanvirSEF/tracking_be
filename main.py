from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

import models
import crud
from database import init_db, database_initialized
from config import settings
from routers import auth as auth_router, admin, affiliate, email_verification

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    db_connected = await init_db()
    
    # Only initialize system if database connected
    if db_connected:
        try:
            await crud.initialize_system()
            print("System initialized")
            print(f"Admin link: {settings.ADMIN_REGISTRATION_LINK}")
        except Exception as e:
            print(f"System init failed: {e}")
    else:
        print("Skipping system initialization")
    
    print("API is ready (database may be disconnected)")
    
    yield
    
    # Shutdown
    print("Shutting down")

app = FastAPI(
    title="Affiliate Management System",
    description="API for managing affiliate registrations and approvals",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware (configurable)
# Parse and validate CORS origins; if wildcard, disable credentials for safety
allowed_origins = (
    ["*"] if settings.CORS_ORIGINS.strip() == "*"
    else [o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()]
)
allow_credentials = False if allowed_origins == ["*"] else True
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router.router, tags=["Authentication"])
app.include_router(admin.router, prefix="/admin", tags=["Admin"])
app.include_router(affiliate.router, tags=["Affiliate"])
app.include_router(email_verification.router, prefix="/email", tags=["Email Verification"])

# Root endpoint
@app.get("/")
def read_root():
    return {
        "message": "Affiliate Management System API",
        "documentation": "/docs",
        "registration_endpoint": "/register/{admin_link}"
    }

# Health check
@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "database": "connected" if database_initialized else "disconnected"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
