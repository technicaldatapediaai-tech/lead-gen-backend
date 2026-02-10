"""
Campaign repository.
"""
import uuid
from typing import Optional, List
from datetime import datetime

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy import func

from backend.models.campaign import Campaign
from backend.repositories.base import BaseRepository


class CampaignRepository(BaseRepository[Campaign]):
    """Repository for Campaign operations."""
    
    def __init__(self, session: AsyncSession):
        super().__init__(Campaign, session)
    
    async def update_status(self, campaign_id: uuid.UUID, status: str) -> Optional[Campaign]:
        """Update campaign status with appropriate timestamps."""
        campaign = await self.get(campaign_id)
        if not campaign:
            return None
        
        campaign.status = status
        campaign.updated_at = datetime.utcnow()
        
        # Set appropriate timestamp based on status
        if status == "active":
            if not campaign.started_at:
                campaign.started_at = datetime.utcnow()
            campaign.paused_at = None
            campaign.last_resumed_at = datetime.utcnow()
        elif status == "paused":
            campaign.paused_at = datetime.utcnow()
        elif status == "completed":
            campaign.completed_at = datetime.utcnow()
        
        self.session.add(campaign)
        await self.session.commit()
        await self.session.refresh(campaign)
        return campaign
    
    async def increment_leads_count(self, campaign_id: uuid.UUID, count: int = 1) -> bool:
        """Increment leads count for a campaign."""
        campaign = await self.get(campaign_id)
        if campaign:
            campaign.leads_count += count
            campaign.updated_at = datetime.utcnow()
            self.session.add(campaign)
            await self.session.commit()
            return True
        return False
    
    async def get_active(self, org_id: uuid.UUID) -> List[Campaign]:
        """Get all active campaigns for an organization."""
        query = select(Campaign).where(
            Campaign.org_id == org_id,
            Campaign.status == "active"
        )
        result = await self.session.exec(query)
        return result.all()
    
    async def get_stats(self, campaign_id: uuid.UUID) -> dict:
        """Get statistics for a specific campaign."""
        campaign = await self.get(campaign_id)
        if not campaign:
            return {}
        
        return {
            "campaign_id": campaign_id,
            "leads_count": campaign.leads_count,
            "qualified_leads_count": campaign.qualified_leads_count,
            "contacted_count": campaign.contacted_count,
            "replied_count": campaign.replied_count,
            "status": campaign.status,
            "started_at": campaign.started_at,
            "completed_at": campaign.completed_at
        }
    
    async def count_by_status(self, org_id: uuid.UUID, status: str) -> int:
        """Count campaigns by status."""
        return await self.count(org_id, {"status": status})

    async def get_global_stats(self, org_id: uuid.UUID) -> dict:
        """Get aggregated stats across all campaigns for the organization."""
        # Active campaigns count
        active_count = await self.count(org_id, {"status": "active"})
        
        # Total metrics (SUM)
        query = select(
            func.sum(Campaign.contacted_count),
            func.sum(Campaign.replied_count),
            func.sum(Campaign.leads_count)
        ).where(Campaign.org_id == org_id)
        
        result = await self.session.exec(query)
        contacted, replied, total_leads = result.one()
        
        contacted = contacted or 0
        replied = replied or 0
        total_leads = total_leads or 0
        
        # Reply Rate
        avg_reply_rate = round((replied / contacted * 100), 1) if contacted > 0 else 0
        
        # Channel counts
        # Map DB types to Frontend labels: 'social'->LinkedIn, 'email'->Email, 'ai_call'->AI Call
        linkedin_count = await self.count(org_id, {"status": "active", "type": "social"})
        linkedin_running = await self.count(org_id, {"status": "running", "type": "social"})
        
        email_count = await self.count(org_id, {"status": "active", "type": "email"})
        email_running = await self.count(org_id, {"status": "running", "type": "email"})
        
        call_count = await self.count(org_id, {"status": "active", "type": "ai_call"})
        call_running = await self.count(org_id, {"status": "running", "type": "ai_call"})
        
        return {
            "active_campaigns": active_count,
            "total_contacted": contacted,
            "avg_reply_rate": avg_reply_rate,
            "meetings_booked": int(replied * 0.3), # Estimate for now
            "total_leads": total_leads,
            "channels": {
                "linkedin": linkedin_count + linkedin_running,
                "email": email_count + email_running,
                "ai_call": call_count + call_running
            }
        }
