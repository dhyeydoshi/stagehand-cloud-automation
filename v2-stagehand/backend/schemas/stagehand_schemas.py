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
    result: Any = Field(..., description="Agent execution result")
    url: str = Field(..., description="Starting URL")
    timestamp: str = Field(..., description="Timestamp of execution")
    processing_time: float = Field(..., description="Processing time in seconds")
    execution_method: str = Field(default="agent", description="Execution method used")
    error: Optional[str] = Field(default=None, description="Error message if failed")
    error_code: Optional[str] = Field(default=None, description="Error code if failed")


# Extraction Schemas (extract with custom schema)


class ExtractionRequest(BaseModel):
    url: str = Field(..., description="Target URL to extract from")
    instruction: str = Field(
        ...,
        description="Natural language extraction instruction"
    )
    schema_name: str = Field(
        ...,
        description="Name of the Pydantic schema to use for extraction",
        examples=["ProductData", "JobPosting", "CompanyInfo"]
    )
    take_screenshots: bool = Field(
        default=False,
        description="Take screenshot after extraction"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "url": "https://example.com/product",
                "instruction": "Extract product name, price, and rating",
                "schema_name": "ProductData",
                "take_screenshots": True
            }
        }


class ExtractionResponse(BaseModel):
    success: bool = Field(..., description="Whether extraction succeeded")
    data: Dict[str, Any] = Field(..., description="Extracted data")
    schema_name: str = Field(..., description="Schema name used for extraction", alias="schema")
    instruction: str = Field(..., description="Extraction instruction")
    artifacts: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Screenshots or other artifacts"
    )
    url: str = Field(..., description="URL extracted from")
    timestamp: str = Field(..., description="Timestamp of extraction")
    processing_time: float = Field(..., description="Processing time in seconds")
    error: Optional[str] = Field(default=None, description="Error message if failed")
    error_code: Optional[str] = Field(default=None, description="Error code if failed")

    model_config = {"populate_by_name": True}


class StagehandJobConfig(BaseModel):
    extract_prompt: Optional[str] = Field(
        default=None,
        description="AI extraction prompt for general content"
    )
    extract_links: bool = Field(
        default=False,
        description="Extract all links from page"
    )

    # Stagehand-specific features
    use_observe_act: bool = Field(
        default=False,
        description="Use observe + act pattern for actions"
    )
    action_instruction: Optional[str] = Field(
        default=None,
        description="Action to perform using observe + act"
    )

    use_agent: bool = Field(
        default=False,
        description="Use agent for complex workflows"
    )
    workflow_instruction: Optional[str] = Field(
        default=None,
        description="Workflow for agent to execute"
    )
    agent_max_steps: int = Field(
        default=20,
        description="Maximum steps for agent",
        ge=1,
        le=100
    )

    # Custom schema extraction
    custom_schema_name: Optional[str] = Field(
        default=None,
        description="Name of custom Pydantic schema for extraction"
    )

    # General options
    take_screenshots: bool = Field(default=False, description="Take screenshots")
    draw_overlay: bool = Field(default=False, description="Draw overlay on observed elements")
    wait_between_actions: int = Field(
        default=1000,
        description="Wait between actions in ms",
        ge=0,
        le=10000
    )


class StagehandJobRequest(BaseModel):
    url: str = Field(..., description="Target URL")
    tenant_id: Optional[str] = Field(default=None, description="Tenant ID")
    config: StagehandJobConfig = Field(
        default_factory=StagehandJobConfig,
        description="Stagehand job configuration"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "url": "https://example.com",
                "tenant_id": "tenant_123",
                "config": {
                    "extract_prompt": "Extract product information",
                    "extract_links": False,
                    "take_screenshots": True,
                    "use_observe_act": False,
                    "use_agent": False
                }
            }
        }


class ProductData(BaseModel):
    name: str = Field(..., description="Product name")
    price: float = Field(..., description="Product price in USD")
    rating: Optional[float] = Field(None, description="Product rating (0-5)")
    in_stock: bool = Field(..., description="Product availability")
    description: Optional[str] = Field(None, description="Product description")


class JobPosting(BaseModel):
    title: str = Field(..., description="Job title")
    company: str = Field(..., description="Company name")
    location: str = Field(..., description="Job location")
    salary_range: Optional[str] = Field(None, description="Salary range if available")
    description: str = Field(..., description="Job description")
    requirements: List[str] = Field(..., description="List of job requirements")


class CompanyInfo(BaseModel):
    name: str = Field(..., description="Company name")
    description: str = Field(..., description="Company description")
    founded_year: Optional[int] = Field(None, description="Year founded")
    employee_count: Optional[str] = Field(None, description="Number of employees")
    industry: Optional[str] = Field(None, description="Industry sector")


class ArticleData(BaseModel):
    headline: str = Field(..., description="Article headline")
    author: str = Field(..., description="Article author")
    published_date: str = Field(..., description="Publication date")
    summary: str = Field(..., description="Article summary or excerpt")
    category: Optional[str] = Field(None, description="Article category or topic")
    read_time: Optional[str] = Field(None, description="Estimated reading time")


# Schema registry for dynamic lookup
EXTRACTION_SCHEMAS = {
    "ProductData": ProductData,
    "JobPosting": JobPosting,
    "CompanyInfo": CompanyInfo,
    "ArticleData": ArticleData,
}


def get_extraction_schema(schema_name: str) -> Optional[type[BaseModel]]:
    return EXTRACTION_SCHEMAS.get(schema_name)

