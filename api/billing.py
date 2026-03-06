from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from datetime import datetime, timedelta

from backend.database import get_session
from backend.api.deps import get_current_user
from backend.models.user import User
from backend.models.billing import Invoice, SubscriptionInfo

router = APIRouter(prefix="/api/billing", tags=["billing"])

@router.get("/ping")
async def ping():
    return {"message": "Billing router is reachable", "status": "online"}

@router.get("/subscription")
async def get_subscription_info(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Get current organization's subscription info."""
    if not current_user.current_org_id:
        raise HTTPException(status_code=400, detail="No active organization")
    
    query = select(SubscriptionInfo).where(SubscriptionInfo.org_id == current_user.current_org_id)
    result = await session.exec(query)
    sub = result.first()
    
    if not sub:
        # Create default sub info for the org (Starting as a Free Plan)
        sub = SubscriptionInfo(
            org_id=current_user.current_org_id,
            plan_name="Free Plan",
            status="active",
            billing_cycle="monthly",
            next_billing_date=datetime.utcnow() + timedelta(days=30),
            current_period_start=datetime.utcnow(),
            current_period_end=datetime.utcnow() + timedelta(days=30),
            payment_method_summary="No card on file",
            total_spent=0.00
        )
        session.add(sub)
        await session.commit()
        await session.refresh(sub)
    
    return sub

@router.get("/invoices")
async def get_invoices(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Get current organization's invoice history."""
    if not current_user.current_org_id:
        raise HTTPException(status_code=400, detail="No active organization")
    
    query = select(Invoice).where(Invoice.org_id == current_user.current_org_id).order_by(Invoice.invoice_date.desc())
    result = await session.exec(query)
    invoices = result.all()
    
    return invoices
