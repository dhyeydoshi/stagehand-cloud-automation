import asyncio
import json
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone, timedelta
from typing import Any

from fastapi import FastAPI, HTTPException, status, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
import uvicorn
from fastapi.middleware.gzip import GZipMiddleware

from config import settings
from services.stagehand_service import StagehandService
from schemas.stagehand_schemas import (
    ActionRequest,
    ActionResponse,
    WorkflowRequest,
    WorkflowResponse,
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
results: dict[str, Any] = {}

# Configurable cleanup threshold (1 hour)
CLEANUP_THRESHOLD = timedelta(hours=1)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting Stagehand AI Automation API...")

    try:
        # Verify Stagehand configuration
        connection_ok = await stagehand_service.test_connection()
        if connection_ok:
            logger.info("Stagehand configuration verified")
        else:
            logger.warning("Stagehand configuration incomplete - will initialize on first use")
    except Exception as e:
        logger.warning(f"Stagehand check failed: {e}")

    logger.info("Application startup completed")

    yield

    logger.info("Shutting down Stagehand API...")
    logger.info("Application shutdown complete (session-per-job mode - no cleanup needed)")


app = FastAPI(
    title=settings.APP_NAME + " API",
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
app.add_middleware(GZipMiddleware, minimum_size=1000)  # Compress responses >1KB

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

async def run_workflow_background(task_id: str, request: WorkflowRequest):
    try:
        logger.info(f"Running background workflow on {request.url}: {request.workflow_instruction}")
        result = await stagehand_service.execute_workflow_with_agent(
            url=request.url,
            workflow_instruction=request.workflow_instruction,
            config={
                "max_steps": request.max_steps,
                "auto_screenshot": request.auto_screenshot,
                "wait_between_actions": request.wait_between_actions
            }
        )
        results[task_id] = {
            "data": WorkflowResponse(
                success=result["success"],
                workflow=request.workflow_instruction,
                message=result.get("message"),
                memorized_facts=result.get("memorized_facts", []),
                result=result,
                url=request.url,
                timestamp=datetime.now(timezone.utc).isoformat(),
                processing_time=result.get("processing_time", 0.0),
                execution_method=result.get("execution_method", "agent"),
                agent_model=result.get("agent_model"),
            ),
            "timestamp": datetime.now(timezone.utc)
        }
        logger.info(f"Background workflow {task_id} completed")
    except Exception as e:
        logger.error(f"Background workflow {task_id} failed: {e}")
        results[task_id] = {
            "data": {"status": "failed", "error": str(e)},
            "timestamp": datetime.now(timezone.utc)
        }



@app.post(
    "/api/v1/stagehand/workflow",
    response_model=WorkflowResponse,
    tags=["Stagehand"],
    summary="Execute agent workflow (supports Google, OpenAI, Anthropic, Microsoft FARA(Local model))"
)
async def execute_workflow(background_tasks: BackgroundTasks, request: WorkflowRequest):
    task_id = f"workflow_{datetime.now(timezone.utc).isoformat()}"
    background_tasks.add_task(run_workflow_background, task_id, request)
    return {"task_id": task_id, "status": "running"}


@app.get("/api/v1/stagehand/workflow/{task_id}")
async def get_workflow_status(task_id: str):
    if task_id in results:
        entry = results[task_id]
        if datetime.now(timezone.utc) - entry["timestamp"] > CLEANUP_THRESHOLD:
            del results[task_id]
            return {"status": "not_found"}
        return entry["data"]
    return {"status": "not_found"}

async def run_multistep_background(task_id: str, request: MultiStepJobRequest):
    try:
        logger.info(f"Running background multi-step on {request.url} with {len(request.instructions)} steps")
        result = await stagehand_service.process_multi_step_instructions(
            url=request.url,
            instructions=request.instructions,
            config={
                "take_screenshots": request.take_screenshots,
                "draw_overlay": request.draw_overlay,
                "stop_on_error": request.stop_on_error
            }
        )
        result["timestamp"] = datetime.now(timezone.utc).isoformat()
        results[task_id] = {
            "data": result,
            "timestamp": datetime.now(timezone.utc)
        }
        logger.info(f"Background multi-step {task_id} completed")
    except Exception as e:
        logger.error(f"Background multi-step {task_id} failed: {e}")
        results[task_id] = {
            "data": {"status": "failed", "error": str(e)},
            "timestamp": datetime.now(timezone.utc)
        }



@app.post("/api/v1/stagehand/multistep",
    tags=["Stagehand"],
    summary="Execute multi-step sequential workflow")
async def execute_multistep(background_tasks: BackgroundTasks, request: MultiStepJobRequest):
    task_id = f"multistep_{datetime.now(timezone.utc).isoformat()}"
    background_tasks.add_task(run_multistep_background, task_id, request)
    return {"task_id": task_id, "status": "running"}

@app.get("/api/v1/stagehand/multistep/{task_id}")
async def get_multistep_status(task_id: str):
    if task_id in results:
        entry = results[task_id]
        if datetime.now(timezone.utc) - entry["timestamp"] > CLEANUP_THRESHOLD:
            del results[task_id]
            return {"status": "not_found"}
        return entry["data"]
    return {"status": "not_found"}

@app.get("/api/v1/stagehand/multistep/{task_id}/stream")
async def stream_multistep_results(task_id: str):
    if task_id not in results:
        return JSONResponse(status_code=404, content={"error": "Task not found"})
    entry = results[task_id]
    if datetime.now(timezone.utc) - entry["timestamp"] > CLEANUP_THRESHOLD:
        del results[task_id]
        return JSONResponse(status_code=404, content={"error": "Task not found"})
    result = entry["data"]
    if not isinstance(result, dict) or "steps" not in result:
        return JSONResponse(status_code=400, content={"error": "Invalid result format"})

    async def generate():
        for step in result["steps"]:
            yield f"data: {json.dumps(step)}\n\n"
            await asyncio.sleep(0.1)  # Simulate streaming delay
        yield "data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/plain")


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
