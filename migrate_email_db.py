import asyncio
from sqlalchemy import text
from backend.database import engine

async def migrate_email_account():
    print("Migrating email_account table...")
    async with engine.begin() as conn:
        # Check if columns exist and add them if they don't
        await conn.execute(text("ALTER TABLE email_account ADD COLUMN IF NOT EXISTS access_token VARCHAR"))
        await conn.execute(text("ALTER TABLE email_account ADD COLUMN IF NOT EXISTS refresh_token VARCHAR"))
        await conn.execute(text("ALTER TABLE email_account ADD COLUMN IF NOT EXISTS token_expires_at TIMESTAMP"))
        
        # Also ensure provider can handle 'google' (it was already there but good to check)
        # and ensure smtp fields are nullable (which they are in my model now)
        await conn.execute(text("ALTER TABLE email_account ALTER COLUMN smtp_host DROP NOT NULL"))
        await conn.execute(text("ALTER TABLE email_account ALTER COLUMN smtp_user DROP NOT NULL"))
        await conn.execute(text("ALTER TABLE email_account ALTER COLUMN smtp_password DROP NOT NULL"))
        
    print("Migration complete.")

if __name__ == "__main__":
    asyncio.run(migrate_email_account())
