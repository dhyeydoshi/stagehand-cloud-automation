from datetime import datetime, timezone
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = Field(..., description="Health status")
    timestamp: datetime = Field(..., description="Response timestamp")
    version: str = Field(..., description="Application version")
    services: Optional[Dict[str, str]] = Field(default=None, description="Service status")