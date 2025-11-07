import sys
from functools import lru_cache
from pathlib import Path

# Add backend directory to Python path
backend_path = Path(__file__).resolve().parent.parent / "backend"
backend_path_str = str(backend_path)

if backend_path_str not in sys.path:
    sys.path.insert(0, backend_path_str)

_backend_settings = None
_backend_config_loaded = False


def _load_backend_config():
    global _backend_settings, _backend_config_loaded

    if _backend_config_loaded:
        return _backend_settings

    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "backend_config",
            backend_path / "frontend_config.py"
        )
        backend_config = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(backend_config)

        _backend_settings = backend_config.settings
        _backend_config_loaded = True
        return _backend_settings

    except Exception as e:
        print(f"Warning: Could not import backend config: {e}")
        print("Using fallback configuration...")
        _backend_config_loaded = False
        return None
# Load backend config once
backend_settings = _load_backend_config()

BACKEND_CONFIG_LOADED = _backend_config_loaded


@lru_cache()
def get_frontend_settings():
    if BACKEND_CONFIG_LOADED and backend_settings:
        return backend_settings
    else:
        raise ImportError("Backend settings not loaded. Using fallback values.")

