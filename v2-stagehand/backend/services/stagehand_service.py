import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Dict, Any
from config import settings


logger = logging.getLogger(__name__)


class StagehandService:
    def __init__(self):
        pass

    async def _create_session(self, config: Dict[str, Any] = None):
        try:
            import os
            from stagehand import Stagehand, StagehandConfig

            env = settings.STAGEHAND_ENV
            env = env.upper()

            if env not in ["LOCAL", "BROWSERBASE"]:
                raise ValueError(f"Invalid environment: {env}. Must be 'LOCAL' or 'BROWSERBASE'")

            logger.info(f"Creating new {env} session")

            using_openrouter = (
                settings.MODEL_BASE_URL and "openrouter" in settings.MODEL_BASE_URL.lower()
            )

            config_params: Dict[str, Any] = {
                "env": env,
                "verbose": settings.VERBOSE,
                "dom_settle_timeout_ms": settings.DOM_SETTLE_TIMEOUT_MS,
                "self_heal": settings.SELF_HEAL,
                "headless": settings.HEADLESS,
                "system_prompt": "You are a browser automation assistant that helps users navigate websites effectively.",
            }


            if env == "BROWSERBASE":

                config_params["api_key"] = settings.BROWSERBASE_API_KEY
                config_params["project_id"] = settings.BROWSERBASE_PROJECT_ID

            elif env == "LOCAL":
                config_params["local_browser_launch_options"] = {
                    "viewport": {"width": 1280, "height": 720},
                    "headless": settings.HEADLESS,
                    # "args": [
                    #     "--no-sandbox",
                    #     "--disable-setuid-sandbox",
                    #     "--disable-web-security",
                    #     "--allow-running-insecure-content",
                    # ]
                }

            if settings.MODEL_NAME:
                config_params["model_name"] = settings.MODEL_NAME
            if settings.MODEL_API_KEY:
                config_params["model_api_key"] = settings.MODEL_API_KEY

            if using_openrouter and settings.MODEL_BASE_URL:
                try:
                    config_params["model_client_options"] = {
                        "api_base": settings.MODEL_BASE_URL
                    }
                    logger.info(f"Using OpenRouter base URL: {settings.MODEL_BASE_URL}")
                except Exception as e:
                    logger.warning(f"Could not set model_client_options: {e}")

            logger.info(f"Initializing Stagehand with model: {config_params.get('model_name')}")
            logger.info(f"Environment mode: {env}")

            stagehand_config = StagehandConfig(**config_params)
            stagehand = Stagehand(stagehand_config)
            await stagehand.init()

            logger.info(f"✓ {env} session created successfully")
            return stagehand

        except ValueError as ve:
            logger.error(f"Configuration error: {ve}")
            raise

        except Exception as e:
            logger.error(f"Failed to create session: {e}")
            raise

    async def _close_session(self, stagehand):
        if not stagehand:
            return

        try:
            if hasattr(stagehand, 'close'):
                await stagehand.close()
                logger.info("✓ Session closed successfully")
            else:
                logger.warning("Stagehand instance has no close method")
        except Exception as e:
            logger.error(f"Error closing session: {e}")

    async def _navigate_with_retry(self, page, url: str, max_retries: int = 3) -> bool:
        timeout = settings.PAGE_NAVIGATION_TIMEOUT_MS

        for attempt in range(max_retries):
            try:
                logger.info(f"Navigating to {url} (attempt {attempt + 1}/{max_retries}, timeout: {timeout}ms)")
                await page.goto(url, timeout=timeout, wait_until="domcontentloaded")
                logger.info(f"✓ Successfully navigated to {url}")
                return True
            except Exception as e:
                error_msg = str(e)
                logger.warning(f"Navigation attempt {attempt + 1} failed: {error_msg}")

                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
                    logger.info(f"Retrying in {wait_time} seconds...")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"Failed to navigate to {url} after {max_retries} attempts")
                    raise Exception(f"Navigation timeout: Failed to load {url} after {max_retries} attempts. Last error: {error_msg}")

        return False

    async def test_connection(self) -> bool:
        try:
            if not settings.BROWSERBASE_API_KEY and settings.STAGEHAND_ENV == "BROWSERBASE":
                logger.warning("BROWSERBASE_API_KEY not configured")
                return False
            if not settings.BROWSERBASE_PROJECT_ID and settings.STAGEHAND_ENV == "BROWSERBASE":
                logger.warning("BROWSERBASE_PROJECT_ID not configured")
                return False
            if not settings.MODEL_API_KEY:
                logger.warning("MODEL_API_KEY not configured")
                return False

            logger.info("✓ Browserbase configuration verified (will connect on first job)")
            return True

        except Exception as e:
            logger.error(f"Configuration test failed: {e}")
            return False

    async def perform_action_with_observe(
        self,
        url: str,
        action_instruction: str,
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        start_time = time.time()
        stagehand = None

        try:
            stagehand = await self._create_session(config)
            page = stagehand.page

            await self._navigate_with_retry(page, url)

            draw_overlay = config.get("draw_overlay", False)
            results = await page.observe(
                instruction=action_instruction,
                draw_overlay=draw_overlay
            )

            if results:
                logger.info(f"Observed {len(results)} elements, executing action: {action_instruction}")
                await page.act(results[0])

                artifacts = []
                if config.get("take_screenshots", False):
                    import base64
                    for i, element in enumerate(results):
                        locator = page.locator(element.selector)
                        await locator.scroll_into_view_if_needed()
                        element_screenshot_bytes = await locator.screenshot()
                        element_screenshot_b64 = base64.b64encode(element_screenshot_bytes).decode('utf-8')
                        artifacts.append({
                            "type": "screenshot",
                            "data": element_screenshot_b64,
                            "format": "png",
                            "description": element.description or f"Screenshot of observed element {i + 1}"
                        })

                return {
                    "success": True,
                    "action": action_instruction,
                    "observed_elements": len(results),
                    "artifacts": artifacts,
                    "url": url,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "processing_time": time.time() - start_time
                }
            else:
                return {
                    "success": False,
                    "error": "No elements observed for the given instruction",
                    "error_code": "NO_ELEMENTS_FOUND",
                    "action": action_instruction,
                    "observed_elements": 0,
                    "artifacts": [],
                    "url": url,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "processing_time": time.time() - start_time
                }

        except Exception as e:
            logger.error(f"Error performing action: {e}")
            return {
                "success": False,
                "error": str(e),
                "error_code": "ACTION_EXECUTION_ERROR",
                "action": action_instruction,
                "observed_elements": 0,
                "artifacts": [],
                "url": url,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "processing_time": time.time() - start_time
            }

        finally:
            # Always close session
            if stagehand:
                await self._close_session(stagehand)

    async def extract_with_schema(
        self,
        url: str,
        instruction: str,
        schema: Any,
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        start_time = time.time()
        stagehand = None

        try:
            stagehand = await self._create_session(config)
            page = stagehand.page

            await self._navigate_with_retry(page, url)

            data = await page.extract(
                instruction=instruction,
                schema=schema
            )

            artifacts = []
            if config.get("take_screenshots", False):
                import base64
                screenshot_bytes = await page.screenshot()
                screenshot_b64 = base64.b64encode(screenshot_bytes).decode('utf-8')
                artifacts.append({
                    "type": "screenshot",
                    "data": screenshot_b64,
                    "format": "png"
                })

            return {
                "success": True,
                "data": data.model_dump() if hasattr(data, 'model_dump') else data,
                "schema": schema.__name__ if hasattr(schema, '__name__') else str(schema),
                "instruction": instruction,
                "artifacts": artifacts,
                "url": url,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "processing_time": time.time() - start_time
            }

        except Exception as e:
            logger.error(f"Error extracting with schema: {e}")
            return {
                "success": False,
                "error": str(e),
                "error_code": "EXTRACTION_ERROR",
                "data": {},
                "schema": schema.__name__ if hasattr(schema, '__name__') else str(schema),
                "instruction": instruction,
                "artifacts": [],
                "url": url,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "processing_time": time.time() - start_time
            }

        finally:
            if stagehand:
                await self._close_session(stagehand)

    async def execute_workflow_with_agent(
        self,
        url: str,
        workflow_instruction: str,
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        start_time = time.time()
        stagehand = None

        try:
            stagehand = await self._create_session(config)
            page = stagehand.page

            await self._navigate_with_retry(page, url)

            agent_model = 'gemini-2.5-computer-use-preview-10-2025'
            agent_instructions = config.get("agent_instructions", "You are a helpful web navigation assistant.")

            api_key = settings.MODEL_API_KEY

            agent_options = {}
            if api_key:
                agent_options["apiKey"] = api_key

            agent = stagehand.agent(
                model=agent_model,
                instructions=agent_instructions,
                options=agent_options
            )

            max_steps = config.get("max_steps", 20)
            auto_screenshot = config.get("auto_screenshot", True)
            wait_between_actions = config.get("wait_between_actions", 45000)

            result = await agent.execute(
                instruction=workflow_instruction,
                max_steps=max_steps,
                auto_screenshot=auto_screenshot,
                wait_between_actions=wait_between_actions
            )

            return {
                "success": True,
                "workflow": workflow_instruction,
                "result": result,
                "url": url,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "processing_time": time.time() - start_time,
                "execution_method": "agent"
            }

        except Exception as e:
            logger.error(f"Error executing workflow: {e}")
            return {
                "success": False,
                "error": str(e),
                "error_code": "WORKFLOW_EXECUTION_ERROR",
                "workflow": workflow_instruction,
                "result": None,
                "url": url,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "processing_time": time.time() - start_time,
                "execution_method": "agent"
            }

        finally:
            if stagehand:
                await self._close_session(stagehand)


    async def process_multi_step_instructions(
        self,
        url: str,
        instructions: list,
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        start_time = time.time()
        stagehand = None

        try:
            logger.info("Creating session for multi-step workflow")
            stagehand = await self._create_session(config)
            page = stagehand.page
            steps_results = []

            await self._navigate_with_retry(page, url)
            logger.info(f"Navigated to {url}")

            # Wait for page to be fully stable - comprehensive loading strategy
            logger.info("Waiting for page to fully load (content, scripts, CSS)...")

            try:
                await page.wait_for_load_state("domcontentloaded", timeout=60000)
                logger.info("✓ DOM content loaded")
            except Exception as e:
                logger.warning(f"DOM content loaded timeout: {e}")

            try:
                await page.wait_for_load_state("load", timeout=20000)
                logger.info("✓ All resources loaded")
            except Exception as e:
                logger.warning(f"Load state timeout: {e}")

            # Step 3: Wait for network to be idle (no ongoing requests)
            try:
                await page.wait_for_load_state("networkidle", timeout=15000)
                logger.info("✓ Network idle (no active requests)")
            except Exception as e:
                logger.warning(f"Network idle timeout: {e}, continuing anyway")

            logger.info("Waiting additional 5 seconds for JavaScript and dynamic content...")
            await asyncio.sleep(5)

            logger.info("✓ Page fully loaded and stable")

            for idx, instruction in enumerate(instructions, 1):
                step_start = time.time()
                if hasattr(instruction, 'instruction_type'):
                    step_type = instruction.instruction_type
                    instruction_text = instruction.instruction_text
                    wait_after = instruction.wait_after
                else:
                    step_type = instruction.get("instruction_type", "act")
                    instruction_text = instruction.get("instruction_text", "")
                    wait_after = instruction.get("wait_after", 1000)

                logger.info(f"Processing step {idx}: {step_type} - {instruction_text}")

                step_result = {
                    "step_number": idx,
                    "instruction_type": step_type,
                    "instruction_text": instruction_text,
                    "success": False,
                    "data": None,
                    "screenshot": None,
                    "error": None,
                    "error_code": None,
                    "execution_time": 0,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }

                try:
                    if step_type == "goto":
                        await page.goto(instruction_text)
                        step_result["success"] = True

                    elif step_type == "observe":
                        try:
                            logger.info(f"Calling page.observe with instruction: '{instruction_text}'")

                            # Wait for page to be stable before observing - comprehensive check
                            logger.info("Ensuring page stability before observe operation...")
                            try:
                                await page.wait_for_load_state("domcontentloaded", timeout=8000)
                                logger.info("✓ DOM ready for observe")
                            except Exception as wait_error:
                                logger.warning(f"DOM wait failed: {wait_error}")

                            try:
                                await page.wait_for_load_state("networkidle", timeout=8000)
                                logger.info("✓ Network idle for observe")
                            except Exception as wait_error:
                                logger.warning(f"Network idle wait failed: {wait_error}")

                            # Additional wait for dynamic content and JavaScript
                            await asyncio.sleep(2)
                            logger.info("✓ Page stable, proceeding with observe")

                            results = await page.observe(
                                instruction=instruction_text,
                                draw_overlay=config.get("draw_overlay", False)
                            )
                            step_result["success"] = True
                            step_result["data"] = {
                                "observed_elements": len(results),
                                "elements_found": len(results) > 0
                            }
                            logger.info(f"Observe found {len(results)} elements")
                        except Exception as observe_error:
                            logger.error(f"Observe error: {observe_error}")
                            step_result["success"] = False
                            error_msg = str(observe_error)

                            if "Execution context was destroyed" in error_msg or "navigation" in error_msg.lower():
                                step_result["error"] = (
                                    f"Page navigation occurred during observe: {error_msg}. "
                                    "This usually happens when:\n"
                                    "1. The page automatically redirected\n"
                                    "2. A popup or modal appeared\n"
                                    "3. The page is still loading\n"
                                    "Try: Add a 'wait' step before observe, or increase wait_after time"
                                )
                                step_result["error_code"] = "NAVIGATION_ERROR"
                            elif "Server returned error" in error_msg:
                                step_result["error"] = (
                                    f"Stagehand AI model error: {error_msg}. "
                                    "Possible causes:\n"
                                    "1. Missing or invalid MODEL_API_KEY in .env\n"
                                    "2. MODEL_NAME not supported or incorrectly configured\n"
                                    "3. Page content too complex for the instruction\n"
                                    "4. Network issues with AI provider\n"
                                    f"Current config: MODEL_NAME={settings.MODEL_NAME}, "
                                    f"API_KEY={'set' if settings.MODEL_API_KEY else 'NOT SET'}"
                                )
                                step_result["error_code"] = "AI_MODEL_ERROR"
                            else:
                                step_result["error"] = f"Observe failed: {error_msg}"
                                step_result["error_code"] = "OBSERVE_ERROR"

                    elif step_type == "act":
                        try:
                            # Wait for page stability before acting - comprehensive check
                            logger.info("Ensuring page stability before act operation...")
                            try:
                                await page.wait_for_load_state("domcontentloaded", timeout=8000)
                                logger.info("✓ DOM ready for act")
                            except Exception as wait_error:
                                logger.warning(f"DOM wait failed: {wait_error}")

                            try:
                                await page.wait_for_load_state("networkidle", timeout=8000)
                                logger.info("✓ Network idle for act")
                            except Exception as wait_error:
                                logger.warning(f"Network idle wait failed: {wait_error}")

                            # Additional wait for dynamic content
                            await asyncio.sleep(2)
                            logger.info("✓ Page stable, proceeding with act")

                            results = await page.observe(instruction=instruction_text)
                            if results:
                                await page.act(results[0])
                                step_result["success"] = True
                                step_result["data"] = {"action_performed": True}
                            else:
                                step_result["error"] = "No elements found to act upon"
                                step_result["error_code"] = "NO_ELEMENTS_FOUND"
                        except Exception as act_error:
                            error_msg = str(act_error)
                            if "Execution context was destroyed" in error_msg or "navigation" in error_msg.lower():
                                step_result["error"] = f"Page navigation occurred during action: {error_msg}"
                                step_result["error_code"] = "NAVIGATION_ERROR"
                            else:
                                step_result["error"] = f"Action failed: {error_msg}"
                                step_result["error_code"] = "ACTION_ERROR"

                    elif step_type == "extract":
                        try:
                            logger.info(f"Calling page.extract with instruction: '{instruction_text}'")
                            extracted_data = await page.extract(instruction_text)

                            if extracted_data is None:
                                step_result["success"] = False
                                step_result["error"] = "Extraction returned no data"
                                step_result["error_code"] = "NO_DATA_EXTRACTED"
                            elif isinstance(extracted_data, dict):
                                step_result["success"] = True
                                step_result["data"] = extracted_data
                            elif isinstance(extracted_data, str):
                                step_result["success"] = True
                                step_result["data"] = {"extracted_text": extracted_data}
                            elif hasattr(extracted_data, 'model_dump'):
                                step_result["success"] = True
                                step_result["data"] = extracted_data.model_dump()
                            else:
                                step_result["success"] = True
                                step_result["data"] = {"content": str(extracted_data)}

                        except Exception as extract_error:
                            import traceback
                            error_tb = traceback.format_exc()
                            logger.error(f"Extract error: {extract_error}")
                            logger.error(f"Extract traceback:\n{error_tb}")

                            error_msg = str(extract_error)
                            if "Server returned error" in error_msg:
                                step_result["error"] = f"Stagehand server error: {error_msg}."
                                step_result["error_code"] = "AI_MODEL_ERROR"
                            else:
                                step_result["error"] = f"Extraction failed: {str(extract_error)}"
                                step_result["error_code"] = "EXTRACTION_ERROR"

                            step_result["success"] = False
                            step_result["data"] = None

                    elif step_type == "wait":
                        wait_ms = int(instruction_text) if instruction_text.isdigit() else wait_after
                        await asyncio.sleep(wait_ms / 1000)
                        step_result["success"] = True
                        step_result["data"] = {"waited_ms": wait_ms}

                    elif step_type == "screenshot":
                        import base64
                        screenshot_bytes = await page.screenshot()
                        screenshot_b64 = base64.b64encode(screenshot_bytes).decode('utf-8')
                        step_result["success"] = True
                        step_result["screenshot"] = screenshot_b64
                        step_result["data"] = {"screenshot_taken": True}

                    if config.get("take_screenshots", False) and step_type != "screenshot":
                        try:
                            import base64
                            screenshot_bytes = await page.screenshot()
                            step_result["screenshot"] = base64.b64encode(screenshot_bytes).decode('utf-8')
                        except Exception as e:
                            logger.warning(f"Screenshot failed for step {idx}: {e}")

                    if wait_after > 0:
                        await asyncio.sleep(wait_after / 1000)

                except Exception as e:
                    import traceback
                    error_details = traceback.format_exc()
                    logger.error(f"Error in step {idx}: {e}")
                    logger.error(f"Traceback: {error_details}")
                    step_result["error"] = str(e)
                    step_result["error_code"] = "STEP_EXECUTION_ERROR"
                    step_result["success"] = False

                    if config.get("stop_on_error", False):
                        steps_results.append(step_result)
                        break

                finally:
                    step_result["execution_time"] = time.time() - step_start
                    steps_results.append(step_result)

            all_success = all(step["success"] for step in steps_results)

            import uuid
            job_id = f"job_{uuid.uuid4().hex[:12]}"

            end_time = datetime.now(timezone.utc)

            return {
                "job_id": job_id,
                "url": url,
                "success": all_success,
                "total_steps": len(instructions),
                "completed_steps": len(steps_results),
                "steps": steps_results,
                "total_execution_time": time.time() - start_time,
                "started_at": datetime.fromtimestamp(start_time, tz=timezone.utc).isoformat(),
                "completed_at": end_time.isoformat()
            }

        except Exception as e:
            logger.error(f"Error in multi-step processing: {e}")
            import uuid
            job_id = f"job_{uuid.uuid4().hex[:12]}"
            end_time = datetime.now(timezone.utc)

            return {
                "job_id": job_id,
                "url": url,
                "success": False,
                "error": str(e),
                "error_code": "MULTISTEP_PROCESSING_ERROR",
                "total_steps": len(instructions),
                "completed_steps": 0,
                "steps": [],
                "total_execution_time": time.time() - start_time,
                "started_at": datetime.fromtimestamp(start_time, tz=timezone.utc).isoformat(),
                "completed_at": end_time.isoformat()
            }

        finally:
            if stagehand:
                logger.info("Closing session after workflow")
                await self._close_session(stagehand)
