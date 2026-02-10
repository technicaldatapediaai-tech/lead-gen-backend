from typing import Optional
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Environment
    DEV_MODE: bool = True  # Set to False in production
    FRONTEND_URL: str = "http://localhost:3000"  # Your Next.js frontend URL
    
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/lead_genius"
    
    # JWT Settings
    SECRET_KEY: str = "supersecretkey"  # Change this in production!
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # Password Reset
    PASSWORD_RESET_TOKEN_EXPIRE_HOURS: int = 24
    
    # Email Verification
    EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS: int = 48
    
    # Email Settings (configure these in .env for production)
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    EMAIL_FROM: str = "noreply@leadgenius.com"
    
    # API Settings
    API_PREFIX: str = "/api"
    BACKEND_URL: str = "http://localhost:8000"
    
    # LinkedIn API Settings (configure in .env for LinkedIn integration)
    LINKEDIN_CLIENT_ID: str = ""
    LINKEDIN_CLIENT_SECRET: str = ""

    # Apify Settings
    APIFY_API_TOKEN: str = ""
    APIFY_WEBHOOK_SECRET: str = ""
    
    # OpenAI Settings (for AI-powered analysis)
    # Using OpenRouter for unified access to multiple AI models
    OPENAI_API_KEY: str = ""
    OPENAI_BASE_URL: str = "https://openrouter.ai/api/v1"  # OpenRouter endpoint
    GEMINI_API_KEY: Optional[str] = ""  # Disabled in favor of OpenRouter
    AI_MODEL: str = "openai/gpt-4o-mini"  # Fast, cost-effective model via OpenRouter
    
    # Apollo.io Settings (for lead enrichment)
    APOLLO_API_KEY: str = ""
    APOLLO_AUTO_ENRICH: bool = True  # Auto-enrich high-value leads
    APOLLO_MIN_SCORE_FOR_ENRICH: int = 70  # Only enrich leads with score >= 70
    
    class Config:
        env_file = ".env"
        extra = "ignore"  # Allow extra fields in .env

settings = Settings()


