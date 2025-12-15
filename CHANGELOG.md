# Changelog

All notable changes to the Stagehand AI Automation project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added
- **Microsoft CUA Agent Integration**: Added support for Microsoft Computer Use Agent (Fara-7B model)
  - New extension system in `backend/extensions/microsoft_cua/`
  - Factory pattern for agent client creation
  - Full integration with Stagehand agent system
  - Supports Azure OpenAI endpoints for CUA execution
- **Fact Extraction & Display**: Agent now properly returns extracted data to frontend
  - Memorized facts from `pause_and_memorize_fact` actions are included in final message
  - Structured display with "Extracted Information:" section
  - Bullet-point formatting for easy readability
- **Enhanced Agent Instructions**: Improved system prompts for better data extraction
  - Clear guidelines for using `pause_and_memorize_fact`
  - Fact formatting standards 
  - Better termination messages with extracted data summaries
### Changed
- **Multi-Step Stability Checks**: Backend now performs adaptive load-state checks with configurable intervals (`stability_check_interval_ms`, `stability_timeout_ms`, `stability_extra_wait_ms`) instead of fixed sleep calls, cutting idle time while keeping Stagehand runs stable.
- **Frontend Health Polling**: Streamlit sidebar caches `/health` responses for 30 seconds and adds a manual refresh button, reducing redundant requests during reruns.
- **Multi-Step UX**: The single-step form (and its auto-resetting wait slider) has been removed; the streamlined bulk-add table now handles all workflow creation with persistent wait values, add/reset buttons, and easy multi-row editing.
- **Workflow Load Guardrails**: Multi-step backend waits for `domcontentloaded`, `load`, and `networkidle` states before and after navigations/critical actions so pages fully load scripts/CSS before Stagehand sessions close.
- **Observe/Act Auto-Retry**: Navigation-induced "Execution context was destroyed" errors now trigger an automatic stability wait and one retry before surfacing a failure, reducing spurious errors on redirect-heavy pages.
- **Backend API Cleanup**: Simplified main.py by removing redundant code
- **Schema Simplification**: Streamlined stagehand_schemas.py
- **Service Layer Optimization**: Refactored stagehand_service.py for better maintainability
- **Frontend Code Reduction**: Cleaned up stagehand_features.py

### Technical Details
- Microsoft CUA agent uses Azure OpenAI API with custom endpoints
- Agent viewport is intelligently resized for optimal model performance (1288x711 → calculated dimensions)
- Screenshot compression and caching to reduce token usage
- Maximum image limit configurable (default: 1 recent screenshot)
- Temperature set to 0 for deterministic outputs
- Supports multiple action types: click, type, scroll, wait, web_search, pause_and_memorize_fact, terminate
- Self-healing capabilities when DOM changes during execution

---

## [1.0.1]

### Changed
- **UI Simplification**: Removed "Navigate (goto)" from default step type options in Multi-Step workflow
  - Initial navigation is now automatically handled by providing the Target URL
  - Reduces confusion for users about when to use goto vs. automatic navigation
  - Backend implementation retained for advanced use cases requiring mid-workflow navigation
- **Improved Documentation**: Updated Multi-Step workflow info text to clarify automatic navigation behavior

### Added
- **Multi-Step Form UX Enhancement**: Dramatically improved the step-building experience
  - Form now stays expanded after adding steps (no need to reopen)
  - Added `clear_on_submit=True` to automatically reset form fields
  - Improved button styling with primary type
  - Added success/error messages for better feedback
  - Enhanced workflow steps display with better formatting
  - Cleaner UI with consistent styling

### Fixed
- **Backend Error**: Fixed `'StepInstruction' object has no attribute 'get'` error in multi-step workflow processing
  - Backend now properly handles both Pydantic model objects and dictionary formats
  - Improved compatibility with FastAPI request validation
  - Added proper attribute access for StepInstruction objects
- **Multi-Step Form Bug**: Fixed issue where adding steps after the first one required multiple clicks
  - Implemented dynamic form key that changes after each submission
  - Form now properly resets and is immediately ready for next step
  - Resolved conflict between `clear_on_submit` and `st.rerun()`
- **Navigation Error Handling**: Comprehensive improvements for "Execution context was destroyed" errors
  - **Initial page load**: Multi-stage loading (domcontentloaded → load → networkidle → 5s wait)
  - **Before observe/act**: Added 8s timeout checks for DOM and network, plus 2s stability wait
  - **Increased default wait_after**: Changed from 1000ms to 2000ms for better stability
  - **Better logging**: Added step-by-step confirmation of page load states
  - **Enhanced UI guidance**: Updated info box with specific recommendations for complex sites
  - Ensures all page content, JavaScript, and CSS are fully loaded before operations

### Improved
- **Multi-Step Workflow Builder**: Reduced clicks needed to build workflows
  - Users can now add multiple steps continuously without reopening the form
  - Instant visual confirmation when steps are added
  - Cleaner, more professional UI appearance
  - Better step type identification with consistent formatting

### Technical Details
- Modified `stagehand_features.py` to remove "goto" from step type dropdown
- Added helpful tooltip explaining that navigate is not needed
- Backend still supports "goto" instruction type for advanced workflows that need URL changes mid-execution
- Implemented `clear_on_submit` pattern for better form UX
- Fixed `stagehand_service.py` to handle Pydantic StepInstruction objects using attribute access instead of dict.get()
- Added backward compatibility for both object and dictionary instruction formats
- Implemented dynamic form key using counter (`form_counter`) to force proper form reset after each submission
- Form key changes with each step addition, ensuring Streamlit creates a fresh form instance
- Added page stability checks using `wait_for_load_state()` before observe/act operations
- Improved initial page load with networkidle/domcontentloaded wait strategies
- Enhanced error messages for navigation-related failures with actionable suggestions

---

## [1.0.0]

### Removed
- **Extract Data Functionality**: Removed standalone "Extract Data" tab from frontend UI
  - Simplified to focus on three core workflows: Quick Action, Agent Workflow, and Multi-Step
  - Extraction still available through Quick Action and Multi-Step workflows
  - Files modified:
    - `v2-stagehand/frontend/api_client.py`
    - `v2-stagehand/frontend/frontend_config.py`
    - `v2-stagehand/frontend/main.py`
    - `v2-stagehand/frontend/stagehand_features.py`

### Fixed
- **Bug Fixes**: Various bug fixes and improvements
- **README Updates**: Updated documentation to reflect new features and functionality

---

## [0.2.0]

### Added
- Initial commit of v2-stagehand implementation
- Session-per-job pattern for browser automation
- Multi-tenant support
- Three main workflow types:
  - **Quick Action**: Single atomic actions using observe & act
  - **Agent Workflow**: Autonomous multi-step task execution
  - **Multi-Step Workflow**: Sequential instruction-based workflows

### Features
- Integration with Stagehand Python library
- Support for both LOCAL and BROWSERBASE environments
- Screenshot capture with overlay visualization
- Structured data extraction with Pydantic schemas

### Technical Stack
- **Backend**: FastAPI with async/await patterns
- **Frontend**: Streamlit with session state management
- **Browser Automation**: Stagehand Python (Playwright-based)
- **AI Models**: Support for multiple LLM providers (OpenRouter, Anthropic, OpenAI)

---

## [0.1.0]

### Added
- Project initialization
- Basic project structure
- Initial documentation (README, LICENSE)

---

## Notes

### Workflow Types Explained

**Quick Action (Observe & Act)**
- Best for: Single, atomic actions
- Example: "Click the sign in button", "Find list of phones sold in 2018"
- Avoid: Complex multi-step instructions

**Agent Workflow**
- Best for: Complex autonomous tasks
- Example: "Navigate to products and filter by Electronics"
- Uses AI agents for autonomous decision-making

**Multi-Step Workflow**
- Best for: Sequential, step-by-step automation
- Each step should be atomic and specific
- Automatic navigation to target URL before executing steps
- Step types: observe, act, extract, wait, screenshot

### Migration Notes

If you were using the "Extract Data" tab (removed in v1.0.0):
- Use **Quick Action** for simple extractions
- Use **Multi-Step** workflow with "extract" step type for complex scenarios
- All extraction schemas remain available through the API

### Known Issues

- Scroll action parsing errors may occur with certain AI models (validation error for ScrollAction)
- Large page content may cause timeouts with some AI providers
---

