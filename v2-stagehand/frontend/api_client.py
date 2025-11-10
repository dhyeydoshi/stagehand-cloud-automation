import streamlit as st
import requests
import logging
from typing import Dict, List, Optional, Any
from functools import wraps

logger = logging.getLogger(__name__)


def handle_api_errors(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except requests.exceptions.Timeout:
            st.error("⏱️ Request timed out. Please try again.")
            return None
        except requests.exceptions.ConnectionError:
            st.error("Cannot connect to backend. Ensure it's running on http://localhost:8000")
            return None
        except requests.exceptions.HTTPError as e:
            st.error(f"❌ API Error: {e.response.status_code} - {e.response.text}")
            return None
        except Exception as e:
            st.error(f"❌ Unexpected error: {str(e)}")
            logger.exception("API call failed")
            return None
    return wrapper


class APIClient:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip('/')
        self.default_timeout = 30
        logger.info(f"Stagehand API Client initialized: {self.base_url}")

    def _request(self, method: str, endpoint: str, timeout: int = None, **kwargs) -> Optional[Any]:
        url = f"{self.base_url}{endpoint}"
        timeout = timeout or self.default_timeout

        try:
            response = requests.request(method, url, timeout=timeout, **kwargs)
            response.raise_for_status()
            return response.json() if response.content else {}
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {method} {url} - {e}")
            raise

    @handle_api_errors
    def health_check(self) -> bool:
        result = self._request('GET', '/health')
        return result is not None

    @handle_api_errors
    def stagehand_action(self, url: str, instruction: str, draw_overlay: bool = False,
                        take_screenshots: bool = True) -> Optional[Dict]:
        return self._request(
            'POST',
            '/api/v1/stagehand/action',
            json={
                "url": url,
                "action_instruction": instruction,
                "draw_overlay": draw_overlay,
                "take_screenshots": take_screenshots
            },
            timeout=60
        )

    @handle_api_errors
    def stagehand_extract(self, url: str, instruction: str, schema_name: str,
                         take_screenshots: bool = True) -> Optional[Dict]:
        return self._request(
            'POST',
            '/api/v1/stagehand/extract',
            json={
                "url": url,
                "instruction": instruction,
                "schema_name": schema_name,
                "take_screenshots": take_screenshots
            },
            timeout=60
        )

    @handle_api_errors
    def stagehand_workflow(self, url: str, instruction: str, max_steps: int = 20,
                          auto_screenshot: bool = True, wait_between: int = 1000) -> Optional[Dict]:
        return self._request(
            'POST',
            '/api/v1/stagehand/workflow',
            json={
                "url": url,
                "workflow_instruction": instruction,
                "max_steps": max_steps,
                "auto_screenshot": auto_screenshot,
                "wait_between_actions": wait_between
            },
            timeout=300
        )

    @handle_api_errors
    def stagehand_multistep(self, url: str, instructions: List[Dict],
                           take_screenshots: bool = True, draw_overlay: bool = False,
                           stop_on_error: bool = False) -> Optional[Dict]:
        return self._request(
            'POST',
            '/api/v1/stagehand/multistep',
            json={
                "url": url,
                "tenant_id": "default",
                "instructions": instructions,
                "take_screenshots": take_screenshots,
                "draw_overlay": draw_overlay,
                "stop_on_error": stop_on_error
            },
            timeout=300
        )

    @st.cache_data(ttl=300, show_spinner=False)
    def get_stagehand_schemas(_self) -> Dict:
        try:
            result = _self._request('GET', '/api/v1/stagehand/schemas')

            if not result:
                return {}

            if isinstance(result, dict):
                if 'schemas' in result:
                    schemas_data = result['schemas']

                    if isinstance(schemas_data, list):
                        return {
                            schema.get('name', f'schema_{i}'): {
                                'name': schema.get('name', f'schema_{i}'),
                                'description': schema.get('description', 'N/A'),
                                'fields': schema.get('fields', [])
                            }
                            for i, schema in enumerate(schemas_data)
                        }

                    return schemas_data if isinstance(schemas_data, dict) else {}

                return result

            elif isinstance(result, list):
                return {
                    schema.get('name', f'schema_{i}'): {
                        'name': schema.get('name', f'schema_{i}'),
                        'description': schema.get('description', 'N/A'),
                        'fields': schema.get('fields', [])
                    }
                    for i, schema in enumerate(result)
                }

            return {}

        except Exception as e:
            logger.error(f"Error fetching schemas: {e}")
            return {}

