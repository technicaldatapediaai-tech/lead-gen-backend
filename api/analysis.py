from fastapi import APIRouter, HTTPException, Request, BackgroundTasks, Depends, Query
from pydantic import BaseModel
from typing import List, Optional
import logging
import uuid
from sqlmodel import Session, select

from backend.services.analysis_service import analysis_service
from backend.models.post_analysis import LinkedInPost, PostInteraction
from backend.models.lead import Lead
from backend.database import engine

router = APIRouter(prefix="/ingest/analysis", tags=["Post Analysis"])
logger = logging.getLogger(__name__)

class AnalyzeRequest(BaseModel):
    post_urls: List[str]
    org_id: str  # UUID as string
    persona_id: Optional[str] = None

@router.post("/")
async def start_analysis(request: AnalyzeRequest):
    """
    Start analysis on a list of LinkedIn Post URLs.
    """
    if len(request.post_urls) > 10:
        raise HTTPException(status_code=400, detail="Max 10 URLs allowed per batch")
        
    try:
        org_uuid = uuid.UUID(request.org_id)
        persona_uuid = uuid.UUID(request.persona_id) if request.persona_id else None
        
        started_ids = await analysis_service.analyze_posts(
            request.post_urls,
            org_uuid,
            persona_uuid
        )
        return {"status": "started", "count": len(started_ids), "ids": started_ids}
    except Exception as e:
        logger.error(f"Analysis trigger failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/results")
async def get_analysis_results(
    org_id: str = Query(..., description="Organization ID"),
    limit: int = Query(20, le=100),
    status: Optional[str] = Query(None)
):
    """
    Get analysis results for an organization.
    Returns posts with their interactions and created leads.
    """
    try:
        org_uuid = uuid.UUID(org_id)
        
        with Session(engine) as session:
            # Fetch posts
            statement = select(LinkedInPost).where(LinkedInPost.org_id == org_uuid)
            if status:
                statement = statement.where(LinkedInPost.status == status)
            statement = statement.order_by(LinkedInPost.created_at.desc()).limit(limit)
            
            posts = session.exec(statement).all()
            
            results = []
            for post in posts:
                # Get interactions
                interactions_stmt = select(PostInteraction).where(
                    PostInteraction.post_id == post.id
                ).order_by(PostInteraction.relevance_score.desc())
                interactions = session.exec(interactions_stmt).all()
                
                # Get created leads
                lead_ids = [i.lead_id for i in interactions if i.lead_id]
                leads = []
                if lead_ids:
                    leads_stmt = select(Lead).where(Lead.id.in_(lead_ids))
                    leads = session.exec(leads_stmt).all()
                
                results.append({
                    "post": {
                        "id": str(post.id),
                        "url": post.post_url,
                        "content": post.post_content[:200] if post.post_content else "",
                        "author": post.author_name,
                        "status": post.status,
                        "intent": post.post_intent,
                        "ai_insights": post.ai_insights,
                        "total_comments": post.total_comments,
                        "total_likes": post.total_likes,
                        "created_at": post.created_at.isoformat() if post.created_at else None
                    },
                    "interactions": [
                        {
                            "id": str(i.id),
                            "type": i.type,
                            "actor_name": i.actor_name,
                            "actor_headline": i.actor_headline,
                            "classification": i.classification,
                            "score": i.relevance_score,
                            "profile_type": i.profile_type,
                            "seniority": i.seniority_level,
                            "lead_id": str(i.lead_id) if i.lead_id else None
                        }
                        for i in interactions
                    ],
                    "leads_created": len([i for i in interactions if i.lead_id]),
                    "high_value_count": len([i for i in interactions if i.classification == "high"])
                })
            
            return {
                "total": len(results),
                "results": results
            }
            
    except Exception as e:
        logger.error(f"Failed to fetch results: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/webhook")
async def analysis_webhook(request: Request, background_tasks: BackgroundTasks):
    """
    Specific webhook for the Analysis Service.
    """
    payload = await request.json()
    logger.info(f"Received Analysis webhook: {payload}")
    
    event_type = payload.get("eventType")
    resource = payload.get("resource", {})
    run_id = resource.get("id")
    dataset_id = resource.get("defaultDatasetId")

    if event_type == "ACTOR.RUN.SUCCEEDED" and dataset_id:
        background_tasks.add_task(analysis_service.process_webhook, dataset_id, run_id)
    
    return {"status": "received"}
