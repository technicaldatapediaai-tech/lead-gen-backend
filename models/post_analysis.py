from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import JSONB
import uuid

class LinkedInPost(SQLModel, table=True):
    """
    Represents a LinkedIn post being tracked and analyzed.
    """
    __tablename__ = "linkedin_post"
    
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    post_url: str = Field(index=True)
    
    # Metadata extracted from the post
    author_name: Optional[str] = None
    post_content: Optional[str] = None
    posted_at: Optional[datetime] = None
    
    # Analysis Status
    status: str = Field(default="pending")  # pending, processing, completed, failed
    apify_run_id: Optional[str] = None
    
    # Analysis Results
    post_intent: Optional[str] = None
    total_comments: int = Field(default=0)
    total_likes: int = Field(default=0)
    
    # AI Insights
    ai_insights: Dict[str, Any] = Field(default={}, sa_column=Column(JSONB))
    
    # Organization & Persona
    org_id: uuid.UUID = Field(foreign_key="organization.id", index=True)
    persona_id: Optional[uuid.UUID] = Field(default=None, foreign_key="persona.id", index=True)
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    interactions: List["PostInteraction"] = Relationship(back_populates="post")


class PostInteraction(SQLModel, table=True):
    """
    An interaction (Like/Comment) on a tracked post.
    """
    __tablename__ = "post_interaction"
    
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    post_id: uuid.UUID = Field(foreign_key="linkedin_post.id", index=True)
    
    # Interaction Details
    type: str = Field(index=True)  # COMMENT, LIKE
    content: Optional[str] = None  # Comment text
    reacted_at: Optional[datetime] = None
    
    # User Details (The Lead)
    actor_name: Optional[str] = None
    actor_profile_url: Optional[str] = None
    actor_headline: Optional[str] = None
    actor_urn: Optional[str] = None # LinkedIn ID
    
    # Scoring & Classification
    relevance_score: int = Field(default=0)
    classification: str = Field(default="unclassified") # high, medium, low, irrelevant
    
    # AI Evaluation Results
    profile_type: Optional[str] = None  # individual, company
    seniority_level: Optional[str] = None  # C-level, VP, Director, etc.
    role_category: Optional[str] = None  # decision_maker, influencer, end_user, irrelevant
    ai_insights: Dict[str, Any] = Field(default={}, sa_column=Column(JSONB))
    
    # Link to Lead if converted
    lead_id: Optional[uuid.UUID] = Field(default=None, index=True)
    
    post: LinkedInPost = Relationship(back_populates="interactions")
