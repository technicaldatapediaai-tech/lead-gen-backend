from sqlmodel import SQLModel, create_engine
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from .config import settings

# Create Async Engine
engine = create_async_engine(settings.DATABASE_URL, echo=True, future=True)

# Set to True to recreate all tables (WARNING: deletes all data)
RECREATE_TABLES = False  # Disabled to preserve data

async def init_db():
    print("Initializing database...")
    print(f"Connecting to: {settings.DATABASE_URL}")
    async with engine.begin() as conn:
        print("Connected to database successfully!")
        if RECREATE_TABLES:
            # Drop all tables with CASCADE to handle foreign key dependencies
            await conn.execute(text("DROP SCHEMA public CASCADE"))
            await conn.execute(text("CREATE SCHEMA public"))
            await conn.execute(text("GRANT ALL ON SCHEMA public TO public"))
        print("Creating tables if they don't exist...")
        await conn.run_sync(SQLModel.metadata.create_all)
        print("Tables created!")
        
        # Schema Evolution: Add columns if missing (for dev environment)
        try:
            await conn.execute(text("ALTER TABLE lead ADD COLUMN IF NOT EXISTS profile_data JSONB DEFAULT '{}'::jsonb"))
            await conn.execute(text("ALTER TABLE outreach_message ADD COLUMN IF NOT EXISTS message_type VARCHAR DEFAULT 'inmail'"))
            await conn.execute(text("ALTER TABLE outreach_message ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES \"user\"(id)"))
            await conn.execute(text("ALTER TABLE organization ADD COLUMN IF NOT EXISTS credits INTEGER DEFAULT 500"))
        except Exception as e:
            print(f"Migration warning: {e}")

async def get_session() -> AsyncSession:
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session() as session:
        yield session


