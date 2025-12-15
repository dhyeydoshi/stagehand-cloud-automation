import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Dict, Any
from config import settings
from extensions.microsoft_cua.factory import register_microsoft_cua


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

            logger.info(f"{env} session created successfully")
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
                logger.info(f"Successfully navigated to {url}")
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

            logger.info("Browserbase configuration verified (will connect on first job)")
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
                        try:
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
                        except Exception as e:
                            logger.warning(f"Failed to take screenshot for element {i + 1}: {e}")

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
        if settings.ENABLE_MICROSOFT_CUA:
            logger.info("Microsoft CUA registered with Stagehand")

        try:
            stagehand = await self._create_session(config)
            page = stagehand.page

            await self._navigate_with_retry(page, url)

            agent_model = settings.AGENT_MODEL_NAME or "microsoft/Fara-7B"
            agent_instructions = config.get("agent_instructions", "You are a helpful web navigation assistant.")

            agent_options = {}
            api_key = settings.MODEL_API_KEY
            if api_key:
                agent_options["apiKey"] = api_key
            # Add API key for non-Microsoft/Fara Cloud models
            if "fara" in agent_model.lower() or "microsoft" in agent_model.lower():
                agent_options["baseURL"] = settings.MODEL_BASE_URL
                register_microsoft_cua()

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
                "execution_method": "agent",
                "agent_model": agent_model
            }

        except Exception as e:
            logger.error(f"Error executing workflow: {e}")
            # Get agent_model from local scope if available, otherwise use default
            model_name = locals().get('agent_model', 'microsoft/Fara-7B')
            return {
                "success": False,
                "error": str(e),
                "error_code": "WORKFLOW_EXECUTION_ERROR",
                "workflow": workflow_instruction,
                "result": None,
                "url": url,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "processing_time": time.time() - start_time,
                "execution_method": "agent",
                "agent_model": model_name
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
            config = config or {}
            logger.info("Creating session for multi-step workflow")
            stagehand = await self._create_session(config)
            page = stagehand.page
            steps_results = []
            stability_interval_ms = max(0, config.get("stability_check_interval_ms", 1000))
            stability_timeout_ms = max(1000, config.get("stability_timeout_ms", 15000))
            stability_extra_wait_ms = max(0, config.get("stability_extra_wait_ms", 2000))
            last_stability_check = 0.0

            async def wait_for_page_stability(
                reason: str = "",
                force: bool = False,
                require_full_load: bool = False
            ):
                nonlocal last_stability_check
                now = time.time()
                if not force and (now - last_stability_check) < (stability_interval_ms / 1000):
                    return

                reason_label = f" before {reason}" if reason else ""
                logger.info(f"Waiting for page stability{reason_label}")

                load_states = ["domcontentloaded"]
                if require_full_load:
                    load_states.append("load")
                load_states.append("networkidle")

                for state in load_states:
                    try:
                        await page.wait_for_load_state(state, timeout=stability_timeout_ms)
                        logger.debug(f"✓ {state} state reached{reason_label}")
                    except Exception as state_error:
                        logger.debug(f"{state} state wait skipped{reason_label}: {state_error}")

                if stability_extra_wait_ms:
                    await asyncio.sleep(stability_extra_wait_ms / 1000)

                last_stability_check = time.time()

            await self._navigate_with_retry(page, url)
            logger.info(f"Navigated to {url}")
            await wait_for_page_stability("initial navigation", force=True, require_full_load=True)
            logger.info("✓ Page stable and ready for instructions")

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
                        await wait_for_page_stability(f"goto step {idx}", force=True, require_full_load=True)
                        step_result["success"] = True

                    elif step_type == "observe":
                        nav_retry_attempted = False
                        while True:
                            try:
                                await wait_for_page_stability(
                                    f"observe step {idx}",
                                    force=nav_retry_attempted,
                                    require_full_load=True
                                )
                                logger.info(f"Calling page.observe with instruction: '{instruction_text}'")

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
                                break
                            except Exception as observe_error:
                                logger.error(f"Observe error: {observe_error}")
                                error_msg = str(observe_error)
                                nav_issue = (
                                    "Execution context was destroyed" in error_msg
                                    or "navigation" in error_msg.lower()
                                )
                                if nav_issue and not nav_retry_attempted:
                                    nav_retry_attempted = True
                                    logger.warning(
                                        "Navigation detected during observe; waiting for page to settle and retrying once"
                                    )
                                    await wait_for_page_stability(
                                        f"observe retry step {idx}",
                                        force=True,
                                        require_full_load=True
                                    )
                                    continue

                                step_result["success"] = False

                                if nav_issue:
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
                                break

                    elif step_type == "act":
                        nav_retry_attempted = False
                        while True:
                            try:
                                await wait_for_page_stability(
                                    f"act step {idx}",
                                    force=nav_retry_attempted,
                                    require_full_load=True
                                )
                                logger.info("Proceeding with observe/act sequence")

                                results = await page.observe(instruction=instruction_text)
                                if results:
                                    await page.act(results[0])
                                    step_result["success"] = True
                                    step_result["data"] = {"action_performed": True}
                                    await wait_for_page_stability(
                                        f"post-act step {idx}",
                                        force=True,
                                        require_full_load=True
                                    )
                                else:
                                    step_result["error"] = "No elements found to act upon"
                                    step_result["error_code"] = "NO_ELEMENTS_FOUND"
                                break
                            except Exception as act_error:
                                error_msg = str(act_error)
                                nav_issue = (
                                    "Execution context was destroyed" in error_msg
                                    or "navigation" in error_msg.lower()
                                )
                                if nav_issue and not nav_retry_attempted:
                                    nav_retry_attempted = True
                                    logger.warning(
                                        "Navigation detected during act; waiting for page to settle and retrying once"
                                    )
                                    await wait_for_page_stability(
                                        f"act retry step {idx}",
                                        force=True,
                                        require_full_load=True
                                    )
                                    continue

                                if nav_issue:
                                    step_result["error"] = f"Page navigation occurred during action: {error_msg}"
                                    step_result["error_code"] = "NAVIGATION_ERROR"
                                else:
                                    step_result["error"] = f"Action failed: {error_msg}"
                                    step_result["error_code"] = "ACTION_ERROR"
                                break

                    elif step_type == "extract":
                        try:
                            await wait_for_page_stability(f"extract step {idx}", require_full_load=True)
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

                    await wait_for_page_stability(f"post step {idx}", force=True)

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

            await wait_for_page_stability("workflow completion", force=True, require_full_load=True)
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
                try:
                    if 'wait_for_page_stability' in locals():
                        await wait_for_page_stability("shutdown cleanup", force=True, require_full_load=True)
                except Exception as final_wait_error:
                    logger.debug(f"Final stability check skipped: {final_wait_error}")
                logger.info("Closing session after workflow")
                await self._close_session(stagehand)
