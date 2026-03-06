import uuid
from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field

class Invoice(SQLModel, table=True):
    """
    Invoice model for billing history.
    """
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    org_id: uuid.UUID = Field(index=True)
    invoice_number: str = Field(unique=True, index=True)
    amount: float
    currency: str = Field(default="USD")
    status: str = Field(default="paid") # paid, open, void, uncollectible
    plan_name: str
    payment_method: str # e.g. Visa ending in 4242
    invoice_date: datetime = Field(default_factory=datetime.utcnow)
    pdf_url: Optional[str] = None
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class SubscriptionInfo(SQLModel, table=True):
    """
    Subscription info for an organization.
    """
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    org_id: uuid.UUID = Field(unique=True, index=True)
    plan_name: str = Field(default="Free")
    status: str = Field(default="active")
    billing_cycle: str = Field(default="monthly")
    next_billing_date: Optional[datetime] = None
    current_period_start: datetime = Field(default_factory=datetime.utcnow)
    current_period_end: Optional[datetime] = None
    cancel_at_period_end: bool = Field(default=False)
    
    payment_method_summary: Optional[str] = None # e.g. Visa 4242
    total_spent: float = Field(default=0.0)
    
    updated_at: datetime = Field(default_factory=datetime.utcnow)
