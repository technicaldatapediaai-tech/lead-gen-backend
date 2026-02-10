"""
User settings schemas.
"""
from typing import Optional, Dict, Any
from pydantic import BaseModel


class UserSettingsResponse(BaseModel):
    """User settings response."""
    language_preference: str
    timezone: str
    email_preferences: Optional[Dict[str, Any]] = None
    
    class Config:
        from_attributes = True


class UserSettingsUpdate(BaseModel):
    """Update user settings."""
    language_preference: Optional[str] = None
    timezone: Optional[str] = None
    email_preferences: Optional[Dict[str, Any]] = None


class WorkingHoursSettings(BaseModel):
    """Working hours and activity settings."""
    working_days: Dict[str, bool] = {
        "MONDAY": True,
        "TUESDAY": True,
        "WEDNESDAY": True,
        "THURSDAY": True,
        "FRIDAY": True,
        "SATURDAY": False,
        "SUNDAY": False
    }
    start_time: str = "09:00"  # 24-hour format
    end_time: str = "17:00"
    daily_custom_mode: bool = False
    
    class Config:
        from_attributes = True
