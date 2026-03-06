import uuid
import secrets
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import RedirectResponse
from sqlmodel.ext.asyncio.session import AsyncSession

from backend.database import get_session
from backend.config import settings
from backend.api.deps import get_current_user
from backend.models.user import User
from backend.models.email import EmailAccount
from backend.schemas.email import (
    EmailAccountCreate, 
    EmailAccountUpdate, 
    EmailAccountResponse,
    EmailPreferenceUpdate
)
from backend.services.email_account_service import EmailAccountService
from backend.services.integrations.google import GoogleAPIClient, GoogleConfig

router = APIRouter(prefix="/api/email", tags=["email"])


@router.get("/accounts", response_model=List[EmailAccountResponse])
async def list_email_accounts(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """List all email accounts accessible to the current user."""
    service = EmailAccountService(session)
    return await service.list_accounts(current_user.current_org_id, current_user.id)


@router.post("/accounts", response_model=EmailAccountResponse, status_code=status.HTTP_201_CREATED)
async def create_email_account(
    account_data: EmailAccountCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Connect a new email account."""
    service = EmailAccountService(session)
    return await service.create_account(current_user.current_org_id, current_user.id, account_data)


@router.get("/accounts/{account_id}", response_model=EmailAccountResponse)
async def get_email_account(
    account_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Get details of a specific email account."""
    service = EmailAccountService(session)
    return await service.get_account(current_user.current_org_id, account_id)


@router.patch("/accounts/{account_id}", response_model=EmailAccountResponse)
async def update_email_account(
    account_id: uuid.UUID,
    account_data: EmailAccountUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Update an existing email account."""
    service = EmailAccountService(session)
    return await service.update_account(current_user.current_org_id, account_id, account_data)


@router.delete("/accounts/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_email_account(
    account_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Disconnect an email account."""
    service = EmailAccountService(session)
    await service.delete_account(current_user.current_org_id, account_id)


@router.get("/preference")
async def get_email_preference(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Get the user's preferred email account for the current organization."""
    service = EmailAccountService(session)
    pref = await service.get_preference(current_user.id, current_user.current_org_id)
    return {"preferred_account_id": pref.preferred_account_id if pref else None}


@router.post("/preference")
async def set_email_preference(
    pref_data: EmailPreferenceUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Set the user's preferred email account."""
    service = EmailAccountService(session)
    await service.set_preference(
        current_user.id, 
        current_user.current_org_id, 
        pref_data.preferred_account_id
    )
    return {"message": "Email preference updated"}


# =============================================================================
# GOOGLE OAUTH
# =============================================================================

@router.get("/auth/google/url")
async def get_google_auth_url(
    is_org_shared: bool = Query(default=False),
    current_user: User = Depends(get_current_user)
):
    """Generate Google OAuth URL."""
    config = GoogleConfig(
        client_id=settings.GOOGLE_CLIENT_ID,
        client_secret=settings.GOOGLE_CLIENT_SECRET,
        redirect_uri=f"{settings.BACKEND_URL}/api/email/auth/google/callback"
    )
    
    if not config.client_id:
        raise HTTPException(status_code=400, detail="Google OAuth not configured")
        
    # State stores: user_id:is_org_shared:random
    state = f"{current_user.id}:{is_org_shared}:{secrets.token_urlsafe(16)}"
    
    client = GoogleAPIClient()
    return {"url": client.get_auth_url(config, state)}


@router.get("/auth/google/callback")
async def google_auth_callback(
    code: str,
    state: str,
    session: AsyncSession = Depends(get_session)
):
    """Handle Google OAuth callback."""
    # 1. Parse state
    # Format: user_id:is_org_shared:random:verifier
    try:
        parts = state.split(':')
        user_id = parts[0]
        is_org_shared_str = parts[1]
        is_org_shared = is_org_shared_str.lower() == "true"
        code_verifier = parts[3]
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid state")
        
    # 2. Exchange code for token
    config = GoogleConfig(
        client_id=settings.GOOGLE_CLIENT_ID,
        client_secret=settings.GOOGLE_CLIENT_SECRET,
        redirect_uri=f"{settings.BACKEND_URL}/api/email/auth/google/callback"
    )
    
    client = GoogleAPIClient()
    token_resp = client.fetch_token(config, code, code_verifier)
    
    # 3. Get user info
    email, name = client.get_user_info(token_resp)
    
    # 4. Save account
    user = await session.get(User, uuid.UUID(user_id))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    # Check if account already exists
    from sqlmodel import select
    query = select(EmailAccount).where(
        EmailAccount.email == email,
        EmailAccount.org_id == user.current_org_id
    )
    result = await session.exec(query)
    existing = result.first()
    
    if existing:
        account = existing
    else:
        account = EmailAccount(
            email=email,
            org_id=user.current_org_id,
            user_id=user.id if not is_org_shared else None,
            provider="google",
            is_org_shared=is_org_shared
        )
        
    account.sender_name = name
    account.access_token = token_resp['access_token']
    account.refresh_token = token_resp.get('refresh_token')
    account.token_expires_at = token_resp.get('expires_at')
    
    session.add(account)
    await session.commit()
    
    # Redirect to frontend settings
    return RedirectResponse(url=f"{settings.FRONTEND_URL}/settings/email?connected=google")

