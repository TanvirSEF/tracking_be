from fastapi import APIRouter, HTTPException, status, Depends, File, UploadFile, Form
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional, List

import models
import schemas
import crud
import auth_utils as auth
import cloudinary_utils
from beanie import PydanticObjectId

router = APIRouter()
security = HTTPBearer()

# ==================== Authentication Dependencies ====================

async def get_current_admin_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Dependency to get current admin user"""
    token = credentials.credentials
    user = await auth.get_current_user(token)
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return user

async def get_current_affiliate_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Dependency to get current affiliate user"""
    token = credentials.credentials
    user = await auth.get_current_user(token)
    affiliate = await crud.get_affiliate_by_user(user.id)
    if not affiliate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Affiliate profile not found"
        )
    return affiliate

async def get_current_member_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Dependency to get current member/referral user"""
    token = credentials.credentials
    referral = await auth.get_current_referral(token)
    return referral

# ==================== ADMIN ENDPOINTS ====================

@router.get("/admin/tickets", response_model=List[schemas.TicketResponse])
async def get_admin_tickets(
    status: Optional[str] = None,
    priority: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    current_user: models.User = Depends(get_current_admin_user)
):
    """Get all affiliate->admin tickets (Admin view)"""
    # Convert string to enum if provided
    status_enum = None
    priority_enum = None
    
    if status:
        try:
            status_enum = models.TicketStatus(status)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status. Must be one of: open, ongoing, closed"
            )
    
    if priority:
        try:
            priority_enum = models.TicketPriority(priority)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid priority. Must be one of: average, medium, high"
            )
    
    tickets = await crud.get_tickets_for_admin(
        status=status_enum,
        priority=priority_enum,
        page=page,
        page_size=page_size
    )
    
    return tickets

@router.get("/admin/tickets/{ticket_id}", response_model=schemas.TicketWithRepliesResponse)
async def get_admin_ticket_by_id(
    ticket_id: str,
    current_user: models.User = Depends(get_current_admin_user)
):
    """Get specific ticket with all replies (Admin view)"""
    ticket = await crud.get_ticket_with_replies(ticket_id)
    
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found"
        )
    
    # Admin can view any affiliate->admin ticket
    if ticket['ticket_type'] != models.TicketType.AFFILIATE_TO_ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    return ticket

@router.post("/admin/tickets/{ticket_id}/reply", response_model=schemas.TicketReplyResponse)
async def admin_reply_to_ticket(
    ticket_id: str,
    message: str = Form(...),
    image: Optional[UploadFile] = File(None),
    current_user: models.User = Depends(get_current_admin_user)
):
    """Admin replies to an affiliate ticket"""
    # Get ticket to verify it exists and is correct type
    ticket = await crud.get_ticket_by_id(ticket_id)
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found"
        )
    
    if ticket.ticket_type != models.TicketType.AFFILIATE_TO_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot reply to this ticket type"
        )
    
    # Upload image if provided
    image_url = None
    if image:
        image_url = await cloudinary_utils.upload_reply_image(image)
    
    # Add reply
    reply = await crud.add_ticket_reply(
        ticket_id=ticket_id,
        sender_id=current_user.id,
        sender_email=current_user.email,
        sender_name="Admin",
        sender_type="admin",
        message=message,
        image_url=image_url
    )
    
    if not reply:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add reply"
        )
    
    return schemas.TicketReplyResponse(
        id=str(reply.id),
        ticket_id=str(reply.ticket_id),
        sender_id=str(reply.sender_id),
        sender_email=reply.sender_email,
        sender_name=reply.sender_name,
        sender_type=reply.sender_type,
        message=reply.message,
        image_url=reply.image_url,
        created_at=reply.created_at
    )

@router.patch("/admin/tickets/{ticket_id}", response_model=schemas.TicketResponse)
async def admin_update_ticket(
    ticket_id: str,
    update_data: schemas.TicketUpdateRequest,
    current_user: models.User = Depends(get_current_admin_user)
):
    """Admin updates ticket status or priority"""
    # Get ticket to verify access
    ticket = await crud.get_ticket_by_id(ticket_id)
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found"
        )
    
    if ticket.ticket_type != models.TicketType.AFFILIATE_TO_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot update this ticket type"
        )
    
    # Convert enum strings to actual enums
    status_enum = None
    priority_enum = None
    
    if update_data.status:
        status_enum = models.TicketStatus(update_data.status.value)
    if update_data.priority:
        priority_enum = models.TicketPriority(update_data.priority.value)
    
    # Update ticket
    updated_ticket = await crud.update_ticket_status_priority(
        ticket_id=ticket_id,
        status=status_enum,
        priority=priority_enum
    )
    
    if not updated_ticket:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update ticket"
        )
    
    # Get reply count
    reply_count = await models.TicketReply.find(
        models.TicketReply.ticket_id == updated_ticket.id
    ).count()
    
    return schemas.TicketResponse(
        id=str(updated_ticket.id),
        ticket_type=updated_ticket.ticket_type.value,
        creator_id=str(updated_ticket.creator_id),
        creator_email=updated_ticket.creator_email,
        creator_name=updated_ticket.creator_name,
        assigned_to_id=str(updated_ticket.assigned_to_id) if updated_ticket.assigned_to_id else None,
        subject=updated_ticket.subject,
        message=updated_ticket.message,
        priority=updated_ticket.priority.value,
        status=updated_ticket.status.value,
        image_url=updated_ticket.image_url,
        created_at=updated_ticket.created_at,
        updated_at=updated_ticket.updated_at,
        last_reply_at=updated_ticket.last_reply_at,
        reply_count=reply_count
    )

@router.get("/admin/tickets/stats/dashboard", response_model=schemas.TicketStatsResponse)
async def get_admin_ticket_stats(
    current_user: models.User = Depends(get_current_admin_user)
):
    """Get ticket statistics for admin dashboard"""
    stats = await crud.get_ticket_stats_for_admin()
    return stats

# ==================== AFFILIATE ENDPOINTS ====================

# Affiliate's own tickets TO admin

@router.post("/affiliate/tickets", response_model=schemas.TicketResponse)
async def create_affiliate_ticket(
    subject: str = Form(...),
    message: str = Form(...),
    priority: str = Form(...),
    name: str = Form(...),
    email: str = Form(...),
    image: Optional[UploadFile] = File(None),
    current_affiliate: models.Affiliate = Depends(get_current_affiliate_user)
):
    """Affiliate creates a ticket to admin"""
    # Validate priority
    try:
        priority_enum = models.TicketPriority(priority)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid priority. Must be one of: average, medium, high"
        )
    
    # Upload image if provided
    image_url = None
    if image:
        image_url = await cloudinary_utils.upload_ticket_image(image)
    
    # Create ticket
    ticket = await crud.create_support_ticket(
        ticket_type=models.TicketType.AFFILIATE_TO_ADMIN,
        creator_id=current_affiliate.id,
        creator_email=email,
        creator_name=name,
        subject=subject,
        message=message,
        priority=priority_enum,
        image_url=image_url,
        assigned_to_id=None  # Any admin can respond
    )
    
    # Get reply count (will be 0 initially)
    reply_count = 0
    
    return schemas.TicketResponse(
        id=str(ticket.id),
        ticket_type=ticket.ticket_type.value,
        creator_id=str(ticket.creator_id),
        creator_email=ticket.creator_email,
        creator_name=ticket.creator_name,
        assigned_to_id=None,
        subject=ticket.subject,
        message=ticket.message,
        priority=ticket.priority.value,
        status=ticket.status.value,
        image_url=ticket.image_url,
        created_at=ticket.created_at,
        updated_at=ticket.updated_at,
        last_reply_at=ticket.last_reply_at,
        reply_count=reply_count
    )

@router.get("/affiliate/tickets", response_model=List[schemas.TicketResponse])
async def get_affiliate_tickets(
    status: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    current_affiliate: models.Affiliate = Depends(get_current_affiliate_user)
):
    """Get affiliate's own tickets to admin"""
    # Convert string to enum if provided
    status_enum = None
    if status:
        try:
            status_enum = models.TicketStatus(status)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status. Must be one of: open, ongoing, closed"
            )
    
    tickets = await crud.get_tickets_by_affiliate(
        affiliate_id=str(current_affiliate.id),
        status=status_enum,
        page=page,
        page_size=page_size
    )
    
    return tickets

@router.get("/affiliate/tickets/{ticket_id}", response_model=schemas.TicketWithRepliesResponse)
async def get_affiliate_ticket_by_id(
    ticket_id: str,
    current_affiliate: models.Affiliate = Depends(get_current_affiliate_user)
):
    """Get specific ticket with all replies"""
    ticket = await crud.get_ticket_with_replies(ticket_id)
    
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found"
        )
    
    # Verify this ticket belongs to the affiliate
    if ticket['creator_id'] != str(current_affiliate.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    return ticket

@router.post("/affiliate/tickets/{ticket_id}/reply", response_model=schemas.TicketReplyResponse)
async def affiliate_reply_to_admin_ticket(
    ticket_id: str,
    message: str = Form(...),
    image: Optional[UploadFile] = File(None),
    current_affiliate: models.Affiliate = Depends(get_current_affiliate_user)
):
    """Affiliate replies to their ticket to admin"""
    # Get ticket to verify it exists and belongs to this affiliate
    ticket = await crud.get_ticket_by_id(ticket_id)
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found"
        )
    
    if str(ticket.creator_id) != str(current_affiliate.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    # Upload image if provided
    image_url = None
    if image:
        image_url = await cloudinary_utils.upload_reply_image(image)
    
    # Get user email for affiliate
    user = await models.User.find_one(models.User.id == current_affiliate.user_id)
    
    # Add reply
    reply = await crud.add_ticket_reply(
        ticket_id=ticket_id,
        sender_id=current_affiliate.id,
        sender_email=user.email if user else ticket.creator_email,
        sender_name=current_affiliate.name,
        sender_type="affiliate",
        message=message,
        image_url=image_url
    )
    
    if not reply:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add reply"
        )
    
    return schemas.TicketReplyResponse(
        id=str(reply.id),
        ticket_id=str(reply.ticket_id),
        sender_id=str(reply.sender_id),
        sender_email=reply.sender_email,
        sender_name=reply.sender_name,
        sender_type=reply.sender_type,
        message=reply.message,
        image_url=reply.image_url,
        created_at=reply.created_at
    )

# Member tickets TO this affiliate

@router.get("/affiliate/member-tickets", response_model=List[schemas.TicketResponse])
async def get_member_tickets_for_affiliate(
    status: Optional[str] = None,
    priority: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    current_affiliate: models.Affiliate = Depends(get_current_affiliate_user)
):
    """Get tickets from members to this affiliate"""
    # Convert string to enum if provided
    status_enum = None
    priority_enum = None
    
    if status:
        try:
            status_enum = models.TicketStatus(status)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status. Must be one of: open, ongoing, closed"
            )
    
    if priority:
        try:
            priority_enum = models.TicketPriority(priority)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid priority. Must be one of: average, medium, high"
            )
    
    tickets = await crud.get_member_tickets_for_affiliate(
        affiliate_id=str(current_affiliate.id),
        status=status_enum,
        priority=priority_enum,
        page=page,
        page_size=page_size
    )
    
    return tickets

@router.get("/affiliate/member-tickets/{ticket_id}", response_model=schemas.TicketWithRepliesResponse)
async def get_member_ticket_by_id(
    ticket_id: str,
    current_affiliate: models.Affiliate = Depends(get_current_affiliate_user)
):
    """Get specific member ticket with all replies"""
    ticket = await crud.get_ticket_with_replies(ticket_id)
    
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found"
        )
    
    # Verify this ticket is assigned to this affiliate
    if ticket.get('assigned_to_id') != str(current_affiliate.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    return ticket

@router.post("/affiliate/member-tickets/{ticket_id}/reply", response_model=schemas.TicketReplyResponse)
async def affiliate_reply_to_member_ticket(
    ticket_id: str,
    message: str = Form(...),
    image: Optional[UploadFile] = File(None),
    current_affiliate: models.Affiliate = Depends(get_current_affiliate_user)
):
    """Affiliate replies to a member's ticket"""
    # Get ticket to verify it exists and is assigned to this affiliate
    ticket = await crud.get_ticket_by_id(ticket_id)
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found"
        )
    
    if not ticket.assigned_to_id or str(ticket.assigned_to_id) != str(current_affiliate.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    # Upload image if provided
    image_url = None
    if image:
        image_url = await cloudinary_utils.upload_reply_image(image)
    
    # Get user email for affiliate
    user = await models.User.find_one(models.User.id == current_affiliate.user_id)
    
    # Add reply
    reply = await crud.add_ticket_reply(
        ticket_id=ticket_id,
        sender_id=current_affiliate.id,
        sender_email=user.email if user else current_affiliate.name,
        sender_name=current_affiliate.name,
        sender_type="affiliate",
        message=message,
        image_url=image_url
    )
    
    if not reply:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add reply"
        )
    
    return schemas.TicketReplyResponse(
        id=str(reply.id),
        ticket_id=str(reply.ticket_id),
        sender_id=str(reply.sender_id),
        sender_email=reply.sender_email,
        sender_name=reply.sender_name,
        sender_type=reply.sender_type,
        message=reply.message,
        image_url=reply.image_url,
        created_at=reply.created_at
    )

@router.patch("/affiliate/member-tickets/{ticket_id}", response_model=schemas.TicketResponse)
async def affiliate_update_member_ticket(
    ticket_id: str,
    update_data: schemas.TicketUpdateRequest,
    current_affiliate: models.Affiliate = Depends(get_current_affiliate_user)
):
    """Affiliate updates member ticket status or priority"""
    # Get ticket to verify access
    ticket = await crud.get_ticket_by_id(ticket_id)
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found"
        )
    
    if not ticket.assigned_to_id or str(ticket.assigned_to_id) != str(current_affiliate.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    # Convert enum strings to actual enums
    status_enum = None
    priority_enum = None
    
    if update_data.status:
        status_enum = models.TicketStatus(update_data.status.value)
    if update_data.priority:
        priority_enum = models.TicketPriority(update_data.priority.value)
    
    # Update ticket
    updated_ticket = await crud.update_ticket_status_priority(
        ticket_id=ticket_id,
        status=status_enum,
        priority=priority_enum
    )
    
    if not updated_ticket:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update ticket"
        )
    
    # Get reply count
    reply_count = await models.TicketReply.find(
        models.TicketReply.ticket_id == updated_ticket.id
    ).count()
    
    return schemas.TicketResponse(
        id=str(updated_ticket.id),
        ticket_type=updated_ticket.ticket_type.value,
        creator_id=str(updated_ticket.creator_id),
        creator_email=updated_ticket.creator_email,
        creator_name=updated_ticket.creator_name,
        assigned_to_id=str(updated_ticket.assigned_to_id) if updated_ticket.assigned_to_id else None,
        subject=updated_ticket.subject,
        message=updated_ticket.message,
        priority=updated_ticket.priority.value,
        status=updated_ticket.status.value,
        image_url=updated_ticket.image_url,
        created_at=updated_ticket.created_at,
        updated_at=updated_ticket.updated_at,
        last_reply_at=updated_ticket.last_reply_at,
        reply_count=reply_count
    )

@router.get("/affiliate/tickets/stats/dashboard")
async def get_affiliate_ticket_stats(
    current_affiliate: models.Affiliate = Depends(get_current_affiliate_user)
):
    """Get ticket statistics for affiliate dashboard"""
    stats = await crud.get_ticket_stats_for_affiliate(str(current_affiliate.id))
    return stats

# ==================== MEMBER/REFERRAL ENDPOINTS ====================

@router.post("/referral/tickets", response_model=schemas.TicketResponse)
async def create_member_ticket(
    subject: str = Form(...),
    message: str = Form(...),
    priority: str = Form(...),
    name: str = Form(...),
    email: str = Form(...),
    image: Optional[UploadFile] = File(None),
    current_member: models.Referral = Depends(get_current_member_user)
):
    """Member creates a ticket to their affiliate"""
    # Validate priority
    try:
        priority_enum = models.TicketPriority(priority)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid priority. Must be one of: average, medium, high"
        )
    
    # Upload image if provided
    image_url = None
    if image:
        image_url = await cloudinary_utils.upload_ticket_image(image)
    
    # Create ticket assigned to their affiliate
    ticket = await crud.create_support_ticket(
        ticket_type=models.TicketType.MEMBER_TO_AFFILIATE,
        creator_id=current_member.id,
        creator_email=email,
        creator_name=name,
        subject=subject,
        message=message,
        priority=priority_enum,
        image_url=image_url,
        assigned_to_id=current_member.affiliate_id  # Assigned to their affiliate
    )
    
    # Get reply count (will be 0 initially)
    reply_count = 0
    
    return schemas.TicketResponse(
        id=str(ticket.id),
        ticket_type=ticket.ticket_type.value,
        creator_id=str(ticket.creator_id),
        creator_email=ticket.creator_email,
        creator_name=ticket.creator_name,
        assigned_to_id=str(ticket.assigned_to_id) if ticket.assigned_to_id else None,
        subject=ticket.subject,
        message=ticket.message,
        priority=ticket.priority.value,
        status=ticket.status.value,
        image_url=ticket.image_url,
        created_at=ticket.created_at,
        updated_at=ticket.updated_at,
        last_reply_at=ticket.last_reply_at,
        reply_count=reply_count
    )

@router.get("/referral/tickets", response_model=List[schemas.TicketResponse])
async def get_member_tickets(
    status: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    current_member: models.Referral = Depends(get_current_member_user)
):
    """Get member's own tickets to their affiliate"""
    # Convert string to enum if provided
    status_enum = None
    if status:
        try:
            status_enum = models.TicketStatus(status)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status. Must be one of: open, ongoing, closed"
            )
    
    tickets = await crud.get_tickets_by_member(
        member_id=str(current_member.id),
        status=status_enum,
        page=page,
        page_size=page_size
    )
    
    return tickets

@router.get("/referral/tickets/{ticket_id}", response_model=schemas.TicketWithRepliesResponse)
async def get_member_ticket_by_id(
    ticket_id: str,
    current_member: models.Referral = Depends(get_current_member_user)
):
    """Get specific ticket with all replies"""
    ticket = await crud.get_ticket_with_replies(ticket_id)
    
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found"
        )
    
    # Verify this ticket belongs to the member
    if ticket['creator_id'] != str(current_member.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    return ticket

@router.post("/referral/tickets/{ticket_id}/reply", response_model=schemas.TicketReplyResponse)
async def member_reply_to_ticket(
    ticket_id: str,
    message: str = Form(...),
    image: Optional[UploadFile] = File(None),
    current_member: models.Referral = Depends(get_current_member_user)
):
    """Member replies to their ticket to affiliate"""
    # Get ticket to verify it exists and belongs to this member
    ticket = await crud.get_ticket_by_id(ticket_id)
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found"
        )
    
    if str(ticket.creator_id) != str(current_member.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    # Upload image if provided
    image_url = None
    if image:
        image_url = await cloudinary_utils.upload_reply_image(image)
    
    # Add reply
    reply = await crud.add_ticket_reply(
        ticket_id=ticket_id,
        sender_id=current_member.id,
        sender_email=current_member.email,
        sender_name=current_member.full_name,
        sender_type="member",
        message=message,
        image_url=image_url
    )
    
    if not reply:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add reply"
        )
    
    return schemas.TicketReplyResponse(
        id=str(reply.id),
        ticket_id=str(reply.ticket_id),
        sender_id=str(reply.sender_id),
        sender_email=reply.sender_email,
        sender_name=reply.sender_name,
        sender_type=reply.sender_type,
        message=reply.message,
        image_url=reply.image_url,
        created_at=reply.created_at
    )

