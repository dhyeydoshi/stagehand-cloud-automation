from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from enum import Enum


class InstructionType(str, Enum):
    NAVIGATE = "goto"
    OBSERVE = "observe"
    ACT = "act"
    EXTRACT = "extract"
    WAIT = "wait"
    SCREENSHOT = "screenshot"


class StepInstruction(BaseModel):
    step_number: int = Field(..., description="Step sequence number", ge=1)
    instruction_type: InstructionType = Field(..., description="Type of instruction")
    instruction_text: str = Field(..., description="Natural language instruction")
    selector: Optional[str] = Field(default=None, description="CSS selector if applicable")
    wait_after: int = Field(default=1000, description="Milliseconds to wait after step", ge=0, le=30000)

    class Config:
        json_schema_extra = {
            "example": {
                "step_number": 1,
                "instruction_type": "goto",
                "instruction_text": "Go to the products section",
                "wait_after": 2000
            }
        }


class MultiStepJobRequest(BaseModel):
    url: str = Field(..., description="Starting URL")
    tenant_id: Optional[str] = Field(default="default", description="Tenant ID")
    instructions: List[StepInstruction] = Field(
        ...,
        description="List of sequential instructions to execute",
        min_length=1
    )
    take_screenshots: bool = Field(
        default=True,
        description="Take screenshot after each step"
    )
    draw_overlay: bool = Field(
        default=False,
        description="Draw overlay on observed elements"
    )
    stop_on_error: bool = Field(
        default=False,
        description="Stop execution if any step fails"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "url": "https://example.com",
                "tenant_id": "default",
                "instructions": [
                    {
                        "step_number": 1,
                        "instruction_type": "goto",
                        "instruction_text": "Go to section one",
                        "wait_after": 1000
                    },
                    {
                        "step_number": 2,
                        "instruction_type": "observe",
                        "instruction_text": "Find the image in the gallery",
                        "wait_after": 1000
                    },
                    {
                        "step_number": 3,
                        "instruction_type": "extract",
                        "instruction_text": "Extract image URL and metadata",
                        "wait_after": 500
                    }
                ],
                "take_screenshots": True,
                "draw_overlay": False,
                "stop_on_error": False
            }
        }


class StepResult(BaseModel):
    step_number: int = Field(..., description="Step sequence number")
    instruction_type: str = Field(..., description="Type of instruction executed")
    instruction_text: str = Field(..., description="Instruction that was executed")
    success: bool = Field(..., description="Whether step succeeded")
    data: Optional[Dict[str, Any]] = Field(default=None, description="Extracted data if any")
    screenshot: Optional[str] = Field(default=None, description="Base64 screenshot if taken")
    error: Optional[str] = Field(default=None, description="Error message if failed")
    error_code: Optional[str] = Field(default=None, description="Error code if failed")
    execution_time: float = Field(..., description="Step execution time in seconds")
    timestamp: str = Field(..., description="Step completion timestamp")


class MultiStepJobResponse(BaseModel):
    job_id: str = Field(..., description="Job ID")
    url: str = Field(..., description="Starting URL")
    total_steps: int = Field(..., description="Total number of steps")
    completed_steps: int = Field(..., description="Number of completed steps")
    success: bool = Field(..., description="Overall job success")
    steps: List[StepResult] = Field(..., description="Results for each step")
    total_execution_time: float = Field(..., description="Total execution time in seconds")
    started_at: str = Field(..., description="Job start timestamp")
    completed_at: str = Field(..., description="Job completion timestamp")
    model_used: Optional[str] = Field(default=None, description="LLM model used for multi-step workflow")
    execution_method: Optional[str] = Field(default="multi-step", description="Execution method used")
    error: Optional[str] = Field(default=None, description="Overall error message if failed")
    error_code: Optional[str] = Field(default=None, description="Overall error code if failed")

    class Config:
        json_schema_extra = {
            "example": {
                "job_id": "job_abc123",
                "url": "https://example.com",
                "total_steps": 3,
                "completed_steps": 3,
                "success": True,
                "steps": [
                    {
                        "step_number": 1,
                        "instruction_type": "goto",
                        "instruction_text": "Go to section one",
                        "success": True,
                        "data": None,
                        "screenshot": "base64_data...",
                        "error": None,
                        "execution_time": 1.5,
                        "timestamp": "2025-11-04T12:00:00Z"
                    }
                ],
                "total_execution_time": 5.2,
                "started_at": "2025-11-04T12:00:00Z",
                "completed_at": "2025-11-04T12:00:05Z"
            }
        }

