import uuid
from typing import List, Optional
from datetime import datetime
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from fastapi import HTTPException, status

from backend.models.email import EmailAccount, EmailPreference
from backend.schemas.email import EmailAccountCreate, EmailAccountUpdate


class EmailAccountService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_accounts(self, org_id: uuid.UUID, user_id: Optional[uuid.UUID] = None) -> List[EmailAccount]:
        """List accounts for an organization. If user_id is provided, also list personal accounts."""
        query = select(EmailAccount).where(EmailAccount.org_id == org_id)
        
        # Always include org-shared accounts
        # If user_id is provided, also include their personal accounts
        if user_id:
            query = query.where(
                (EmailAccount.is_org_shared == True) | 
                (EmailAccount.user_id == user_id)
            )
        else:
            query = query.where(EmailAccount.is_org_shared == True)
            
        result = await self.session.exec(query)
        return result.all()

    async def get_account(self, org_id: uuid.UUID, account_id: uuid.UUID) -> EmailAccount:
        """Get a specific account."""
        query = select(EmailAccount).where(
            EmailAccount.id == account_id,
            EmailAccount.org_id == org_id
        )
        result = await self.session.exec(query)
        account = result.first()
        
        if not account:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Email account not found"
            )
        return account

    async def create_account(
        self, 
        org_id: uuid.UUID, 
        user_id: uuid.UUID, 
        data: EmailAccountCreate
    ) -> EmailAccount:
        """Create a new email account."""
        account = EmailAccount(
            **data.model_dump(),
            org_id=org_id,
            user_id=user_id if not data.is_org_shared else None
        )
        self.session.add(account)
        await self.session.commit()
        await self.session.refresh(account)
        return account

    async def update_account(
        self, 
        org_id: uuid.UUID, 
        account_id: uuid.UUID, 
        data: EmailAccountUpdate
    ) -> EmailAccount:
        """Update an email account."""
        account = await self.get_account(org_id, account_id)
        
        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(account, key, value)
            
        account.updated_at = datetime.utcnow()
        self.session.add(account)
        await self.session.commit()
        await self.session.refresh(account)
        return account

    async def delete_account(self, org_id: uuid.UUID, account_id: uuid.UUID):
        """Delete an email account."""
        account = await self.get_account(org_id, account_id)
        await self.session.delete(account)
        await self.session.commit()

    async def get_preference(self, user_id: uuid.UUID, org_id: uuid.UUID) -> Optional[EmailPreference]:
        """Get user email preference."""
        query = select(EmailPreference).where(
            EmailPreference.user_id == user_id,
            EmailPreference.org_id == org_id
        )
        result = await self.session.exec(query)
        return result.first()

    async def set_preference(
        self, 
        user_id: uuid.UUID, 
        org_id: uuid.UUID, 
        account_id: Optional[uuid.UUID]
    ) -> EmailPreference:
        """Set user email preference."""
        preference = await self.get_preference(user_id, org_id)
        
        if preference:
            preference.preferred_account_id = account_id
            preference.updated_at = datetime.utcnow()
        else:
            preference = EmailPreference(
                user_id=user_id,
                org_id=org_id,
                preferred_account_id=account_id
            )
            
        self.session.add(preference)
        await self.session.commit()
        await self.session.refresh(preference)
        return preference
