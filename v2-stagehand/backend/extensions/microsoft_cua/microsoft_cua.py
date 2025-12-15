import base64
import hashlib
import json
import math
import os
import re
import time
from typing import Any, Literal, Optional

from dotenv import load_dotenv
from openai import AsyncOpenAI
from pydantic import TypeAdapter

from stagehand.handlers.cua_handler import CUAHandler
from stagehand.types.agent import (
    AgentAction,
    AgentActionType,
    AgentConfig,
    AgentExecuteOptions,
    AgentResult,
    AgentUsage,
)
from stagehand.agent.client import AgentClient

load_dotenv()


class MicrosoftCUAClient(AgentClient):
    KEY_MAP: dict[str, str] = {
        "ENTER": "Enter",
        "RETURN": "Enter",
        "ESCAPE": "Escape",
        "ESC": "Escape",
        "BACKSPACE": "Backspace",
        "TAB": "Tab",
        "SPACE": " ",
        "DELETE": "Delete",
        "DEL": "Delete",
        "ARROWUP": "ArrowUp",
        "ARROWDOWN": "ArrowDown",
        "ARROWLEFT": "ArrowLeft",
        "ARROWRIGHT": "ArrowRight",
        "ARROW_UP": "ArrowUp",
        "ARROW_DOWN": "ArrowDown",
        "ARROW_LEFT": "ArrowLeft",
        "ARROW_RIGHT": "ArrowRight",
        "UP": "ArrowUp",
        "DOWN": "ArrowDown",
        "LEFT": "ArrowLeft",
        "RIGHT": "ArrowRight",
        "SHIFT": "Shift",
        "CONTROL": "Control",
        "CTRL": "Control",
        "ALT": "Alt",
        "HOME": "Home",
        "END": "End",
        "PAGEUP": "PageUp",
        "PAGEDOWN": "PageDown",
        "PAGE_UP": "PageUp",
        "PAGE_DOWN": "PageDown",
        "PGUP": "PageUp",
        "PGDN": "PageDown",
    }

    MLM_PROCESSOR_IM_CFG = {
        "min_pixels": 3136,
        "max_pixels": 12845056,
        "patch_size": 14,
        "merge_size": 2,
    }
    SAVE_SCREENSHOTS = True
    DEBUG_SCREENSHOTS = True
    SCREENSHOT_DIR = "./downloads"


    def __init__(
            self,
            model: str = "microsoft/Fara-7B",
            instructions: Optional[str] = None,
            config: Optional[AgentConfig] = None,
            logger: Optional[Any] = None,
            handler: Optional[CUAHandler] = None,
            viewport: Optional[dict[str, int]] = None,
            **kwargs,
    ):
        super().__init__(model, instructions, config, logger, handler)

        api_key = None
        base_url = None
        if config and hasattr(config, "options") and config.options:
            api_key = config.options.get("apiKey")
            base_url = config.options.get("baseURL")

        if not api_key:
            api_key = os.getenv("AZURE_API_KEY")
        if not base_url:
            base_url = os.getenv("AZURE_ENDPOINT")

        if not api_key:
            raise ValueError(
                "API key is required.  Please provide it via config.options.apiKey "
                "or AZURE_API_KEY environment variables."
            )

        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)

        self._action_adapter = TypeAdapter(AgentActionType)

        dimensions = (
            (viewport["width"], viewport["height"]) if viewport else (1288, 711)
        )
        self.current_viewport = {"width": dimensions[0], "height": dimensions[1]}

        self.resized_viewport = self._smart_resize(dimensions[0], dimensions[1])
        self._system_prompt_cache = self._generate_system_prompt()

        self.max_images = kwargs.get("max_images", 1)
        self.temperature = kwargs.get("temperature", 0)
        self.api_message_debug = kwargs.get("debug", False)

        self.current_url: Optional[str] = None
        self.facts: list[str] = []

        self.search_count = 0
        self.last_search_query: Optional[str] = None
        self.last_action: Optional[str] = None

    def _log_warning(self, msg: str,  category: str = "agent") -> None:
        if not self.logger:
            return
        if hasattr(self.logger, "warning"):
            self.logger.warning(msg, category=category)
        elif hasattr(self.logger, "warn"):
            self.logger.warn(msg, category=category)
        elif hasattr(self.logger, "info"):
            self.logger.info(f"[WARN] {msg}", category=category)
        else:
            print(f"[WARN] {msg}")


    def _debug_log_screenshot(self, screenshot_base64: str, label: str, step: int) -> None:
        if not self.logger:
            return
        try:
            raw_bytes = base64.b64decode(screenshot_base64)
        except Exception:
            self.logger.error(
                f"Screenshot decode failed for {label} step={step}",
                category="agent",
            )
            return

        size = len(raw_bytes)
        sha = hashlib.sha256(raw_bytes).hexdigest()[:16]
        self.logger.info(
            f"Screenshot [{label}] step={step} bytes={size} sha256={sha}",
            category="agent",
        )

        if self.SAVE_SCREENSHOTS:
            try:
                os.makedirs(self.SCREENSHOT_DIR, exist_ok=True)
                filename = os.path.join(
                    self.SCREENSHOT_DIR,
                    f"{label}_step_{step:03d}.png",
                )
                with open(filename, "wb") as f:
                    f.write(raw_bytes)
                self.logger.info(
                    f"Saved screenshot to {filename}",
                    category="agent",
                )
            except Exception as e:
                self.logger.error(
                    f"Failed to save screenshot for {label} step={step}: {e}",
                    category="agent",
                )


    def _smart_resize(self, width: int, height: int) -> dict[str, int]:
        patch_size = self.MLM_PROCESSOR_IM_CFG["patch_size"]
        merge_size = self.MLM_PROCESSOR_IM_CFG["merge_size"]
        min_pixels = self.MLM_PROCESSOR_IM_CFG["min_pixels"]
        max_pixels = self.MLM_PROCESSOR_IM_CFG["max_pixels"]
        factor = patch_size * merge_size

        def round_by_factor(num: float, f: int) -> int:
            return round(num / f) * f

        def ceil_by_factor(num: float, f: int) -> int:
            return math.ceil(num / f) * f

        def floor_by_factor(num: float, f: int) -> int:
            return math.floor(num / f) * f

        h_bar = max(factor, round_by_factor(height, factor))
        w_bar = max(factor, round_by_factor(width, factor))

        if h_bar * w_bar > max_pixels:
            beta = math.sqrt((height * width) / max_pixels)
            h_bar = floor_by_factor(height / beta, factor)
            w_bar = floor_by_factor(width / beta, factor)
        elif h_bar * w_bar < min_pixels:
            beta = math.sqrt(min_pixels / (height * width))
            h_bar = ceil_by_factor(height * beta, factor)
            w_bar = ceil_by_factor(width * beta, factor)

        return {"width": w_bar, "height": h_bar}

    def _generate_system_prompt(self) -> str:
        width = self.resized_viewport["width"]
        height = self.resized_viewport["height"]

        base_prompt = """You are a helpful assistant that can control a web browser and can SEE the browser window via screenshots. 
You have access to the **computer_use** tool to interact with the screen using mouse and keyboard actions. For every step you MUST do three things, in this order:
- Carefully look at the screenshot and read the visible text, buttons, and controls.
- In a short natural language description BEFORE <tool_call>, explain what you see on screen and quote at least one exact piece of text you can read.
- Then pick ONE action and output it as a <tool_call>.
GROUND RULES:
- Never claim the page is blank unless the screenshot is completely empty or a single solid color.
- If you can see any UI at all, you must quote some visible text. Example: "I see the text 'HOW TO PLAY 2048:' and a 4x4 grid with tiles 4 and 2."
- Do not invent elements that are not visible in the screenshot.
- Use `web_search` at most once per task unless the results page is empty or irrelevant.
- After a `web_search`, you MUST click a relevant search result and open a source page.
- If a URL is provided in the task, navigate to it by clicking the address bar, typing the URL, and pressing Enter. 
- After one scroll, click a visible result title instead of refining the query.
- After clicking, wait briefly for the page to respond before the next action.
- For games or interactive content:  focus on the game area and use appropriate controls.
DATA EXTRACTION:
- When asked to find prices, values, or other data, use `pause_and_memorize_fact` to record each piece of information clearly.
- Format facts as: "Item: Value".
- After memorizing all requested facts, terminate with status="success" and a summary message listing what was found."""
        #
        # if self.instructions:
        #     print('Instructions:', self.instructions)
        #     base_prompt = f"{base_prompt}\n\n{self.instructions}"

        tool_description = f"""The screen's resolution is {width}x{height} pixels. 
Click elements in their center.  Wait for pages to load after navigation."""

        actions_description = """Available actions:
* `left_click`: Click at (x, y) coordinate.
* `type`: Type a string of text on the keyboard (optionally at coordinate, with press_enter option).
* `key`: Performs key down presses on the arguments passed in order, then performs key releases in reverse order. Includes "Enter", "Alt", "Shift", "Tab", "Control", "Backspace", "Delete", "Escape", "ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight", "PageDown", "PageUp", "Shift", etc.
* `mouse_move`: Move the cursor to a specified (x, y) pixel coordinate on the screen.
* `scroll`: Scroll by pixels (positive=up, negative=down).
* `wait`: Wait seconds for changes.
* `web_search`: Search the web with a query.
* `visit`: Navigate to a URL.
* `goto`: Navigate to a URL.
* `history_back`: Go back in browser history.
* `pause_and_memorize_fact`: Memorize a fact for future use.
* `terminate`: End task with status "success" or "failure". """

        tool_schema = {
            "name": "computer_use",
            "description": tool_description,
            "parameters": {
                "type": "object",
                "required": ["action"],
                "properties": {
                    "action": {
                        "type": "string",
                        "description": actions_description,
                        "enum": [
                            "left_click",
                            "type",
                            "key",
                            "mouse_move",
                            "scroll",
                            "wait",
                            "web_search",
                            "visit",
                            "history_back",
                            "pause_and_memorize_fact",
                            "terminate",
                        ],
                    },
                    "coordinate": {
                        "type": "array",
                        "description": "[x, y] pixel coordinates. Required only by `action=left_click`, `action=mouse_move`, and `action=type`.",
                    },
                    "text": {"type": "string", "description": "Text to type. Required only by `action=type`."},
                    "keys": {"type": "array", "description": "Keys to press. Required only by `action=key`."},
                    "press_enter": {"type": "boolean", "description": "Press Enter after typing. Required only by `action=type`."},
                    "pixels": {"type": "number", "description": "Scroll amount. Positive values scroll up, negative values scroll down. Required only by `action=scroll`."},
                    "time": {"type": "number", "description": "Seconds to wait. Required only by `action=wait`."},
                    "query": {"type": "string", "description": "Search query. Required only by `action=web_search`."},
                    "url": {
                        "type": "string",
                        "description": "URL to open. Required only by `action=visit`."
                    },
                    "fact": {
                        "type": "string",
                        "description": "The fact to remember for the future. Required only by `action=pause_and_memorize_fact`.",
                    },
                    "status": {
                        "type": "string",
                        "enum": ["success", "failure"],
                        "description": "The status of the task. Required only by `action=terminate`.",
                    },
                },
            },
        }

        tool_description = json.dumps(tool_schema, indent=2)
        function_call_template = f"""
                <tools>
                {tool_description}
                </tools>
                
                Return your action as: 
                <tool_call>
                {{"name": "computer_use", "arguments": {{... }}}}
                </tool_call>"""

        return f"{base_prompt}\n\n{function_call_template}"

    def key_to_playwright(self, key: str) -> str:
        if not key:
            return key
        return self.KEY_MAP.get(key.upper(), key)

    def format_screenshot(self, screenshot_base64: str) -> dict[str, Any]:
        return {
            "type": "image_url",
            "image_url": {"url": f"data:image/png;base64,{screenshot_base64}"},
        }

    def _format_initial_messages(
            self, instruction: str, screenshot_base64: Optional[str]
    ) -> list[dict[str, Any]]:
        messages: list[dict[str, Any]] = [{
            "role": "system",
            "content": self._system_prompt_cache
        }]

        user_content: list[dict[str, Any]] = []

        if screenshot_base64:
            user_content.append(self.format_screenshot(screenshot_base64))

        task_text = instruction
        if self.current_url:
            task_text = f"Current URL: {self.current_url}\n\nTask: {instruction}"

        user_content.append({"type": "text", "text": task_text})
        messages.append({"role": "user", "content": user_content})

        return messages

    # _TOOL_CALL_RE = re.compile(r"<tool_call>\s*(\{.*?\})\s*</tool_call>", re.DOTALL)
    _TOOL_CALL_BLOCK_RE = re.compile(r"<tool_call>(.*?)</tool_call>", re.DOTALL | re.IGNORECASE)

    def _extract_tool_call_json(self, text: str) -> Optional[str]:
        m = self._TOOL_CALL_BLOCK_RE.search(text)
        return m.group(1).strip() if m else None

    def _strip_tool_call_from_text(self, text: str) -> str:
        return self._TOOL_CALL_BLOCK_RE.sub("", text, count=1).strip()


    def _parse_thoughts_and_action(
            self, response: str
    ) -> tuple[str, dict[str, Any]]:
        default_action = {
            "name": "computer_use",
            "arguments": {"action": "wait", "time": 1}
        }
        tool_json = self._extract_tool_call_json(response)
        if not tool_json:
            self._log_warning(
                f"No <tool_call> in response, using wait. Response: {response[:200]}",
            )
            return response.strip(), default_action
        thoughts = self._strip_tool_call_from_text(response)
        parsed_action = self._parse_json_safely(tool_json)
        if not parsed_action:
            self._log_warning("Could not parse tool_call JSON. Falling back to wait.")
            return thoughts, default_action

        arguments = parsed_action.get("arguments", {}) or {}
        allowed_keys = {
            "action", "coordinate", "text", "keys", "press_enter", "pixels", "time",
            "query", "url", "fact", "status"
        }
        arguments = {k: v for k, v in arguments.items() if k in allowed_keys}

        if "action" not in arguments:
            self._log_warning("Missing 'action' field, defaulting to wait", category="agent")
            arguments["action"] = "wait"
            arguments["time"] = 1

        ALLOWED_ACTIONS = {
            "left_click",
            "type",
            "key",
            "mouse_move",
            "scroll",
            "wait",
            "web_search",
            "visit",
            "history_back",
            "pause_and_memorize_fact",
            "terminate",
        }
        action = arguments.get("action")

        if action not in ALLOWED_ACTIONS:
            self._log_warning(f"Unsupported action '{action}'. Falling back to wait.")
            arguments = {"action": "wait", "time": 1}

        return thoughts, {
            "name": parsed_action.get("name", "computer_use"),
            "arguments": arguments,
        }

    def _parse_json_safely(self, text: str) -> Optional[dict[str, Any]]:

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        fixed = text
        if fixed.startswith("{{"):
            fixed = fixed[1:]
        if fixed.endswith("}}"):
            fixed = fixed[:-1]

        try:
            return json.loads(fixed)
        except json.JSONDecodeError:
            pass

        open_count = text.count("{") - text.count("}")
        if open_count > 0:
            fixed = text + ("}" * open_count)
            try:
                return json.loads(fixed)
            except json.JSONDecodeError:
                pass

        action_match = re.search(r'"action"\s*:\s*"([^"]+)"', text)
        if action_match:
            return {
                "name": "computer_use",
                "arguments": {"action": action_match.group(1)}
            }

        return None

    def _transform_coordinate(self, coordinates: list[int]) -> list[int]:
        if not coordinates or len(coordinates) != 2:
            return coordinates if coordinates else [0, 0]

        x, y = coordinates
        scale_x = self.current_viewport["width"] / self.resized_viewport["width"]
        scale_y = self.current_viewport["height"] / self.resized_viewport["height"]
        return [round(x * scale_x), round(y * scale_y)]

    def _process_provider_response(
            self, response: Any
    ) -> tuple[Optional[AgentAction], Optional[str], bool, Optional[str]]:
        content = response.choices[0].message.content or ""

        self.logger.debug(f"Raw response: {content[: 500]}", category="agent")

        thoughts, function_call = self._parse_thoughts_and_action(content)

        agent_action = self._convert_function_call_to_action(function_call)

        is_complete = function_call["arguments"].get("action") == "terminate"
        status = function_call["arguments"].get("status") if is_complete else None

        final_message = None
        if is_complete:
            final_message = (
                "Task completed successfully."
                if status == "success"
                else "Task completed."
            )

        return agent_action, thoughts, is_complete, final_message

    def _convert_function_call_to_action(
            self, function_call: dict[str, Any]
    ) -> AgentAction:
        args = function_call["arguments"]
        action = args.get("action", "wait")
        reasoning = args.get("thoughts", "")

        self.last_action = action

        if action == "left_click":
            coordinates = self._transform_coordinate(args.get("coordinate", [0, 0]))
            return AgentAction(
                action_type="click",
                action=self._action_adapter.validate_python({
                    "type": "click",
                    "x": coordinates[0],
                    "y": coordinates[1],
                    "button": "left",
                }),
                reasoning=reasoning,
            )

        elif action == "mouse_move":
            coordinates = self._transform_coordinate(args.get("coordinate", [0, 0]))
            return AgentAction(
                action_type="move",
                action=self._action_adapter.validate_python({
                    "type": "move",
                    "x": coordinates[0],
                    "y": coordinates[1],
                }),
                reasoning=reasoning,
            )

        elif action == "type":
            payload: dict[str, Any] = {
                "type": "type",
                "text": args.get("text", ""),
            }
            if "coordinate" in args:
                coordinates = self._transform_coordinate(args["coordinate"])
                payload["x"] = coordinates[0]
                payload["y"] = coordinates[1]
            payload["press_enter_after"] = args.get("press_enter", False)

            return AgentAction(
                action_type="type",
                action=self._action_adapter.validate_python(payload),
                reasoning=reasoning,
            )

        elif action in ("key", "keypress"):
            keys = args.get("keys", [])
            key_mapped_playwright = [self.key_to_playwright(k) for k in keys]
            return AgentAction(
                action_type="keypress",
                action=self._action_adapter.validate_python({
                    "type": "keypress",
                    "keys": key_mapped_playwright,
                }),
                reasoning=reasoning,
            )

        elif action == "scroll":
            pixels = args.get("pixels", 0)
            coordinates = self._transform_coordinate(args.get("coordinate", [
                self.current_viewport["width"] // 2,
                self.current_viewport["height"] // 2
            ]))
            return AgentAction(
                action_type="scroll",
                action=self._action_adapter.validate_python({
                    "type": "scroll",
                    "x": coordinates[0],
                    "y": coordinates[1],
                    "scroll_x": 0,
                    "scroll_y": -pixels,  # FARA:  positive=up, invert for Playwright
                }),
                reasoning=reasoning,
            )
        elif action == "history_back":
            # Use keyboard shortcut Alt+Left Arrow to go back
            return AgentAction(
                action_type="keypress",
                action=self._action_adapter.validate_python({
                    "type": "keypress",
                    "keys": ["Alt", "ArrowLeft"],
                }),
                reasoning=f"{reasoning} (Using Alt+ArrowLeft to go back)",
            )
        elif action == "web_search":
            from urllib.parse import quote

            query = (args.get("query") or "").strip()
            if self.search_count >= 1:
                self._log_warning("Search budget exceeded. Forcing click flow.")
                return AgentAction(
                    action_type="wait",
                    action=self._action_adapter.validate_python({
                        "type": "wait",
                        "milliseconds": 200,
                    }),
                    reasoning="Search budget exceeded; please click a relevant result.",
                )

            if self.last_search_query and query == self.last_search_query:
                self._log_warning("Duplicate search query. Forcing click flow.")
                return AgentAction(
                    action_type="wait",
                    action=self._action_adapter.validate_python({
                        "type": "wait",
                        "milliseconds": 200,
                    }),
                    reasoning="Duplicate search query; please click a relevant result.",
                )

            self.search_count += 1
            self.last_search_query = query

            search_url = f"https://duckduckgo.com/?q={quote(query)}&ia=web"
            return AgentAction(
                action_type="function",
                action=self._action_adapter.validate_python({
                    "type": "function",
                    "name": "goto",
                    "arguments": {"url": search_url},
                }),
                reasoning=reasoning,
            )

        elif action == "visit":
            url = (args.get("url") or "").strip()
            if not url:
                self._log_warning("visit called without url, falling back to wait")
                return AgentAction(
                    action_type="wait",
                    action=self._action_adapter.validate_python({
                        "type": "wait",
                        "milliseconds": 500,
                    }),
                    reasoning=reasoning,
                )

            return AgentAction(
                action_type="function",
                action=self._action_adapter.validate_python({
                    "type": "function",
                    "name": "goto",
                    "arguments": {"url": url},
                }),
                reasoning=reasoning,
            )

        elif action == "wait":
            duration = args.get("time", args.get("duration", 2.0))
            return AgentAction(
                action_type="wait",
                action=self._action_adapter.validate_python({
                    "type": "wait",
                    "milliseconds": int(duration * 1000),
                }),
                reasoning=reasoning,
            )
        elif action == "pause_and_memorize_fact":
            fact = (args.get("fact") or args.get("act") or "").strip()
            if fact:
                self.facts.append(fact)
                self.logger.info(f"Memorized fact: {fact[:200]}", category="agent")
            else:
                if hasattr(self, "_log_warning"):
                    self._log_warning("pause_and_memorize_fact called without fact/act text")

            return AgentAction(
                action_type="wait",
                action=self._action_adapter.validate_python({
                    "type": "wait",
                    "milliseconds": 0,
                }),
                reasoning=reasoning,
            )


        elif action == "terminate":
            return AgentAction(
                action_type="wait",
                action=self._action_adapter.validate_python({
                    "type": "wait",
                    "milliseconds": 0,
                }),
                reasoning=reasoning,
                status=args.get("status", "success"),
            )

        else:
            self._log_warning(f"Unknown action '{action}', using wait", category="agent")
            return AgentAction(
                action_type="wait",
                action=self._action_adapter.validate_python({
                    "type": "wait",
                    "milliseconds": 500,
                }),
                reasoning=reasoning,
            )

    def _format_action_feedback(
            self,
            action: AgentAction,
            action_result: dict,
            new_screenshot_base64: str,
    ) -> list[dict[str, Any]]:
        user_content: list[dict[str, Any]] = []

        if new_screenshot_base64:
            user_content.append(self.format_screenshot(new_screenshot_base64))

        state_hint = ""
        if self.last_action == "web_search":
            state_hint = (
                "STATE: You are on a search results page. "
                "Next action MUST be a left_click on a relevant result title/snippet. "
                "Do NOT call web_search again."
            )

        text = f"{state_hint}\nScreenshot after action."
        if self.current_url:
            url_display = self.current_url[: 80] + "..." if len(self.current_url) > 80 else self.current_url
            text = f"URL: {url_display}\n{text}"

        if not action_result.get("success", True):
            text = f"Action failed:  {action_result.get('error', 'unknown')}\n{text}"

        user_content.append({"type": "text", "text": text})

        return [{"role": "user", "content": user_content}]

    def _trim_history(self, messages: list[dict[str, Any]], keep_last: int = 8) -> list[dict[str, Any]]:
        if len(messages) <= keep_last + 1:
            return messages
        system = [m for m in messages if m.get("role") == "system"]
        rest = [m for m in messages if m.get("role") != "system"]
        return system + rest[-keep_last:]

    def _maybe_remove_old_screenshots(
            self, messages: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        if self.max_images <= 0:
            return messages

        result = []
        image_count = 0

        for msg in reversed(messages):
            if msg.get("role") == "system":
                result.append(msg)
                continue

            content = msg.get("content")
            if isinstance(content, list):
                has_image = any(c.get("type") == "image_url" for c in content)
                if has_image:
                    if image_count < self.max_images:
                        result.append(msg)
                        image_count += 1
                    else:
                        new_content = [c for c in content if c.get("type") != "image_url"]
                        if new_content:
                            result.append({**msg, "content": new_content})
                else:
                    result.append(msg)
            else:
                result.append(msg)

        return list(reversed(result))

    def _resize_b64_png(self, screenshot_base64: str) -> str:
        from PIL import Image
        import io

        raw = base64.b64decode(screenshot_base64)
        img = Image.open(io.BytesIO(raw)).convert("RGB")

        w = self.resized_viewport["width"]
        h = self.resized_viewport["height"]
        if img.size != (w, h):
            img = img.resize((w, h), Image.BICUBIC)

        out = io.BytesIO()
        img.save(out, format="PNG", optimize=True)
        return base64.b64encode(out.getvalue()).decode("utf-8")

    async def run_task(
            self,
            instruction: str,
            max_steps: int,
            options: Optional[AgentExecuteOptions] = None,
    ) -> AgentResult:

        self.logger.info(
            f"FARA CUA starting:  '{instruction[: 100]}...' (max_steps={max_steps})",
            category="agent",
        )

        if not self.handler:
            self.logger.error("CUAHandler not available", category="agent")
            return AgentResult(
                completed=False,
                actions=[],
                message="Internal error: Handler not set.",
                usage=AgentUsage(input_tokens=0, output_tokens=0, inference_time_ms=0),
            )

        await self.handler.inject_cursor()
        self.current_url = self.handler.page.url if self.handler.page else None

        current_screenshot = await self.handler.get_screenshot_base64()
        model_screenshot = self._resize_b64_png(current_screenshot)
        self._debug_log_screenshot(current_screenshot, label="initial", step=0) if self.DEBUG_SCREENSHOTS else None
        messages = self._format_initial_messages(instruction, model_screenshot)

        actions_taken: list[AgentAction] = []
        actions_summary: list[AgentActionType] = []
        total_input_tokens = 0
        total_output_tokens = 0
        total_inference_ms = 0
        final_message: Optional[str] = None
        task_complete = False

        for step in range(max_steps):
            self.logger.info(f"Step {step + 1}/{max_steps}", category="agent")

            messages_to_send = self._trim_history(self._maybe_remove_old_screenshots(messages), keep_last=8)

            if self.api_message_debug:
                self.logger.debug("API Request Messages: " + json.dumps(messages_to_send, indent=2), category="agent")

            start_time = time.perf_counter()
            try:
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=messages_to_send,
                    temperature=self.temperature,
                )
                if self.api_message_debug:
                    self.logger.debug("API Response: " + json.dumps(response.model_dump(), indent=2), category="agent")

            except Exception as e:
                self.logger.error(f"API error:  {e}", category="agent")
                return AgentResult(
                    actions=actions_summary,
                    message=f"API error: {e}",
                    completed=False,
                    usage=AgentUsage(
                        input_tokens=total_input_tokens,
                        output_tokens=total_output_tokens,
                        inference_time_ms=total_inference_ms,
                    ),
                )

            elapsed_ms = int((time.perf_counter() - start_time) * 1000)
            total_inference_ms += elapsed_ms

            if response.usage:
                total_input_tokens += response.usage.prompt_tokens or 0
                total_output_tokens += response.usage.completion_tokens or 0

            agent_action, reasoning, task_complete, model_message = (
                self._process_provider_response(response)
            )

            messages.append({
                "role": "assistant",
                "content": response.choices[0].message.content or ""
            })

            if reasoning:
                self.logger.debug(f"Reasoning: {reasoning[: 200]}", category="agent")
                final_message = reasoning

            if model_message:
                final_message = model_message

            if agent_action:
                actions_taken.append(agent_action)
                if agent_action.action:
                    actions_summary.append(agent_action.action)

                if not task_complete:
                    action_result = await self.handler.perform_action(agent_action)
                    try:
                        if (
                                agent_action.action_type == "function"
                                and getattr(agent_action.action, "type", None) == "function"
                                and getattr(agent_action.action, "name", None) == "goto"
                        ):
                            initial_url = self.current_url or (self.handler.page.url if self.handler.page else "")
                            await self.handler.handle_page_navigation("function.goto", initial_url)
                    except Exception as e:
                        self._log_warning(f"Post-goto navigation settle failed: {e}")

                    current_screenshot = await self.handler.get_screenshot_base64()
                    model_screenshot = self._resize_b64_png(current_screenshot)
                    self._debug_log_screenshot(current_screenshot, label="step", step=step + 1) if self.DEBUG_SCREENSHOTS else None

                    if self.handler.page:
                        self.current_url = self.handler.page.url

                    feedback = self._format_action_feedback(
                        agent_action, action_result, model_screenshot
                    )
                    messages.extend(feedback)

            if task_complete:
                self.logger.info(f"Task complete:  {final_message}", category="agent")
                break

            if not agent_action and not task_complete:
                self.logger.info("No action provided, ending", category="agent")
                final_message = "Model did not provide an action."
                break

        # Format the final message with memorized facts
        if self.facts:
            facts_text = "\n".join(f"- {fact}" for fact in self.facts)
            if final_message:
                final_message = f"{final_message}\n\nExtracted Information:\n{facts_text}"
            else:
                final_message = f"Extracted Information:\n{facts_text}"
        elif not final_message:
            final_message = f"Completed {step + 1} steps."

        return AgentResult(
            actions=actions_summary,
            message=final_message,
            completed=task_complete,
            usage=AgentUsage(
                input_tokens=total_input_tokens,
                output_tokens=total_output_tokens,
                inference_time_ms=total_inference_ms,
            ),
        )