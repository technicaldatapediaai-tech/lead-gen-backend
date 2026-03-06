"""
Outreach service - messaging and templates.
"""
import uuid
from typing import Optional, List
from datetime import datetime
import re
import json

from sqlmodel.ext.asyncio.session import AsyncSession

from backend.core.exceptions import raise_not_found
from backend.repositories.outreach_repo import OutreachMessageRepository, MessageTemplateRepository
from backend.repositories.lead_repo import LeadRepository
from backend.repositories.activity_repo import ActivityLogRepository
from backend.models.outreach import OutreachMessage, MessageTemplate
from backend.models.activity import Actions
from backend.schemas.outreach import OutreachCreate, TemplateCreate, TemplateUpdate


class OutreachService:
    """Service for outreach operations."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.message_repo = OutreachMessageRepository(session)
        self.template_repo = MessageTemplateRepository(session)
        self.lead_repo = LeadRepository(session)
        self.activity_repo = ActivityLogRepository(session)
    
    # Message operations
    async def create_message(
        self,
        org_id: uuid.UUID,
        user_id: uuid.UUID,
        message_data: OutreachCreate
    ) -> OutreachMessage:
        """Create an outreach message."""
        # Verify lead exists and belongs to org
        lead = await self.lead_repo.get(message_data.lead_id)
        if not lead or lead.org_id != org_id:
            raise_not_found("Lead", str(message_data.lead_id))
        
        data = message_data.model_dump()
        data["org_id"] = org_id
        data["user_id"] = user_id
        
        # Set status based on scheduling or input
        if message_data.status:
            data["status"] = message_data.status
        elif message_data.scheduled_at and message_data.scheduled_at > datetime.utcnow():
            data["status"] = "scheduled"
        elif message_data.send_method == "extension":
            data["status"] = "queued"
        else:
            data["status"] = "pending"
        
        # Ensure profile URL is set if passed
        if message_data.linkedin_profile_url:
            data["linkedin_profile_url"] = message_data.linkedin_profile_url
        elif not data.get("linkedin_profile_url") and lead.linkedin_url:
             data["linkedin_profile_url"] = lead.linkedin_url
        
        message = await self.message_repo.create(data)
        
        # Log activity
        await self.activity_repo.log(
            org_id=org_id,
            actor_id=user_id,
            action=Actions.MESSAGE_CREATED,
            entity_type="outreach",
            entity_id=message.id,
            description=f"Message created for lead '{lead.name}'",
            meta_data={"channel": message.channel, "lead_id": str(lead.id)}
        )
        
        return message
    
    async def list_messages(
        self,
        org_id: uuid.UUID,
        lead_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
        page: int = 1,
        limit: int = 20
    ) -> dict:
        """List outreach messages with filters."""
        if lead_id:
            return await self.message_repo.get_by_lead(org_id, lead_id, page, limit)
        
        filters = {}
        if status:
            filters["status"] = status
        
        return await self.message_repo.list_paginated(
            org_id=org_id,
            filters=filters,
            page=page,
            limit=limit
        )
    
    async def get_message(self, org_id: uuid.UUID, message_id: uuid.UUID) -> OutreachMessage:
        """Get a message by ID."""
        message = await self.message_repo.get(message_id)
        if not message or message.org_id != org_id:
            raise_not_found("Message", str(message_id))
        return message
    
    async def send_message(
        self,
        org_id: uuid.UUID,
        user_id: uuid.UUID,
        message_id: uuid.UUID
    ) -> OutreachMessage:
        """Send a pending message (Email or LinkedIn)."""
        message = await self.message_repo.get(message_id)
        if not message or message.org_id != org_id:
            raise_not_found("Message", str(message_id))
        
        if message.status == "sent":
            return message

        try:
            # 1. Handle Email Channel
            if message.channel == "email":
                lead = await self.lead_repo.get(message.lead_id)
                if not lead or not lead.email:
                    raise Exception("Lead has no email address")

                # Get sender account
                from backend.services.email_account_service import EmailAccountService
                account_service = EmailAccountService(self.session)
                pref = await account_service.get_preference(user_id, org_id)
                
                account = None
                if pref and pref.preferred_account_id:
                    account = await account_service.get_account(org_id, pref.preferred_account_id)
                else:
                    # Fallback to any active account for this user/org
                    accounts = await account_service.list_accounts(org_id, user_id)
                    if accounts:
                        account = accounts[0]
                
                if not account:
                    raise Exception("No email account connected. Please connect an email account in settings.")

                # Prepare SMTP config
                smtp_config = {
                    "host": account.smtp_host,
                    "port": account.smtp_port,
                    "user": account.smtp_user,
                    "password": account.smtp_password
                }

                # Simple subject extraction or default
                subject = f"Message for {lead.name}"
                if message.message.startswith("Subject:"):
                    parts = message.message.split("\n", 1)
                    subject = parts[0].replace("Subject:", "").strip()
                    body = parts[1].strip() if len(parts) > 1 else message.message
                else:
                    body = message.message

                # Send
                success = False
                if account.provider == "google":
                    from backend.services.integrations.google import GoogleAPIClient
                    client = GoogleAPIClient()
                    creds = {
                        'access_token': account.access_token,
                        'refresh_token': account.refresh_token,
                        'expires_at': account.token_expires_at,
                        'client_id': settings.GOOGLE_CLIENT_ID,
                        'client_secret': settings.GOOGLE_CLIENT_SECRET
                    }
                    success = client.send_email(creds, lead.email, subject, body)
                else:
                    from backend.services.email_service import SMTPEmailService
                    email_svc = SMTPEmailService()
                    success = await email_svc.send_email(
                        to=lead.email,
                        subject=subject,
                        body=body,
                        from_email=account.email,
                        smtp_config=smtp_config
                    )

                if not success:
                    raise Exception("Email sending failed")

            # 2. Handle LinkedIn Channel (API)
            elif message.channel == "linkedin" and message.send_method == "api":
                from backend.services.integrations.linkedin import get_linkedin_service
                from backend.api.linkedin import get_active_token
                
                user = await self.session.get(user_id.__class__, user_id) # Using raw session as workaround for now
                token, source = await get_active_token(user, self.session)
                if not token:
                    raise Exception("LinkedIn not connected")
                
                svc = get_linkedin_service(token)
                result = await svc.send_outreach_message(message.linkedin_profile_url, message.message, message.message_type or 'inmail')
                if not result.get("success"):
                    raise Exception(result.get("error", "LinkedIn API failed"))

            # 3. Handle LinkedIn Channel (Extension)
            elif message.channel == "linkedin" and message.send_method == "extension":
                # Extension picks it up itself, this shouldn't really be called for 'extension' 
                # unless we want to force mark as sent manually
                pass

            # Update status
            message = await self.message_repo.update_status(message_id, "sent")
            await self.lead_repo.update_status(message.lead_id, "contacted")
            
            await self.activity_repo.log(
                org_id=org_id,
                actor_id=user_id,
                action=Actions.MESSAGE_SENT,
                entity_type="outreach",
                entity_id=message_id,
                description=f"{message.channel.capitalize()} message sent"
            )
            
        except Exception as e:
            message = await self.message_repo.update_status(message_id, "failed", str(e))
        
        return message
    
    # Template operations
    async def create_template(
        self,
        org_id: uuid.UUID,
        template_data: TemplateCreate
    ) -> MessageTemplate:
        """Create a message template."""
        data = template_data.model_dump()
        data["org_id"] = org_id
        
        # Extract variables from content
        variables = self._extract_variables(data["content"])
        data["variables"] = variables
        
        return await self.template_repo.create(data)
    
    async def list_templates(
        self,
        org_id: uuid.UUID,
        channel: Optional[str] = None
    ) -> List[MessageTemplate]:
        """List message templates."""
        if channel:
            return await self.template_repo.get_by_channel(org_id, channel)
        return await self.template_repo.get_active(org_id)
    
    async def get_template(self, org_id: uuid.UUID, template_id: uuid.UUID) -> MessageTemplate:
        """Get a template by ID."""
        template = await self.template_repo.get(template_id)
        if not template or template.org_id != org_id:
            raise_not_found("Template", str(template_id))
        return template
    
    async def update_template(
        self,
        org_id: uuid.UUID,
        template_id: uuid.UUID,
        template_data: TemplateUpdate
    ) -> MessageTemplate:
        """Update a template."""
        template = await self.template_repo.get(template_id)
        if not template or template.org_id != org_id:
            raise_not_found("Template", str(template_id))
        
        update_data = template_data.model_dump(exclude_unset=True)
        
        # Re-extract variables if content changed
        if "content" in update_data:
            update_data["variables"] = self._extract_variables(update_data["content"])
        
        return await self.template_repo.update(template_id, update_data)
    
    async def delete_template(self, org_id: uuid.UUID, template_id: uuid.UUID) -> bool:
        """Delete a template."""
        template = await self.template_repo.get(template_id)
        if not template or template.org_id != org_id:
            raise_not_found("Template", str(template_id))
        
        return await self.template_repo.delete(template_id)
    
    async def render_template(
        self,
        org_id: uuid.UUID,
        template_id: uuid.UUID,
        lead_id: uuid.UUID,
        personalize: bool = False
    ) -> str:
        """Render a template with lead data, optionally using AI for personalization."""
        template = await self.template_repo.get(template_id)
        if not template or template.org_id != org_id:
            raise_not_found("Template", str(template_id))
        
        lead = await self.lead_repo.get(lead_id)
        if not lead or lead.org_id != org_id:
            raise_not_found("Lead", str(lead_id))
        
        # 1. Base string replacement
        content = template.content
        replacements = {
            "name": lead.name,
            "first_name": lead.name.split()[0] if lead.name else "",
            "company": lead.company or "",
            "title": lead.title or "",
            "location": lead.location or ""
        }
        
        for var, value in replacements.items():
            content = content.replace(f"{{{{{var}}}}}", value)
        
        # 2. AI Personalization if requested
        if personalize:
             content = await self.personalize_message_with_ai(content, lead)
             
        return content

    async def personalize_message_with_ai(self, content: str, lead: 'Lead') -> str:
        """Use AI to personalize the message content for a specific lead."""
        from backend.services.ai_analysis_service import ai_analysis_service
        
        lead_info = {
            "name": lead.name,
            "title": lead.title,
            "company": lead.company,
            "headline": lead.headline,
            "about": lead.about[:500] if lead.about else ""
        }

        prompt = f"""
        Act as a professional B2B relationship manager. 
        I have a message template and a lead's profile information. 
        Please rewrite/adjust the message to feel more personal, warm, and highly relevant to this specific individual.
        Keep the core hook and CTA the same, but add a personalized icebreaker or reference their work/role based on the profile provided.

        LEAD PROFILE:
        {json.dumps(lead_info, indent=2)}

        ORIGINAL MESSAGE:
        {content}

        GOAL: High personalization, professional tone, avoids generic sounding "AI" phrases like "I hope this email finds you well".
        
        RETURN ONLY THE PERSONALIZED MESSAGE TEXT.
        """
        
        try:
            # We use json_mode=False because we want the raw string
            personalized = ai_analysis_service._generate_content(prompt, json_mode=False)
            return personalized.strip() if personalized else content
        except Exception as e:
            # Fallback to original content if AI fails
            return content

    def _extract_variables(self, content: str) -> List[str]:
        """Extract {{variable}} patterns from content."""
        pattern = r'\{\{(\w+)\}\}'
        return list(set(re.findall(pattern, content)))
