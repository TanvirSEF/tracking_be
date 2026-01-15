from fastapi import APIRouter, HTTPException, status, Depends, File, UploadFile, Form
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import List, Optional

import models
import schemas
import crud
import auth_utils as auth
import cloudinary_utils

router = APIRouter()
security = HTTPBearer()

# ==================== Admin Dependency ====================

async def get_current_admin(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Dependency to get current admin user"""
    token = credentials.credentials
    user = await auth.get_current_user(token)
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return user

# ==================== PUBLIC ENDPOINTS (No Auth Required) ====================

@router.get("/tutorials", response_model=List[schemas.TutorialVideoResponse])
async def get_all_tutorials(
    page: int = 1,
    page_size: int = 20
):
    """
    Get all published tutorial videos.
    No authentication required - anyone can watch.
    """
    videos = await crud.get_all_tutorial_videos(
        page=page,
        page_size=page_size,
        include_unpublished=False  # Only show published videos to public
    )
    return videos

@router.get("/tutorials/{video_id}", response_model=schemas.TutorialVideoResponse)
async def get_tutorial_by_id(video_id: str):
    """
    Get a specific tutorial video by ID and increment view count.
    No authentication required - anyone can watch.
    """
    video = await crud.get_tutorial_video_by_id(video_id, increment_view=True)
    
    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tutorial video not found"
        )
    
    # Only return if published (for public access)
    if not video.is_published:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tutorial video not found"
        )
    
    return video

# ==================== ADMIN ENDPOINTS (Auth Required) ====================

@router.post("/admin/tutorials", response_model=schemas.TutorialVideoResponse)
async def upload_tutorial(
    title: str = Form(..., min_length=1, max_length=200, description="Video title"),
    description: str = Form(..., min_length=1, max_length=2000, description="Video description"),
    video: UploadFile = File(..., description="Video file (MP4, MOV, AVI, etc.)"),
    current_user: models.User = Depends(get_current_admin)
):
    """
    Upload a new tutorial video to Cloudinary.
    Admin only.
    
    Accepts multipart/form-data with:
    - title: Video title
    - description: Video description
    - video: Video file (max 100MB)
    
    Supported formats: MP4, MPEG, MOV, AVI, WMV, WEBM
    """
    # Upload video to Cloudinary
    try:
        video_data = await cloudinary_utils.upload_tutorial_video(video)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to upload video: {str(e)}"
        )
    
    # Create tutorial video record in database
    tutorial = await crud.create_tutorial_video(
        admin_id=str(current_user.id),
        admin_email=current_user.email,
        title=title,
        description=description,
        video_data=video_data
    )
    
    return tutorial

@router.get("/admin/tutorials", response_model=List[schemas.TutorialVideoResponse])
async def get_all_tutorials_admin(
    page: int = 1,
    page_size: int = 20,
    current_user: models.User = Depends(get_current_admin)
):
    """
    Get all tutorial videos including unpublished drafts.
    Admin only.
    """
    videos = await crud.get_all_tutorial_videos(
        page=page,
        page_size=page_size,
        include_unpublished=True  # Admin can see all videos
    )
    return videos

@router.patch("/admin/tutorials/{video_id}", response_model=schemas.TutorialVideoResponse)
async def update_tutorial(
    video_id: str,
    update_data: schemas.TutorialVideoUpdate,
    current_user: models.User = Depends(get_current_admin)
):
    """
    Update tutorial video metadata (title, description, publish status).
    Admin only.
    
    Note: This only updates metadata, not the video file itself.
    """
    video = await crud.update_tutorial_video(video_id, update_data)
    
    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tutorial video not found"
        )
    
    return video

@router.put("/admin/tutorials/{video_id}", response_model=schemas.TutorialVideoResponse)
async def update_tutorial_put(
    video_id: str,
    update_data: schemas.TutorialVideoUpdate,
    current_user: models.User = Depends(get_current_admin)
):
    """
    Update tutorial video metadata (PUT method).
    Admin only.
    """
    video = await crud.update_tutorial_video(video_id, update_data)
    
    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tutorial video not found"
        )
    
    return video

@router.delete("/admin/tutorials/{video_id}")
async def delete_tutorial(
    video_id: str,
    current_user: models.User = Depends(get_current_admin)
):
    """
    Delete a tutorial video from both database and Cloudinary.
    Admin only.
    
    This will permanently delete the video file from Cloudinary.
    """
    result = await crud.delete_tutorial_video(video_id)
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tutorial video not found"
        )
    
    return {
        "message": "Tutorial video deleted successfully",
        "video_id": video_id,
        "cloudinary_deleted": True
    }
