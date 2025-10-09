from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

import models
import crud
from database import init_db
from config import settings
from routers import auth as auth_router, admin, affiliate

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_db()
    await crud.initialize_system()
    print("System initialized successfully")
    print(f"Admin registration link: {settings.ADMIN_REGISTRATION_LINK}")
    yield
    # Shutdown (if needed)

app = FastAPI(
    title="Affiliate Management System",
    description="API for managing affiliate registrations and approvals",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware (configurable)
allowed_origins = (
    ["*"] if settings.CORS_ORIGINS.strip() == "*"
    else [o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()]
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router.router, tags=["Authentication"])
app.include_router(admin.router, prefix="/admin", tags=["Admin"])
app.include_router(affiliate.router, tags=["Affiliate"])

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
    return {"status": "healthy", "database": "mongodb"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
