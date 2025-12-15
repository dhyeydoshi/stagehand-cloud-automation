# Stagehand AI Automation Platform

> AI-powered browser automation platform with natural language control. Perform web actions, extract structured data, and execute autonomous workflows using simple English instructions. Built with Python 3.12, FastAPI, Streamlit, and Stagehand.

[![Python 3.12](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.121.0-green.svg)](https://fastapi.tiangolo.com/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.50.0+-red.svg)](https://streamlit.io/)
[![Stagehand](https://img.shields.io/badge/Stagehand-0.5.5+-purple.svg)](https://github.com/browserbase/stagehand-python)

---


## Table of Contents

- [Quick Start](#quick-start) - Get up and running in 5 minutes
- [Usage Examples](#usage-examples) - Code examples for all features
- [Agent Models & Data Extraction](#agent-models--data-extraction) - Learn about available AI models
- [Architecture](#architecture) - System design and data flow

---

## What You Can Do

### AI-Powered Browser Automation
- **Natural Language Actions** - `"Click the sign in button"` - No CSS selectors needed
- **Smart Observation** - AI identifies elements before acting - See what it "sees"
- **Structured Data Extraction** - Extract with Pydantic schemas or simple instructions
- **Autonomous Agents** - Execute complex multistep workflows automatically
- **Microsoft CUA Support** - Integration with Microsoft Computer Use Agent (Fara-7B model)
- **Multi-Step Workflows** - Chain sequential actions with full control
- **Self-Healing** - Automatically adapts when page structure changes

### Core Capabilities
- **Session-per-Request** - Fresh browser for each operation (cost-optimized)
- **Real-time Streaming** - See live logs and progress
- **Screenshot Support** - Visual verification of actions with overlay
- **Error Recovery** - Graceful error handling with detailed messages
- **Type-Safe** - Pydantic validation throughout
- **Production-Ready** - Standardized error codes, monitoring support
- **Extensible Architecture** - Custom agent integration via extension system
- **Multi-Model Support** - Google Gemini, Microsoft CUA, OpenAI, Anthropic
---

## Quick Start

### Prerequisites
1. **Install Python 3.12+**
   - Download from https://www.python.org/downloads/
   - Verify: `python --version`

2. **Get API Keys**
   - Browserbase: https://www.browserbase.com/ (API key + Project ID)
   - Google AI Studio: https://aistudio.google.com/apikey (API key)

3. **Understanding Model Architecture**
   - **Normal LLM**: Used for single-step actions and multi-step workflows
     - Best for: Precise browser actions, data extraction with schemas
     - Example models: Google Gemini Flash, GPT-4, Claude
   - **CUA (Computer Use Agent)**: Used for autonomous agent workflows
     - Best for: Complex multi-step tasks, autonomous navigation
     - Example models: Microsoft Fara-7B, Gemini Computer Use Preview
   - Both can be configured separately or use the same model

4. **Optional**
   - Docker (for containerized deployment)
   - Azure/AWS account (for cloud deployment)


### 1. Clone and Setup

```bash
# Clone repository
git clone <your-repo-url>
cd v2-stagehand

# Create virtual environment (ONE venv for both backend and frontend)
python -m venv <env_name>

# Activate virtual environment:
<env_name>\Scripts\activate.bat


# Setup backend config
cd backend
cp .env.example .env
```

### 2. Configure Environment

Edit `backend/.env` with your credentials:

**Option A: LOCAL Mode** (runs browser locally)
```env
# Set to LOCAL mode
STAGEHAND_ENV=LOCAL

# No Browserbase keys needed
BROWSERBASE_API_KEY=
BROWSERBASE_PROJECT_ID=

# Required - Normal LLM (for single-step and multi-step workflows)
MODEL_API_KEY=your_google_ai_api_key
MODEL_NAME=gemini-2.5-flash
MODEL_BASE_URL=

# Optional - CUA Model (for agent workflows)
# If not set, agent workflows will use the normal LLM configuration above
AGENT_MODEL_NAME=microsoft/Fara-7B
AGENT_MODEL_API_KEY=your_azure_openai_api_key  # Falls back to MODEL_API_KEY if not set
AGENT_MODEL_BASE_URL=your_azure_openai_endpoint  # Falls back to MODEL_BASE_URL if not set
ENABLE_MICROSOFT_CUA=True  # Set to True to enable Microsoft CUA
```

**Option B: BROWSERBASE Mode** (Cloud browser, production-ready)
```env
# Set to BROWSERBASE mode
STAGEHAND_ENV=BROWSERBASE

# Required - Browserbase credentials
BROWSERBASE_API_KEY=your_browserbase_api_key
BROWSERBASE_PROJECT_ID=your_browserbase_project_id

# Required - Normal LLM (for single-step and multi-step workflows)
MODEL_API_KEY=your_google_ai_api_key
MODEL_NAME=gemini-2.5-flash
MODEL_BASE_URL=

# Optional - CUA Model (for agent workflows)
# If not set, agent workflows will use the normal LLM configuration above
AGENT_MODEL_NAME=microsoft/Fara-7B
AGENT_MODEL_API_KEY=your_azure_openai_api_key  # Falls back to MODEL_API_KEY if not set
AGENT_MODEL_BASE_URL=your_azure_openai_endpoint  # Falls back to MODEL_BASE_URL if not set
ENABLE_MICROSOFT_CUA=True  # Set to True to enable Microsoft CUA

# Application Settings
ENVIRONMENT=development
DEBUG=True
HOST=0.0.0.0
PORT=8000
LOG_LEVEL=INFO
VERBOSE=2
```

### 3. Install Dependencies

```bash
# Install all dependencies (with venv activated from step 1)
# Make sure you're in the project root directory: v2-stagehand/

# Install backend dependencies
pip install -r backend/requirements.txt

# Install frontend dependencies
pip install -r frontend/requirements.txt
```

### 4. Run Application

**Option 1: Run Separately** (Recommended for development)
```bash
# Terminal 1 - Backend (with venv activated)
cd backend
python main.py
# Backend runs on http://127.0.0.1:8000

# Terminal 2 - Frontend (activate same venv in new terminal)
cd frontend
streamlit run main.py
# Frontend runs on http://127.0.0.1:8501
```

### 5. Access Application

- **Frontend Dashboard**: http://127.0.0.1:8501
- **Backend API**: http://127.0.0.1:8000
- **API Documentation**: http://127.0.0.1:8000/docs
- **Health Check**: http://127.0.0.1:8000/health


---

## Configuration Examples

### Example 1: Same Model for All Workflows
Use Google Gemini for both normal operations and agent workflows:

```env
# Normal LLM (single-step and multi-step)
MODEL_API_KEY=your_google_api_key
MODEL_NAME=google/gemini-2.5-flash
MODEL_BASE_URL=

ENABLE_MICROSOFT_CUA=False
AGENT_MODEL_NAME=google/gemini-2.5-computer-use-preview-10-2025
AGENT_MODEL_API_KEY=your_google_api_key
AGENT_MODEL_BASE_URL=
```

### Example 2: Separate Models (Recommended)
Use Gemini Flash for normal operations and Microsoft Fara for agent workflows:

```env
# Normal LLM (single-step and multi-step)
MODEL_API_KEY=your_google_api_key
MODEL_NAME=google/gemini-2.5-flash
MODEL_BASE_URL=

# CUA Model (agent workflows only)
ENABLE_MICROSOFT_CUA=True
AGENT_MODEL_NAME=microsoft/Fara-7B
AGENT_MODEL_API_KEY=your_azure_api_key
AGENT_MODEL_BASE_URL=https://your-endpoint.openai.azure.com/
```

### Example 3: OpenRouter Configuration
Use OpenRouter for multiple models:

```env
# Normal LLM via OpenRouter
MODEL_API_KEY=your_openrouter_api_key
MODEL_NAME=anthropic/claude-3.5-sonnet
MODEL_BASE_URL=https://openrouter.ai/api/v1

# Agent workflows via OpenRouter
AGENT_MODEL_NAME=google/gemini-2.5-computer-use-preview-10-2025
AGENT_MODEL_API_KEY=your_openrouter_api_key  # Can be same as MODEL_API_KEY
AGENT_MODEL_BASE_URL=https://openrouter.ai/api/v1
```

---
## Note:
- Ensure your virtual environment is activated in each terminal before running commands.
- For code changes, restart the backend and frontend servers.

---

## Usage Examples

### 1. Quick Action (Observe + Act)

**What it does:** Observes elements using AI, then performs an action

**Via Frontend:**
1. Open http://127.0.0.1:8501
2. Click on "Launch Stagehand" button
3. Enter URL: `https://example.com`
4. Instruction: `Click the sign in button`
5. Enable "Draw Overlay" to see what AI observes
6. Click "Execute Action"

**Via API:**
```python
import requests

response = requests.post(
    "http://localhost:8000/api/v1/stagehand/action",
    json={
        "url": "https://example.com",
        "action_instruction": "Click the sign in button",
        "draw_overlay": True,
        "take_screenshots": True
    }
)

result = response.json()
print(f"Success: {result['success']}")
print(f"Observed {result['observed_elements']} elements")
print(f"Screenshots: {len(result['artifacts'])}")
```

### 2. Agent Workflow (Autonomous)

**What it does:** AI agent executes complex multi-step tasks autonomously

**Example 1: Data Extraction**
```python
# Extract cryptocurrency prices
response = requests.post(
    "http://localhost:8000/api/v1/stagehand/workflow",
    json={
        "url": "https://duckduckgo.com",
        "workflow_instruction": "Find the current price of Bitcoin and Ethereum",
        "max_steps": 20,
        "auto_screenshot": True
    }
)

result = response.json()
print(result['result']['message'])
# Output:
# Task completed successfully.
# 
# Extracted Information:
# - Bitcoin (BTC) — USD price: $89,451.67 (CoinMarketCap)
# - Ethereum price: $3,114.99 USD (CoinMarketCap)
```

**With Microsoft CUA Agent:**
```python
# Use Microsoft's Computer Use Agent (Fara-7B)
response = requests.post(
    "http://localhost:8000/api/v1/stagehand/workflow",
    json={
        "url": "https://example.com",
        "workflow_instruction": "Extract product prices and availability",
        "agent_model": "microsoft/Fara-7B",  # Use Microsoft CUA
        "max_steps": 20
    }
)
```

### 3. Multi-Step Workflow

**What it does:** Execute sequential steps with full control over each action

**Via Frontend:**
1. Navigate to "Multi-Step" tab
2. Add steps:
   - Step 1: goto - `Navigate to products`
   - Step 2: observe - `Find the search box`
   - Step 3: act - `Type "laptop" into search`
   - Step 4: extract - `Get product names and prices`
3. Configure: screenshots, stop on error
4. Click "Execute Workflow"

**Via API:**
```python
response = requests.post(
    "http://localhost:8000/api/v1/stagehand/multistep",
    json={
        "url": "https://example.com",
        "instructions": [
            {
                "step_number": 1,
                "instruction_type": "observe",
                "instruction_text": "Find the search input",
                "wait_after": 2000
            },
            {
                "step_number": 2,
                "instruction_type": "act",
                "instruction_text": "Type 'laptop' in search",
                "wait_after": 1000
            },
            {
                "step_number": 3,
                "instruction_type": "extract",
                "instruction_text": "Extract product names and prices",
                "wait_after": 0
            }
        ],
        "take_screenshots": True,
        "draw_overlay": False,
        "stop_on_error": False
    }
)

result = response.json()
print(f"Job ID: {result['job_id']}")
print(f"Total steps: {result['total_steps']}")
print(f"Completed: {result['completed_steps']}")
for step in result['steps']:
    print(f"  Step {step['step_number']}: {step['success']}")
```

---

## Agent Models & Data Extraction

### Model Architecture

The platform uses **two separate model configurations** optimized for different workflow types:

#### Normal LLM Models (Single-Step & Multi-Step)
- **Purpose**: Precise browser actions, data extraction with schemas
- **Configuration**: `MODEL_NAME`, `MODEL_API_KEY`, `MODEL_BASE_URL`
- **Recommended Models**:
  - `google/gemini-2.5-flash`
  - `google/gemini-2.5-pro`
  - `openai/gpt-4o`
  - `anthropic/claude-3.5-sonnet`

#### CUA Models (Agent Workflows)
- **Purpose**: Autonomous multi-step navigation, complex task execution
- **Configuration**: `AGENT_MODEL_NAME`, `AGENT_MODEL_API_KEY`, `AGENT_MODEL_BASE_URL`
- **Recommended Models**:
  - `microsoft/Fara-7B`
  - `google/gemini-2.5-computer-use-preview-10-2025`
  - `anthropic/claude-sonnet-4-20250514`

**Usage:**
```python
response = requests.post(
    "http://localhost:8000/api/v1/stagehand/workflow",
    json={
        "url": "https://example.com",
        "workflow_instruction": "Find product prices",
        "agent_model": "microsoft/Fara-7B"  # Specify CUA model
    }
)
```

### Data Extraction Features

**Automatic Fact Extraction:**
The Microsoft CUA agent automatically extracts and formats data:

```python
# Request
{
    "url": "https://duckduckgo.com",
    "workflow_instruction": "Find the current price of Bitcoin"
}

# Response
{
    "success": true,
    "result": {
        "message": "Task completed successfully.\n\nExtracted Information:\n- Bitcoin (BTC) — USD price: $",
        "completed": true
    }
}
```

## Architecture

### System Overview

```
┌──────────────────────────────────────────────────────────┐
│              Frontend (Streamlit)                        │
│  • Dashboard UI                                          │
│  • Quick Actions  • Agent Workflows                      │
│  • Multi-Step Workflow • Real-time Results               │
└────────────────────┬─────────────────────────────────────┘
                     │ HTTP REST API
┌────────────────────▼─────────────────────────────────────┐
│              Backend API (FastAPI)                       │
│  • /api/v1/stagehand/action     - Quick actions          │
│  • /api/v1/stagehand/workflow   - Agent workflows        │
│  • /api/v1/stagehand/multistep  - Sequential workflows   │
│  • /health - Health checks                               │
└────────────────────┬─────────────────────────────────────┘
                     │
┌────────────────────▼─────────────────────────────────────┐
│           Stagehand Service Layer                        │
│  • Session-per-request pattern                           │
│  • Browser automation via Browserbase                    │
│  • AI-powered element detection (LLMs)                   │
│  • Screenshot capture  • Error handling                  │
│  • Extension system for custom agents                    │
└────────────────────┬─────────────────────────────────────┘
                     │
          ┌──────────┴──────────────────┐
          │                             │
┌─────────▼───────┐  ┌────────────────▼──────────────┐
│  Browserbase    │  │  AI Models                     │
│  Cloud Browsers │  │  • Google Gemini (default)     │
│  • Chromium     │  │  • Microsoft CUA (Fara-7B)     │
│  • Session Mgmt │  │  • OpenAI, Anthropic support   │
└─────────────────┘  │  • Fact extraction & display   │
                     └────────────────────────────────┘
```

### Key Architecture Decisions

1. **Session-per-Request Pattern**
   - Fresh browser session for each API call
   - No shared state between requests
   - Cost-optimized (Browserbase charges per session) or local browser
   - Automatic cleanup after each operation

2. **Stateless Backend**
   - No database required
   - Direct request-response model
   - Scales horizontally with ease

3. **AI-Powered Element Detection**
   - Uses Google Gemini models or any custom multi modals LLMs
   - No CSS selectors needed
   - Self-healing when page structure changes
   - Visual overlay support for debugging

### Tech Stack

**Backend:**
- **Framework:** FastAPI 0.121.0
- **Language:** Python 3.12+
- **Validation:** Pydantic v2
- **Web Server:** Uvicorn
- **Browser Automation:** Stagehand Python (0.5.5)
- **Extension System:** Custom agent integration (Microsoft CUA, OpenAI, Anthropic)

**Frontend:**
- **Framework:** Streamlit 1.50.0+
- **UI Components:** Native Streamlit widgets
- **API Client:** Requests library

**AI Models:**
- **Default:** Google Gemini 2.5 Flash
- **CUA Agent:** Microsoft Fara-7B (via Azure OpenAI or Local deployment)
- **Supported:** OpenAI GPT-4, Anthropic Claude
- **Features:** Multi-model support, automatic fact extraction

**Infrastructure:**
- **Browser Service:** Browserbase (cloud browsers) or Local Playwright

### Data Flow

```
User Request
    ↓
Frontend (Streamlit)
    ↓ HTTP POST
Backend API (FastAPI)
    ↓ Validate with Pydantic
Stagehand Service
    ↓ Create Session
Browserbase (Remote Browser)
    ↓ Navigate & Execute
Gemini AI (Element Detection)
    ↓ Extract/Act
Response with Results
    ↓ Screenshots + Data
Frontend Display
```

---

### File Descriptions

**Backend Core:**
- `main.py` - FastAPI application with 5 Stagehand endpoints + health checks
- `config.py` - Settings management (Browserbase, AI models, app config)
- `stagehand_service.py` - Core automation logic, session management

**Extensions:**
- `extensions/microsoft_cua/` - Microsoft Computer Use Agent integration
  - `microsoft_cua.py` - CUA client with fact extraction
  - `factory.py` - Agent client factory pattern
  - `__init__.py` - Extension package initialization

**Schemas:**
- `stagehand_schemas.py` - Request/response models for all Stagehand features
- `multistep_schemas.py` - Multi-step workflow schemas (StepInstruction, MultiStepJobResponse)
- `common.py` - Shared schemas (HealthResponse, StandardErrorResponse)

**Frontend:**
- `main.py` - Streamlit dashboard with 3 tabs (Action, Agent Workflow, Multi-Step)
- `stagehand_features.py` - UI components for Stagehand features
- `api_client.py` - HTTP client for backend communication
- `config.py` - Dynamic backend config import (uses lru_cache)

---

## Contributing

Pull requests are welcome! Please open an issue first if you plan a large change.


