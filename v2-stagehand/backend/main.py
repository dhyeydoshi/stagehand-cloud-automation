import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

from config import settings
from services.stagehand_service import StagehandService
from schemas.stagehand_schemas import (
    ActionRequest,
    ActionResponse,
    ExtractionRequest,
    ExtractionResponse,
    WorkflowRequest,
    WorkflowResponse,
    ProductData,
    JobPosting,
    CompanyInfo,
)
from schemas.multistep_schemas import MultiStepJobRequest, MultiStepJobResponse
from schemas.common import HealthResponse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Stagehand service
stagehand_service = StagehandService()

# Schema mapping for extraction
SCHEMA_MAP = {
    "ProductData": ProductData,
    "JobPosting": JobPosting,
    "CompanyInfo": CompanyInfo,
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting Stagehand AI Automation API...")

    try:
        # Verify Stagehand configuration
        connection_ok = await stagehand_service.test_connection()
        if connection_ok:
            logger.info("✅ Stagehand configuration verified")
        else:
            logger.warning("⚠️  Stagehand configuration incomplete - will initialize on first use")
    except Exception as e:
        logger.warning(f"⚠️  Stagehand check failed: {e}")

    logger.info("🚀 Application startup completed")

    yield

    logger.info("Shutting down Stagehand API...")
    logger.info("✅ Application shutdown complete (session-per-job mode - no cleanup needed)")


app = FastAPI(
    title="Stagehand AI Automation API",
    description="AI-powered browser automation with Stagehand",
    version=settings.VERSION,
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now(timezone.utc),
        version=settings.VERSION
    )


@app.get("/health/ready", tags=["Health"])
async def readiness_check():
    try:
        # Quick config check
        is_ready = await stagehand_service.test_connection()
        if is_ready:
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={"status": "ready"}
            )
        else:
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={"status": "not_ready", "reason": "Stagehand not configured"}
            )
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "not_ready", "reason": str(e)}
        )


@app.post(
    "/api/v1/stagehand/action",
    response_model=ActionResponse,
    tags=["Stagehand"],
    summary="Execute single action (observe + act)"
)
async def execute_action(request: ActionRequest):

    try:
        logger.info(f"Executing action on {request.url}: {request.action_instruction}")
        result = await stagehand_service.perform_action_with_observe(
            url=request.url,
            action_instruction=request.action_instruction,
            config={
                "draw_overlay": request.draw_overlay,
                "take_screenshots": request.take_screenshots
            }
        )
        logger.info(f"Action completed successfully")
        return result

    except Exception as e:
        logger.error(f"Action execution failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Action execution failed: {str(e)}"
        )


@app.post(
    "/api/v1/stagehand/extract",
    response_model=ExtractionResponse,
    tags=["Stagehand"],
    summary="Extract structured data"
)
async def extract_data(request: ExtractionRequest):
    try:
        logger.info(f"Extracting data from {request.url} using schema {request.schema_name}")

        # Get the actual Pydantic schema class
        schema_class = SCHEMA_MAP.get(request.schema_name)
        if not schema_class:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown schema: {request.schema_name}. Available: {list(SCHEMA_MAP.keys())}"
            )

        result = await stagehand_service.extract_with_schema(
            url=request.url,
            instruction=request.instruction,
            schema=schema_class,  # Pass actual Pydantic class, not string
            config={
                "take_screenshots": request.take_screenshots
            }
        )
        logger.info(f"Extraction completed successfully")
        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Extraction failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Extraction failed: {str(e)}"
        )


@app.post(
    "/api/v1/stagehand/workflow",
    response_model=WorkflowResponse,
    tags=["Stagehand"],
    summary="Execute agent workflow"
)
async def execute_workflow(request: WorkflowRequest):
    try:
        logger.info(f"Executing workflow on {request.url}: {request.workflow_instruction}")
        result = await stagehand_service.execute_workflow_with_agent(
            url=request.url,
            workflow_instruction=request.workflow_instruction,
            config={
                "max_steps": request.max_steps,
                "auto_screenshot": request.auto_screenshot,
                "wait_between_actions": request.wait_between_actions
            }
        )
        logger.info(f"Workflow completed successfully")
        return result

    except Exception as e:
        logger.error(f"Workflow execution failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Workflow execution failed: {str(e)}"
        )


@app.post("/api/v1/stagehand/multistep",
    response_model=MultiStepJobResponse,
    tags=["Stagehand"],
    summary="Execute multi-step sequential workflow")
async def execute_multistep(request: MultiStepJobRequest):
    try:
        logger.info(f"Executing multi-step workflow on {request.url} with {len(request.instructions)} steps")
        result = await stagehand_service.process_multi_step_instructions(
            url=request.url,
            instructions=request.instructions,
            config={
                "take_screenshots": request.take_screenshots,
                "draw_overlay": request.draw_overlay,
                "stop_on_error": request.stop_on_error
            }
        )
        logger.info(f"Multi-step workflow completed")
        return result

    except Exception as e:
        logger.error(f"Multi-step workflow failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Multi-step workflow failed: {str(e)}"
        )


@app.get("/api/v1/stagehand/schemas",
    tags=["Stagehand"],
    summary="List available extraction schemas")
async def list_available_schemas():
    try:
        schemas = [
            {
                "name": "ProductData",
                "description": "Extract product information",
                "fields": ["name", "price", "rating", "in_stock", "description"]
            },
            {
                "name": "JobPosting",
                "description": "Extract job posting details",
                "fields": ["title", "company", "location", "salary_range", "description", "requirements"]
            },
            {
                "name": "CompanyInfo",
                "description": "Extract company information",
                "fields": ["name", "description", "founded_year", "employee_count", "industry"]
            }
        ]

        return {
            "schemas": schemas,
            "note": "Schemas are optional. You can also extract data without schemas using natural language instructions."
        }

    except Exception as e:
        logger.error(f"Error listing schemas: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list schemas"
        )



# Error Handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": exc.detail,
            "error_code": f"HTTP_{exc.status_code}",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error": "Internal server error" if not settings.DEBUG else str(exc),
            "error_code": "INTERNAL_SERVER_ERROR",
            "details": {"message": str(exc)} if settings.DEBUG else None,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    )


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        log_level=settings.LOG_LEVEL.lower()

    )

