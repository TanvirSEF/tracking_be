from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import models
import crud
from database import engine, get_db
from config import settings
from routers import auth as auth_router, admin, affiliate

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

# Include routers
app.include_router(auth_router.router, tags=["Authentication"])
app.include_router(admin.router, prefix="/admin", tags=["Admin"])
app.include_router(affiliate.router, tags=["Affiliate"])

# Initialize system on startup
@app.on_event("startup")
def startup_event():
    db = next(get_db())
    crud.initialize_system(db)
    db.close()
    print("System initialized successfully")
    print(f"Admin registration link: {settings.ADMIN_REGISTRATION_LINK}")

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
    return {"status": "healthy", "database": "postgresql"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
