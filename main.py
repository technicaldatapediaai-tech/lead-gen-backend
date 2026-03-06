"""
Lead Genius Backend - FastAPI Application
Main entry point with all routes configured.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
from contextlib import asynccontextmanager

from backend.database import init_db

# Re-initializing backend with billing integration v2.4
from backend.api import auth, users, leads, campaigns, outreach, personas, scoring, dashboard, organizations, extension, linkedin, apify, analysis, enrichment, billing, email

# Import models to ensure they are registered with SQLModel
from backend.models import (
    User, Organization, OrganizationMember,
    RefreshToken, PasswordResetToken, EmailVerificationToken,
    Lead, Campaign,
    OutreachMessage, MessageTemplate,
    Persona, ScoringRule,
    ActivityLog, Webhook, WebhookDelivery,
    LinkedInCredential, LinkedInPreference,
    EmailAccount, EmailPreference,
    Invoice, SubscriptionInfo
)
from backend.campaigns.run_models import CampaignRun
from backend.models.lead import LeadInteraction


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    # Startup
    await init_db()
    
    # Start background workers
    import asyncio
    from backend.services.background_tasks import email_automation_worker
    asyncio.create_task(email_automation_worker())
    
    yield
    # Shutdown


app = FastAPI(
    title="Lead Genius API",
    description="AI-powered lead generation and intelligence platform",
    version="2.0.0",
    lifespan=lifespan
)

# Error logging middleware
@app.middleware("http")
async def log_errors(request, call_next):
    try:
        return await call_next(request)
    except Exception as e:
        import traceback
        with open(r"c:\Users\Lenovo\Downloads\lead genius\lead genius\critical_errors.log", "a") as f:
            f.write(f"\n--- ERROR at {datetime.now()} ---\n")
            f.write(f"URL: {request.url}\n")
            f.write(traceback.format_exc())
        raise e

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include all routers
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(organizations.router)  # Multi-org support
app.include_router(leads.router)
app.include_router(campaigns.router)
app.include_router(outreach.router)
app.include_router(personas.router)
app.include_router(scoring.router)
app.include_router(dashboard.router)
app.include_router(extension.router)  # Chrome extension API
app.include_router(linkedin.router)   # LinkedIn API integration
app.include_router(apify.router)      # Apify integration
app.include_router(analysis.router)   # Post Analysis
app.include_router(enrichment.router) # Apollo enrichment
app.include_router(billing.router)
app.include_router(email.router)


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "message": "Lead Genius API is running",
        "version": "2.3.0",
        "docs": "/docs"
    }


@app.get("/health")
async def health():
    """Detailed health check."""
    return {
        "status": "healthy",
        "version": "2.3.0"
    }

