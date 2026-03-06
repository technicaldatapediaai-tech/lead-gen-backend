from typing import Optional
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, EmailStr


class EmailAccountBase(BaseModel):
    email: EmailStr
    sender_name: Optional[str] = None
    provider: str = "custom"
    
    smtp_host: Optional[str] = None
    smtp_port: int = 587
    smtp_user: Optional[str] = None
    
    imap_host: Optional[str] = None
    imap_port: int = 993
    imap_user: Optional[str] = None
    
    is_active: bool = True
    is_org_shared: bool = False


class EmailAccountCreate(EmailAccountBase):
    smtp_password: Optional[str] = None
    imap_password: Optional[str] = None


class EmailAccountUpdate(BaseModel):
    sender_name: Optional[str] = None
    smtp_host: Optional[str] = None
    smtp_port: Optional[int] = None
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None
    
    imap_host: Optional[str] = None
    imap_port: Optional[int] = None
    imap_user: Optional[str] = None
    imap_password: Optional[str] = None
    
    is_active: Optional[bool] = None
    is_org_shared: Optional[bool] = None


class EmailAccountResponse(EmailAccountBase):
    id: UUID
    org_id: UUID
    user_id: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class EmailPreferenceUpdate(BaseModel):
    preferred_account_id: Optional[UUID] = None
