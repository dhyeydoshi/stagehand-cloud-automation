# Stagehand AI Automation Platform

> AI-powered browser automation platform with natural language control. Perform web actions, extract structured data, and execute autonomous workflows using simple English instructions. Built with Python 3.12, FastAPI, Streamlit, and Stagehand.

[![Python 3.12](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.121.0-green.svg)](https://fastapi.tiangolo.com/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.50.0+-red.svg)](https://streamlit.io/)
[![Stagehand](https://img.shields.io/badge/Stagehand-0.5.5-purple.svg)](https://github.com/browserbase/stagehand-python)

**Status:** ✅ Production Ready | **Architecture:** Session-per-request | **Python:** 3.12+

---

## What You Can Do

### AI-Powered Browser Automation
- **Natural Language Actions** - `"Click the sign in button"` - No CSS selectors needed
- **Smart Observation** - AI identifies elements before acting - See what it "sees"
- **Structured Data Extraction** - Extract with Pydantic schemas or simple instructions
- **Autonomous Agents** - Execute complex multi-step workflows automatically
- **Multi-Step Workflows** - Chain sequential actions with full control
- **Self-Healing** - Automatically adapts when page structure changes

### Core Capabilities
- **Session-per-Request** - Fresh browser for each operation (cost-optimized)
- **Real-time Streaming** - See live logs and progress
- **Screenshot Support** - Visual verification of actions
- **Error Recovery** - Graceful error handling with detailed messages
- **Type-Safe** - Pydantic validation throughout
- **Production-Ready** - Standardized error codes, monitoring support

---

## Quick Start

### Prerequisites
1. **Install Python 3.12+**
   - Download from https://www.python.org/downloads/
   - Verify: `python --version`

2. **Get API Keys**
   - Browserbase: https://www.browserbase.com/ (API key + Project ID)
   - Google AI Studio: https://aistudio.google.com/apikey (API key)


3. **Optional**
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

```env
# Required - Stagehand/Browserbase
STAGEHAND_ENV=BROWSERBASE
BROWSERBASE_API_KEY=your_browserbase_api_key
BROWSERBASE_PROJECT_ID=your_browserbase_project_id

# Required - AI Model (Google Gemini recommended)
MODEL_API_KEY=your_google_ai_api_key
MODEL_NAME=gemini-2.5-flash
MODEL_BASE_URL=

# Optional - Application Settings
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

### 2. Extract Structured Data

**What it does:** Extracts data using Pydantic schemas for type safety

**Available Schemas:**
- `ProductData` - Extract product info (name, price, rating, etc.)
- `JobPosting` - Extract job details (title, company, salary, etc.)
- `CompanyInfo` - Extract company data (name, founded year, etc.)

**Via Frontend:**
1. Navigate to "Extract Data" tab
2. Enter URL: `https://example.com/product`
3. Select schema: "ProductData"
4. Instruction: `Extract product name, price, and rating`
5. Click "Extract Data"

**Via API:**
```python
response = requests.post(
    "http://localhost:8000/api/v1/stagehand/extract",
    json={
        "url": "https://example.com/product",
        "instruction": "Extract product name, price, and rating",
        "schema_name": "ProductData",
        "take_screenshots": True
    }
)

result = response.json()
if result['success']:
    product = result['data']
    print(f"Product: {product['name']}")
    print(f"Price: ${product['price']}")
    print(f"Rating: {product['rating']}/5")
```

### 3. Agent Workflow (Autonomous)

**What it does:** AI agent executes complex multi-step tasks autonomously

**Via Frontend:**
1. Navigate to "Agent Workflow" tab
2. Enter URL: `https://jobs.example.com`
3. Instruction: `Find and apply to first engineer position with mock data`
4. Set max steps: 30
5. Enable auto-screenshot
6. Click "Execute Workflow"

**Via API:**
```python
response = requests.post(
    "http://localhost:8000/api/v1/stagehand/workflow",
    json={
        "url": "https://jobs.example.com",
        "workflow_instruction": "Find and apply to first engineer position",
        "max_steps": 30,
        "auto_screenshot": True,
        "wait_between_actions": 2000  # milliseconds
    }
)

result = response.json()
print(f"Workflow completed: {result['success']}")
print(f"Agent result: {result['result']}")
```

### 4. Multi-Step Workflow (Controlled)

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
                "instruction_type": "goto",
                "instruction_text": "Navigate to products section",
                "wait_after": 1000
            },
            {
                "step_number": 2,
                "instruction_type": "observe",
                "instruction_text": "Find the search input",
                "wait_after": 500
            },
            {
                "step_number": 3,
                "instruction_type": "act",
                "instruction_text": "Type 'laptop' in search",
                "wait_after": 1000
            },
            {
                "step_number": 4,
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

### 5. List Available Schemas

```python
response = requests.get("http://localhost:8000/api/v1/stagehand/schemas")
schemas = response.json()

for schema in schemas['schemas']:
    print(f"\n{schema['name']}: {schema['description']}")
    print(f"  Fields: {', '.join(schema['fields'])}")
```

---

## Architecture

### System Overview

```
┌──────────────────────────────────────────────────────────┐
│              Frontend (Streamlit)                         │
│  • Dashboard UI                                          │
│  • Quick Actions  • Agent Workflows  • Data Extraction   │
│  • Multi-Step Builder  • Real-time Results              │
└────────────────────┬─────────────────────────────────────┘
                     │ HTTP REST API
┌────────────────────▼─────────────────────────────────────┐
│              Backend API (FastAPI)                        │
│  • /api/v1/stagehand/action     - Quick actions          │
│  • /api/v1/stagehand/extract    - Data extraction        │
│  • /api/v1/stagehand/workflow   - Agent workflows        │
│  • /api/v1/stagehand/multistep  - Sequential workflows   │
│  • /health - Health checks                               │
└────────────────────┬─────────────────────────────────────┘
                     │
┌────────────────────▼─────────────────────────────────────┐
│           Stagehand Service Layer                         │
│  • Session-per-request pattern                          │
│  • Browser automation via Browserbase                    │
│  • AI-powered element detection (Gemini)                │
│  • Screenshot capture  • Error handling                  │
└────────────────────┬─────────────────────────────────────┘
                     │
          ┌──────────┴──────────┐
          │                     │
┌─────────▼───────┐  ┌─────────▼──────────┐
│  Browserbase    │  │   Google Gemini    │
│  Cloud Browsers │  │   AI Models        │
│  • Chromium     │  │   • Element ID     │
│  • Session Mgmt │  │   • Instructions   │
└─────────────────┘  └────────────────────┘
```

### Key Architecture Decisions

1. **Session-per-Request Pattern**
   - Fresh browser session for each API call
   - No shared state between requests
   - Cost-optimized (Browserbase charges per session)
   - Automatic cleanup after each operation

2. **Stateless Backend**
   - No database required
   - No job queue management
   - Direct request-response model
   - Scales horizontally with ease

3. **AI-Powered Element Detection**
   - Uses Google Gemini models for natural language understanding
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

**Frontend:**
- **Framework:** Streamlit 1.50.0+
- **UI Components:** Native Streamlit widgets
- **API Client:** Requests library

**Infrastructure:**
- **Browser Service:** Browserbase (cloud browsers)
- **AI Models:** Google Gemini (gemini-2.5-flash)
- **Deployment:** Docker, Azure Container Apps, AWS Lambda/ECS

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

**Schemas:**
- `stagehand_schemas.py` - Request/response models for all Stagehand features
- `multistep_schemas.py` - Multi-step workflow schemas (StepInstruction, MultiStepJobResponse)
- `common.py` - Shared schemas (HealthResponse, StandardErrorResponse)

**Frontend:**
- `main.py` - Streamlit dashboard with 4 tabs (Action, Extract, Workflow, Multi-Step)
- `stagehand_features.py` - UI components for Stagehand features
- `api_client.py` - HTTP client for backend communication
- `config.py` - Dynamic backend config import (uses lru_cache)

---

## Deployment Options(Will upload the required files separately)

### Cloud Deployment

This project includes production-ready deployment configurations for multiple cloud platforms:

#### 1. Azure Container Apps (Recommended)
**Best for:** Production deployments, auto-scaling, cost-effective

**Features:**
- ✅ Auto-scaling (0-10 replicas)
- ✅ Built-in HTTPS
- ✅ Free tier available (180K vCPU-seconds/month)
- ✅ Pay only when running

**Deployment:**
```bash
cd azure
# Edit deploy-azure.bat with your API keys
deploy-azure.bat
```


#### 2. AWS Lambda (Serverless - FREE Tier)

**Features:**
- ✅ FREE tier: 1M requests/month
- ✅ Zero cost when idle
- ✅ Automatic scaling
- ⚠️ 25-second timeout limit

**Deployment:**
```bash
cd aws-lambda
./deploy-lambda.sh
```


#### 3. AWS ECS Fargate

**Features:**
- ✅ Full container control
- ✅ VPC networking
- ✅ Load balancing
- ⚠️ Higher cost than Lambda

**Deployment:**
```bash
cd aws-ecs
./setup-infrastructure.sh
./deploy-ecs.sh
```

### Frontend Deployment (Streamlit Cloud)

Deploy frontend separately to Streamlit Cloud (FREE):

1. Push code to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect repository
4. Set secrets (API_URL)
5. Deploy

---


## Status & Roadmap

### Current Status (v1.0)

**Production Ready:**
- ✅ Python 3.12 compatible
- ✅ Full Stagehand integration (observe, act, extract, agent, multi-step)
- ✅ Comprehensive error handling with standardized codes
- ✅ Type-safe with Pydantic v2
- ✅ Session-per-request architecture (cost-optimized)
- ✅ Multiple deployment options (Azure, AWS Lambda, AWS ECS)
- ✅ Frontend/backend separation


---

## Contributing

Pull requests are welcome! Please open an issue first if you plan a large change.


