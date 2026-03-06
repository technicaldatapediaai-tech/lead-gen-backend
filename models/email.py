"""
Email Account model for storing SMTP/IMAP credentials.
Supports personal and organizational email accounts.
"""
import uuid
from datetime import datetime
from typing import Optional

from sqlmodel import SQLModel, Field


class EmailAccount(SQLModel, table=True):
    """
    Credentials for an email account to send/receive outreach.
    """
    __tablename__ = "email_account"
    
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    org_id: uuid.UUID = Field(foreign_key="organization.id", index=True)
    user_id: Optional[uuid.UUID] = Field(default=None, foreign_key="user.id", index=True)
    
    # Email identity
    email: str = Field(index=True)
    sender_name: Optional[str] = None
    provider: str = Field(default="custom")  # google, microsoft, custom
    
    # SMTP Settings (Sending)
    smtp_host: Optional[str] = None
    smtp_port: int = 587
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None
    
    # IMAP Settings (Receiving/Tracking)
    imap_host: Optional[str] = None
    imap_port: int = 993
    imap_user: Optional[str] = None
    imap_password: Optional[str] = None

    # OAuth Settings (for Google/Microsoft)
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    token_expires_at: Optional[datetime] = None

    # Status/Sharing
    is_active: bool = Field(default=True)
    is_org_shared: bool = Field(default=False)
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class EmailPreference(SQLModel, table=True):
    """
    User preference for which email account to use in a specific organization.
    """
    __tablename__ = "email_preference"
    
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="user.id", index=True)
    org_id: uuid.UUID = Field(foreign_key="organization.id", index=True)
    
    # Preferred account
    preferred_account_id: Optional[uuid.UUID] = Field(default=None, foreign_key="email_account.id")
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
