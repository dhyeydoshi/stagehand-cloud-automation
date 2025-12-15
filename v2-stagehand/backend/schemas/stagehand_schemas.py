from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field


# Action Schemas (observe + act)

class ActionRequest(BaseModel):
    url: str = Field(..., description="Target URL")
    action_instruction: str = Field(
        ...,
        description="Natural language instruction (e.g., 'Click the sign in button')"
    )
    draw_overlay: bool = Field(
        default=False,
        description="Show visual overlay on observed elements"
    )
    take_screenshots: bool = Field(
        default=False,
        description="Take screenshot after action"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "url": "https://example.com",
                "action_instruction": "Click the sign in button",
                "draw_overlay": True,
                "take_screenshots": True
            }
        }


class ActionResponse(BaseModel):
    success: bool = Field(..., description="Whether action succeeded")
    action: str = Field(..., description="Action that was performed")
    observed_elements: int = Field(..., description="Number of elements observed")
    artifacts: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Screenshots or other artifacts"
    )
    url: str = Field(..., description="URL where action was performed")
    timestamp: str = Field(..., description="Timestamp of execution")
    processing_time: float = Field(..., description="Processing time in seconds")
    model_used: Optional[str] = Field(default=None, description="LLM model used for single-step action")
    execution_method: Optional[str] = Field(default="single-step", description="Execution method used")
    error: Optional[str] = Field(default=None, description="Error message if failed")
    error_code: Optional[str] = Field(default=None, description="Error code if failed")


# Workflow Schemas (agent)

class WorkflowRequest(BaseModel):
    url: str = Field(..., description="Starting URL for workflow")
    workflow_instruction: str = Field(
        ...,
        description="Natural language workflow description",
        examples=[
            "Navigate to products page and filter by 'Electronics'",
            "Apply for the first engineer position with mock data"
        ]
    )
    max_steps: int = Field(
        default=20,
        description="Maximum number of steps agent can take",
        ge=1,
        le=100
    )
    auto_screenshot: bool = Field(
        default=True,
        description="Automatically take screenshots at each step"
    )
    wait_between_actions: int = Field(
        default=1000,
        description="Milliseconds to wait between actions",
        ge=0,
        le=10000
    )

    class Config:
        json_schema_extra = {
            "example": {
                "url": "https://jobs.example.com",
                "workflow_instruction": "Apply for the first engineer position with mock data",
                "max_steps": 30,
                "auto_screenshot": True,
                "wait_between_actions": 2000
            }
        }


class WorkflowResponse(BaseModel):
    success: bool = Field(..., description="Whether workflow succeeded")
    workflow: str = Field(..., description="Workflow instruction that was executed")
    message: Optional[str] = Field(default=None, description="Summary message from agent including memorized facts")
    memorized_facts: List[str] = Field(default_factory=list, description="Facts memorized by the agent during execution")
    result: Any = Field(..., description="Agent execution result")
    url: str = Field(..., description="Starting URL")
    timestamp: str = Field(..., description="Timestamp of execution")
    processing_time: float = Field(..., description="Processing time in seconds")
    execution_method: str = Field(default="agent", description="Execution method used")
    agent_model: Optional[str] = Field(default=None, description="CUA model used for agent workflow")
    error: Optional[str] = Field(default=None, description="Error message if failed")
    error_code: Optional[str] = Field(default=None, description="Error code if failed")
