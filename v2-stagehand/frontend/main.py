import streamlit as st
import logging
from datetime import datetime, timezone

from frontend_config import get_frontend_settings

frontend_settings = get_frontend_settings()
HEALTH_STATUS_KEY = "backend_health_status"
HEALTH_STATUS_TTL_SECONDS = 30


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

st.set_page_config(
    page_title=f"{frontend_settings.APP_NAME} - Home",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 10px;
        margin-bottom: 2rem;
        color: white;
        text-align: center;
    }
    .stButton>button {
        border-radius: 8px;
        transition: all 0.3s;
    }
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0,0,0,0.2);
    }
    .info-box {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #667eea;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

from api_client import APIClient
from stagehand_features import StagehandFeaturesUI


def init_session_state():
    if 'api_client' not in st.session_state:
        st.session_state.api_client = APIClient()


def _seconds_since(timestamp: datetime) -> float:
    return (datetime.now(timezone.utc) - timestamp).total_seconds()


def get_cached_health_status():
    cache = st.session_state.get(HEALTH_STATUS_KEY)
    if cache:
        age = _seconds_since(cache["checked_at"])
        if age < HEALTH_STATUS_TTL_SECONDS:
            return cache["status"], age

    status = st.session_state.api_client.health_check()
    st.session_state[HEALTH_STATUS_KEY] = {
        "status": status,
        "checked_at": datetime.now(timezone.utc)
    }
    return status, 0.0


def invalidate_health_cache():
    if HEALTH_STATUS_KEY in st.session_state:
        del st.session_state[HEALTH_STATUS_KEY]


def render_sidebar():
    with st.sidebar:
        st.markdown(f"""
        <div class="main-header">
            <h1>{frontend_settings.APP_NAME}</h1>
            <p>Browser Automation with AI</p>
        </div>
        """, unsafe_allow_html=True)

        backend_online, age_seconds = get_cached_health_status()
        if backend_online:
            st.success("Backend Connected")
        else:
            st.error("Backend Offline")
            st.info("Start backend:\n`python backend/main.py`")
        cache_message = (
            f"Status cached {int(age_seconds)}s ago "
            f"(auto-refresh every {HEALTH_STATUS_TTL_SECONDS}s)"
        )
        st.caption(cache_message)

        if st.button("Refresh backend status", key="refresh_backend_status", width='stretch'):
            invalidate_health_cache()
            st.rerun()

        st.divider()

        st.subheader("About Stagehand")
        st.markdown("""
        **Stagehand** is an AI-powered browser automation tool that understands natural language.
        
        **Key Features:**
        - **Quick Actions** - Single atomic actions
        - **Agent Workflows** - Complex multi-step tasks
        - **Multi-Step** - Sequential instructions
        
        **Powered by:**
        - Stagehand backend for orchestration
        - Browserbase for browser infrastructure
        - AI models for understanding and execution
        """)

        st.divider()

        with st.expander("Configuration", expanded=False):
            st.markdown("""
            **Required Environment Variables:**
            ```
            STAGEHAND_ENV=BROWSERBASE or LOCAL
            BROWSERBASE_API_KEY=your_key (if using BROWSERBASE)
            BROWSERBASE_PROJECT_ID=your_project (if using BROWSERBASE)
            MODEL_API_KEY=your_model_key
            MODEL_NAME=your_model_name
            ```
            
            Set these in `backend/.env` file.
            """)


        with st.expander("Tips & Best Practices", expanded=False):
            st.markdown("""
            **Keep actions atomic:**
            - "Click the sign in button"
            - NOT: "Sign in to the website"
            
            **Be specific:**
            - "Type 'hello' into the search box"
            - NOT: "Search for something"
            
            **Use Multi-Step for sequences:**
            - Step 1: "Click filters"
            - Step 2: "Select Electronics"
            - Step 3: "Click apply"
            
            **Use Agent for complex tasks:**
            - "Navigate to jobs and apply to first engineer position"
            """)


def render_home():
    st.markdown(f"""
    <div class="main-header">
        <h1>{frontend_settings.APP_NAME}-v{frontend_settings.VERSION}</h1>
        <p>Automate your browser with natural language</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("""
        ### Quick Actions
        Perform single, atomic actions on web pages.
        - Observe elements before acting
        - Click, type, select with AI
        - Visual overlay support
        
        **Example:** "Click the sign in button"
        """)

        st.markdown("""
        ### Agent Workflows
        Let AI handle complex multi-step tasks autonomously.
        - Autonomous navigation
        - Smart decision making
        - Up to 100 steps
        
        **Example:** "Apply to first job with mock data"
        """)

    with col2:
        st.markdown("""
        ### Multi-Step Workflows
        Build sequential workflows with full control.
        - Step-by-step execution
        - Custom wait times
        - Screenshot support
        
        **Example:** Goto → Filter → Extract
        """)

    st.markdown("---")

    st.subheader("Quick Start")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.info("""
        **1. Choose a Feature**
        
        Click "Launch Stagehand" below to access all AI automation features.
        """)

    with col2:
        st.info("""
        **2. Enter Details**
        
        Provide the target URL and your instruction in natural language.
        """)

    with col3:
        st.info("""
        **3. Execute & View**
        
        Click execute and watch AI automate your task. Results shown instantly.
        """)

    st.markdown("---")

    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        if st.button("Launch Stagehand", type="primary", width='stretch'):
            st.session_state.show_features = True
            st.rerun()


def main():
    init_session_state()

    render_sidebar()

    if 'show_features' not in st.session_state:
        st.session_state.show_features = False

    try:
        if st.session_state.show_features:
            stagehand_ui = StagehandFeaturesUI(st.session_state.api_client)
            stagehand_ui.render()

            st.markdown("---")
            if st.button("Back to Home"):
                st.session_state.show_features = False
                st.rerun()
        else:
            render_home()

    except Exception as e:
        st.error(f"An error occurred: {str(e)}")
        logger.exception("Error in main app")

        if st.button("Refresh Page"):
            st.rerun()


if __name__ == "__main__":
    main()

