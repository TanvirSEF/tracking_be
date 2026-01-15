import cloudinary
import cloudinary.uploader
from fastapi import UploadFile, HTTPException
from config import settings
from typing import Optional
import uuid

# Configure Cloudinary with settings from environment
def configure_cloudinary():
    """Initialize Cloudinary configuration"""
    if settings.CLOUDINARY_CLOUD_NAME and settings.CLOUDINARY_API_KEY and settings.CLOUDINARY_API_SECRET:
        cloudinary.config(
            cloud_name=settings.CLOUDINARY_CLOUD_NAME,
            api_key=settings.CLOUDINARY_API_KEY,
            api_secret=settings.CLOUDINARY_API_SECRET,
            secure=True
        )
        return True
    return False

async def upload_ticket_image(file: UploadFile) -> str:
    """
    Upload ticket image to Cloudinary
    
    Args:
        file: UploadFile object from FastAPI
        
    Returns:
        str: Cloudinary secure URL
        
    Raises:
        HTTPException: If validation fails or upload fails
    """
    # Check if Cloudinary is configured
    if not configure_cloudinary():
        raise HTTPException(
            status_code=500,
            detail="Cloudinary not configured. Please add CLOUDINARY credentials to .env file"
        )
    
    # Validate file type
    allowed_types = ["image/jpeg", "image/jpg", "image/png", "image/gif", "image/webp"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type '{file.content_type}'. Only JPEG, PNG, GIF, and WEBP images are allowed"
        )
    
    # Validate file size (max 5MB)
    contents = await file.read()
    file_size = len(contents)
    
    if file_size > 5 * 1024 * 1024:  # 5MB in bytes
        raise HTTPException(
            status_code=400,
            detail=f"File too large ({file_size / (1024*1024):.2f}MB). Maximum size is 5MB"
        )
    
    # Validate file is not empty
    if file_size == 0:
        raise HTTPException(
            status_code=400,
            detail="File is empty"
        )
    
    try:
        # Generate unique filename
        unique_filename = f"ticket_{uuid.uuid4().hex}"
        
        # Upload to Cloudinary
        result = cloudinary.uploader.upload(
            contents,
            folder="support_tickets",  # Organize in folder
            public_id=unique_filename,
            resource_type="image",
            quality="auto",  # Auto-optimize quality
            transformation={
                "width": 1920,  # Max width
                "height": 1080,  # Max height
                "crop": "limit"  # Only resize if larger
            },
            overwrite=False,  # Don't overwrite existing files
            unique_filename=True
        )
        
        # Return secure HTTPS URL
        return result['secure_url']
    
    except cloudinary.exceptions.Error as e:
        raise HTTPException(
            status_code=500,
            detail=f"Cloudinary upload failed: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to upload image: {str(e)}"
        )


async def upload_reply_image(file: UploadFile) -> str:
    """
    Upload reply image to Cloudinary
    
    Args:
        file: UploadFile object from FastAPI
        
    Returns:
        str: Cloudinary secure URL
        
    Raises:
        HTTPException: If validation fails or upload fails
    """
    # Check if Cloudinary is configured
    if not configure_cloudinary():
        raise HTTPException(
            status_code=500,
            detail="Cloudinary not configured. Please add CLOUDINARY credentials to .env file"
        )
    
    # Validate file type
    allowed_types = ["image/jpeg", "image/jpg", "image/png", "image/gif", "image/webp"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type '{file.content_type}'. Only JPEG, PNG, GIF, and WEBP images are allowed"
        )
    
    # Validate file size (max 5MB)
    contents = await file.read()
    file_size = len(contents)
    
    if file_size > 5 * 1024 * 1024:  # 5MB in bytes
        raise HTTPException(
            status_code=400,
            detail=f"File too large ({file_size / (1024*1024):.2f}MB). Maximum size is 5MB"
        )
    
    # Validate file is not empty
    if file_size == 0:
        raise HTTPException(
            status_code=400,
            detail="File is empty"
        )
    
    try:
        # Generate unique filename for reply
        unique_filename = f"reply_{uuid.uuid4().hex}"
        
        # Upload to Cloudinary
        result = cloudinary.uploader.upload(
            contents,
            folder="support_tickets/replies",  # Organize in subfolder
            public_id=unique_filename,
            resource_type="image",
            quality="auto",
            transformation={
                "width": 1920,
                "height": 1080,
                "crop": "limit"
            },
            overwrite=False,
            unique_filename=True
        )
        
        # Return secure HTTPS URL
        return result['secure_url']
    
    except cloudinary.exceptions.Error as e:
        raise HTTPException(
            status_code=500,
            detail=f"Cloudinary upload failed: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to upload image: {str(e)}"
        )


async def delete_cloudinary_image(image_url: str) -> bool:
    """
    Delete image from Cloudinary (optional cleanup when ticket/reply is deleted)
    
    Args:
        image_url: Cloudinary URL of the image
        
    Returns:
        bool: True if deleted successfully, False otherwise
    """
    if not configure_cloudinary():
        print("Warning: Cloudinary not configured, cannot delete image")
        return False
    
    try:
        # Extract public_id from URL
        # Example URL: https://res.cloudinary.com/cloud_name/image/upload/v1234567/support_tickets/ticket_abc123.jpg
        # We need to extract: support_tickets/ticket_abc123
        
        parts = image_url.split('/')
        
        # Find the version marker (starts with 'v' followed by numbers)
        version_index = -1
        for i, part in enumerate(parts):
            if part.startswith('v') and part[1:].isdigit():
                version_index = i
                break
        
        if version_index > 0 and version_index < len(parts) - 1:
            # Get everything after version, remove file extension
            public_id_parts = parts[version_index + 1:]
            public_id = '/'.join(public_id_parts)
            public_id = public_id.rsplit('.', 1)[0]  # Remove extension
            
            # Delete from Cloudinary
            result = cloudinary.uploader.destroy(public_id, resource_type="image")
            
            if result.get('result') == 'ok':
                print(f"Successfully deleted image: {public_id}")
                return True
            else:
                print(f"Failed to delete image: {result}")
                return False
    except Exception as e:
        print(f"Error deleting image from Cloudinary: {e}")
        return False
    
    return False

# ==================== Tutorial Video Upload Functions ====================

async def upload_tutorial_video(file: UploadFile) -> dict:
    """
    Upload tutorial video to Cloudinary with professional settings
    
    Args:
        file: UploadFile object from FastAPI
        
    Returns:
        dict: {
            'video_url': str,  # Cloudinary secure URL
            'public_id': str,  # For deletion
            'thumbnail_url': str,  # Auto-generated thumbnail
            'duration': int,  # Video duration in seconds
            'format': str,  # Video format
            'size': int  # File size in bytes
        }
        
    Raises:
        HTTPException: If validation fails or upload fails
    """
    # Check if Cloudinary is configured
    if not configure_cloudinary():
        raise HTTPException(
            status_code=500,
            detail="Cloudinary not configured. Please add CLOUDINARY credentials to .env file"
        )
    
    # Validate file type - support common video formats
    allowed_types = [
        "video/mp4", 
        "video/mpeg", 
        "video/quicktime",  # .mov
        "video/x-msvideo",  # .avi
        "video/x-ms-wmv",  # .wmv
        "video/webm"
    ]
    
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type '{file.content_type}'. Supported formats: MP4, MPEG, MOV, AVI, WMV, WEBM"
        )
    
    # Read file contents
    contents = await file.read()
    file_size = len(contents)
    
    # Validate file size (max 100MB for videos)
    max_size = 100 * 1024 * 1024  # 100MB in bytes
    if file_size > max_size:
        raise HTTPException(
            status_code=400,
            detail=f"File too large ({file_size / (1024*1024):.2f}MB). Maximum size is 100MB"
        )
    
    # Validate file is not empty
    if file_size == 0:
        raise HTTPException(
            status_code=400,
            detail="File is empty"
        )
    
    try:
        # Generate unique filename
        unique_filename = f"tutorial_{uuid.uuid4().hex}"
        
        # Upload to Cloudinary with video optimizations
        result = cloudinary.uploader.upload(
            contents,
            folder="tutorials",  # Organize in tutorials folder
            public_id=unique_filename,
            resource_type="video",  # Important: specify video resource type
            quality="auto",  # Auto-optimize quality
            format="mp4",  # Convert to MP4 for compatibility
            transformation=[
                {
                    "quality": "auto:good",  # Good quality with auto optimization
                    "fetch_format": "auto"  # Auto format selection
                }
            ],
            eager=[
                {
                    "width": 1280,
                    "height": 720,
                    "crop": "limit",  # HD quality, limit to 720p
                    "quality": "auto:good"
                }
            ],
            eager_async=True,  # Generate transformations asynchronously
            overwrite=False,
            unique_filename=True
        )
        
        # Extract video metadata
        video_url = result.get('secure_url')
        public_id = result.get('public_id')
        duration = result.get('duration', 0)  # Duration in seconds
        video_format = result.get('format', 'mp4')
        
        # Generate thumbnail URL (Cloudinary auto-generates thumbnails for videos)
        # Get thumbnail at 1 second mark
        thumbnail_url = cloudinary.CloudinaryImage(public_id).build_url(
            resource_type="video",
            format="jpg",
            transformation=[
                {"width": 640, "height": 360, "crop": "fill"},
                {"start_offset": "1"}  # Thumbnail at 1 second
            ]
        )
        
        return {
            'video_url': video_url,
            'public_id': public_id,
            'thumbnail_url': thumbnail_url,
            'duration': int(duration) if duration else 0,
            'format': video_format,
            'size': file_size
        }
    
    except cloudinary.exceptions.Error as e:
        raise HTTPException(
            status_code=500,
            detail=f"Cloudinary upload failed: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to upload video: {str(e)}"
        )


async def delete_cloudinary_video(public_id: str) -> bool:
    """
    Delete video from Cloudinary
    
    Args:
        public_id: Cloudinary public_id of the video
        
    Returns:
        bool: True if deleted successfully, False otherwise
    """
    if not configure_cloudinary():
        print("Warning: Cloudinary not configured, cannot delete video")
        return False
    
    try:
        # Delete from Cloudinary with video resource type
        result = cloudinary.uploader.destroy(public_id, resource_type="video")
        
        if result.get('result') == 'ok':
            print(f"Successfully deleted video: {public_id}")
            return True
        else:
            print(f"Failed to delete video: {result}")
            return False
    except Exception as e:
        print(f"Error deleting video from Cloudinary: {e}")
        return False

