import asyncio
import logging
import uuid
from sqlmodel import select
from backend.database import engine
from backend.models.outreach import OutreachMessage
from backend.services.outreach_service import OutreachService
from sqlalchemy.orm import sessionmaker
from sqlmodel.ext.asyncio.session import AsyncSession

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def email_automation_worker():
    """
    Background worker that periodically checks for pending emails and sends them.
    It runs in an infinite loop, sleeping between cycles.
    """
    logger.info("📧 Email Automation Worker starting...")
    
    # We need a manual session factory because get_session is a dependency
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    while True:
        try:
            async with async_session() as session:
                # 1. Find pending email messages
                query = select(OutreachMessage).where(
                    OutreachMessage.channel == "email",
                    OutreachMessage.status == "pending"
                ).limit(5)  # Small batches
                
                result = await session.exec(query)
                messages = result.all()
                
                if not messages:
                    # No pending emails, check again later
                    await asyncio.sleep(15)
                    continue
                
                logger.info(f"🚀 Worker found {len(messages)} pending emails to process")
                
                outreach_service = OutreachService(session)
                
                for msg in messages:
                    try:
                        if not msg.user_id:
                            logger.warning(f"⚠️ Message {msg.id} has no associated user_id, cannot find SMTP config. Skipping.")
                            # Mark as failed so it doesn't keep looping
                            msg.status = "failed"
                            msg.error_message = "No user_id associated with message"
                            session.add(msg)
                            continue
                            
                        logger.info(f"📤 Sending email {msg.id} to lead {msg.lead_id}")
                        
                        # Use the existing send_message logic which handles SMTP connection
                        await outreach_service.send_message(
                            org_id=msg.org_id,
                            user_id=msg.user_id,
                            message_id=msg.id
                        )
                        
                        # Commitment is handled inside send_message (it calls update_status)
                        # but we should ensure the session in outreach_service is the same
                        
                    except Exception as e:
                        logger.error(f"❌ Error processing message {msg.id}: {str(e)}")
                        # Status update is usually handled inside send_message try/except too
            
            # Wait a bit between message processing to avoid rate limits
            await asyncio.sleep(5)
            
        except Exception as e:
            logger.error(f"🚨 Email worker loop CRITICAL error: {e}")
            await asyncio.sleep(60) # Long sleep on system error
