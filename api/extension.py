"""
Extension API routes.
Endpoints for Chrome extension to fetch and update outreach messages.
"""
import uuid
import secrets
from datetime import datetime, timedelta
from typing import Optional, List
from fastapi import APIRouter, Depends, Query
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from pydantic import BaseModel

from backend.database import get_session
from backend.api.deps import get_current_user
from backend.models.user import User
from backend.models.outreach import OutreachMessage
from backend.models.lead import Lead


router = APIRouter(prefix="/api/extension", tags=["extension"])


# =============================================================================
# SCHEMAS
# =============================================================================

class ExtensionTokenResponse(BaseModel):
    """Extension authentication token."""
    token: str
    expires_in: int
    user_email: str
    org_id: str


class QueuedMessage(BaseModel):
    """Message in the extension queue."""
    id: str
    lead_name: str
    lead_company: Optional[str]
    linkedin_url: str
    message: str
    message_type: str  # inmail or connection
    channel: str
    template_name: Optional[str]
    created_at: str


class MessageQueueResponse(BaseModel):
    """List of queued messages for extension."""
    messages: List[QueuedMessage]
    count: int


class StatusUpdateRequest(BaseModel):
    """Request to update message status from extension."""
    status: str  # sending, sent, failed
    error_message: Optional[str] = None
    linkedin_message_id: Optional[str] = None
    extension_session_id: Optional[str] = None


class BatchStatusUpdate(BaseModel):
    """Batch update multiple messages."""
    message_id: str
    status: str
    error_message: Optional[str] = None

class LeadSyncRequest(BaseModel):
    """Data received from extension to sync a lead."""
    name: str
    url: str
    headline: Optional[str] = None
    company: Optional[str] = None
    location: Optional[str] = None


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.post("/auth", response_model=ExtensionTokenResponse)
async def generate_extension_token(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Generate a token for the Chrome extension.
    Extension uses this token to authenticate API calls.
    
    Token is valid for 30 days.
    """
    # Generate a long-lived JWT for the extension
    from backend.core.security import create_access_token
    
    expires_delta = timedelta(days=30)
    token = create_access_token(
        subject=str(current_user.id),
        expires_delta=expires_delta
    )
    
    return ExtensionTokenResponse(
        token=token,
        expires_in=30 * 24 * 60 * 60,  # 30 days in seconds
        user_email=current_user.email,
        org_id=str(current_user.current_org_id)
    )


@router.get("/queue", response_model=MessageQueueResponse)
async def get_message_queue(
    limit: int = Query(default=20, le=100),
    channel: str = Query(default="linkedin"),
    include_failed: bool = Query(default=False),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Get pending messages for the extension to send.
    Returns messages with status 'queued', 'pending', or optionally 'failed' that are ready to send.
    """
    # Build status filter
    statuses = ["pending", "queued"]
    if include_failed:
        statuses.append("failed")
    
    # AUTO-RESET stuck messages
    # If a message is 'sending' but hasn't been updated in 15 minutes, it's probably stuck
    stuck_limit = datetime.utcnow() - timedelta(minutes=15)
    stuck_query = select(OutreachMessage).where(
        OutreachMessage.org_id == current_user.current_org_id,
        OutreachMessage.status == "sending",
        OutreachMessage.updated_at < stuck_limit
    )
    stuck_result = await session.exec(stuck_query)
    stuck_messages = stuck_result.all()
    for m in stuck_messages:
        m.status = "pending"
        m.error_message = "Auto-reset: Extension timed out while sending"
        session.add(m)
    if stuck_messages:
        await session.commit()

    # Query messages that are queued for extension sending
    query = select(OutreachMessage).where(
        OutreachMessage.org_id == current_user.current_org_id,
        OutreachMessage.channel == channel,
        OutreachMessage.status.in_(statuses),
        OutreachMessage.send_method == "extension"
    ).order_by(OutreachMessage.created_at.asc()).limit(limit)
    
    result = await session.exec(query)
    messages = result.all()
    
    # Enrich with lead data
    queued_messages = []
    for msg in messages:
        # Get lead info
        lead = await session.get(Lead, msg.lead_id)
        if lead:
            url = lead.linkedin_url or msg.linkedin_profile_url or ""
            if url and not url.startswith("http"):
                if url.startswith("www."):
                    url = f"https://{url}"
                elif url.startswith("linkedin.com"):
                    url = f"https://{url}"
                else:
                    url = f"https://www.linkedin.com/{url.lstrip('/')}"
            
            queued_messages.append(QueuedMessage(
                id=str(msg.id),
                lead_name=lead.name,
                lead_company=lead.company,
                linkedin_url=url,
                message=msg.message,
                message_type=getattr(msg, 'message_type', 'inmail') or 'inmail',
                channel=msg.channel,
                template_name=None,
                created_at=msg.created_at.isoformat()
            ))
    
    return MessageQueueResponse(
        messages=queued_messages,
        count=len(queued_messages)
    )


@router.get("/history", response_model=MessageQueueResponse)
async def get_message_history(
    limit: int = Query(default=10, le=50),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Get history of sent or failed messages.
    """
    query = select(OutreachMessage).where(
        OutreachMessage.org_id == current_user.current_org_id,
        OutreachMessage.status.in_(["sent", "failed"]),
        OutreachMessage.send_method == "extension"
    ).order_by(OutreachMessage.updated_at.desc()).limit(limit)
    
    result = await session.exec(query)
    messages = result.all()
    
    history_items = []
    for msg in messages:
        lead = await session.get(Lead, msg.lead_id)
        if lead:
            history_items.append(QueuedMessage(
                id=str(msg.id),
                lead_name=lead.name,
                lead_company=lead.company,
                linkedin_url=lead.linkedin_url or "",
                message=msg.message,
                message_type=getattr(msg, 'message_type', 'inmail') or 'inmail',
                channel=msg.channel,
                template_name=None,
                created_at=msg.updated_at.isoformat()
            ))
    
    return MessageQueueResponse(
        messages=history_items,
        count=len(history_items)
    )


@router.post("/messages/{message_id}/status")
async def update_message_status(
    message_id: uuid.UUID,
    request: StatusUpdateRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Update message status from extension.
    Called when extension sends or fails to send a message.
    """
    # Get message
    message = await session.get(OutreachMessage, message_id)
    if not message:
        return {"error": "Message not found"}
    
    # Verify ownership
    if message.org_id != current_user.current_org_id:
        return {"error": "Access denied"}
    
    # Update status
    message.status = request.status
    message.updated_at = datetime.utcnow()
    
    if request.status == "sent":
        message.sent_at = datetime.utcnow()
    
    if request.error_message:
        message.error_message = request.error_message
        message.retry_count += 1
    
    if request.linkedin_message_id:
        message.linkedin_message_id = request.linkedin_message_id
    
    if request.extension_session_id:
        message.extension_session_id = request.extension_session_id
    
    session.add(message)
    await session.commit()
    
    return {
        "message": f"Status updated to {request.status}",
        "message_id": str(message_id)
    }


@router.post("/messages/batch-status")
async def batch_update_status(
    updates: List[BatchStatusUpdate],
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Batch update multiple message statuses.
    Useful when extension sends multiple messages.
    """
    updated = 0
    errors = []
    
    for update in updates:
        try:
            message = await session.get(OutreachMessage, uuid.UUID(update.message_id))
            if message and message.org_id == current_user.current_org_id:
                message.status = update.status
                message.updated_at = datetime.utcnow()
                if update.status == "sent":
                    message.sent_at = datetime.utcnow()
                if update.error_message:
                    message.error_message = update.error_message
                session.add(message)
                updated += 1
            else:
                errors.append(f"Message {update.message_id} not found or access denied")
        except Exception as e:
            errors.append(f"Error updating {update.message_id}: {str(e)}")
    
    await session.commit()
    
    return {
        "updated": updated,
        "total": len(updates),
        "errors": errors if errors else None
    }


@router.post("/messages/{message_id}/queue")
async def queue_message_for_extension(
    message_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Queue a message for extension sending.
    Changes send_method to 'extension' and status to 'queued'.
    """
    message = await session.get(OutreachMessage, message_id)
    if not message:
        return {"error": "Message not found"}
    
    if message.org_id != current_user.current_org_id:
        return {"error": "Access denied"}
    
    message.send_method = "extension"
    message.status = "queued"
    message.updated_at = datetime.utcnow()
    
    session.add(message)
    await session.commit()
    
    return {
        "message": "Message queued for extension",
        "message_id": str(message_id)
    }


@router.get("/stats")
async def get_extension_stats(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Get extension sending statistics.
    """
    from sqlalchemy import func
    
    # AUTO-RESET stuck messages before reporting stats
    stuck_limit = datetime.utcnow() - timedelta(minutes=15)
    stuck_query = select(OutreachMessage).where(
        OutreachMessage.org_id == current_user.current_org_id,
        OutreachMessage.status == "sending",
        OutreachMessage.updated_at < stuck_limit
    )
    stuck_result = await session.exec(stuck_query)
    stuck_messages = stuck_result.all()
    for m in stuck_messages:
        m.status = "pending"
        session.add(m)
    if stuck_messages:
        await session.commit()

    # Get total counts by status
    query = select(
        OutreachMessage.status,
        func.count(OutreachMessage.id)
    ).where(
        OutreachMessage.org_id == current_user.current_org_id,
        OutreachMessage.send_method == "extension"
    ).group_by(OutreachMessage.status)
    
    result = await session.exec(query)
    stats = {row[0]: row[1] for row in result.all()}
    
    # Get messages sent TODAY specifically
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    today_sent_query = select(func.count(OutreachMessage.id)).where(
        OutreachMessage.org_id == current_user.current_org_id,
        OutreachMessage.send_method == "extension",
        OutreachMessage.status == "sent",
        OutreachMessage.sent_at >= today_start
    )
    today_sent_result = await session.exec(today_sent_query)
    sent_today = today_sent_result.one() or 0
    
    return {
        "queued": stats.get("queued", 0) + stats.get("pending", 0),
        "sending": stats.get("sending", 0),
        "sent": sent_today,  # This maps to "Sent Today" in UI
        "failed": stats.get("failed", 0),
        "total_sent": stats.get("sent", 0),
        "total": sum(stats.values())
    }


class ManualIngestRequest(BaseModel):
    """Request payload for manual data ingestion."""
    url: str
    html_content: Optional[str] = None
    extracted_data: dict

@router.post("/ingest/post")
async def ingest_manual_post(
    request: ManualIngestRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Ingest scraped post data manually from the extension.
    """
    from backend.services.analysis_service import analysis_service
    
    print(f"\n[MANUAL INGEST] Received data for URL: {request.url}")
    print(f"[MANUAL INGEST] Extracted Data Keys: {list(request.extracted_data.keys())}")
    
    try:
        result = await analysis_service.process_manual_data(
            data=request.model_dump(),
            org_id=current_user.current_org_id
        )
        print(f"[MANUAL INGEST] Success! Result: {result}\n")
        return result
    except Exception as e:
        print(f"[MANUAL INGEST] Error: {str(e)}\n")
        return {"success": False, "error": str(e)}

@router.post("/leads/sync")
async def sync_lead_from_extension(
    request: LeadSyncRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """
    Sync a lead profile from LinkedIn directly to the CRM.
    Checks for existing lead by URL before creating.
    """
    # Normalize URL
    normalized_url = request.url.split('?')[0].replace('https://www.', 'https://').rstrip('/')
    
    # Check if lead exists
    query = select(Lead).where(
        Lead.org_id == current_user.current_org_id,
        Lead.linkedin_url.contains(normalized_url)
    )
    result = await session.exec(query)
    existing_lead = result.first()
    
    if existing_lead:
        # Update existing
        existing_lead.name = request.name
        existing_lead.title = request.headline or existing_lead.title
        existing_lead.company = request.company or existing_lead.company
        existing_lead.updated_at = datetime.utcnow()
        session.add(existing_lead)
        await session.commit()
        return {"success": True, "action": "updated", "id": str(existing_lead.id)}
    
    # Create new lead
    new_lead = Lead(
        id=uuid.uuid4(),
        org_id=current_user.current_org_id,
        name=request.name,
        linkedin_url=request.url,
        title=request.headline,
        company=request.company,
        location=request.location,
        status="new",
        source="extension",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    session.add(new_lead)
    await session.commit()
    
    return {"success": True, "action": "created", "id": str(new_lead.id)}
