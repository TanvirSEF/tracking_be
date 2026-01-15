from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import List, Optional

import models
import schemas
import crud
import auth_utils as auth

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

@router.get("/notes", response_model=List[schemas.PublicNoteResponse])
async def get_all_notes(
    page: int = 1,
    page_size: int = 20
):
    """
    Get all published public notes/announcements.
    No authentication required - anyone can read.
    """
    notes = await crud.get_all_public_notes(
        page=page,
        page_size=page_size,
        include_unpublished=False  # Only show published notes to public
    )
    return notes

@router.get("/notes/{note_id}", response_model=schemas.PublicNoteResponse)
async def get_note_by_id(note_id: str):
    """
    Get a specific public note by ID.
    No authentication required - anyone can read.
    """
    note = await crud.get_public_note_by_id(note_id)
    
    if not note:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Note not found"
        )
    
    # Only return if published (for public access)
    if not note.is_published:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Note not found"
        )
    
    return note

# ==================== ADMIN ENDPOINTS (Auth Required) ====================

@router.post("/admin/notes", response_model=schemas.PublicNoteResponse)
async def create_note(
    note_data: schemas.PublicNoteCreate,
    current_user: models.User = Depends(get_current_admin)
):
    """
    Create a new public note/announcement.
    Admin only.
    """
    note = await crud.create_public_note(
        admin_id=str(current_user.id),
        admin_email=current_user.email,
        note_data=note_data
    )
    
    return note

@router.get("/admin/notes", response_model=List[schemas.PublicNoteResponse])
async def get_all_notes_admin(
    page: int = 1,
    page_size: int = 20,
    current_user: models.User = Depends(get_current_admin)
):
    """
    Get all public notes including unpublished drafts.
    Admin only.
    """
    notes = await crud.get_all_public_notes(
        page=page,
        page_size=page_size,
        include_unpublished=True  # Admin can see all notes
    )
    return notes

@router.patch("/admin/notes/{note_id}", response_model=schemas.PublicNoteResponse)
async def update_note(
    note_id: str,
    update_data: schemas.PublicNoteUpdate,
    current_user: models.User = Depends(get_current_admin)
):
    """
    Update a public note.
    Admin only.
    """
    note = await crud.update_public_note(note_id, update_data)
    
    if not note:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Note not found"
        )
    
    return note

@router.put("/admin/notes/{note_id}", response_model=schemas.PublicNoteResponse)
async def update_note_put(
    note_id: str,
    update_data: schemas.PublicNoteUpdate,
    current_user: models.User = Depends(get_current_admin)
):
    """
    Update a public note (PUT method).
    Admin only.
    """
    note = await crud.update_public_note(note_id, update_data)
    
    if not note:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Note not found"
        )
    
    return note

@router.delete("/admin/notes/{note_id}")
async def delete_note(
    note_id: str,
    current_user: models.User = Depends(get_current_admin)
):
    """
    Delete a public note.
    Admin only.
    """
    result = await crud.delete_public_note(note_id)
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Note not found"
        )
    
    return {
        "message": "Note deleted successfully",
        "note_id": note_id
    }
