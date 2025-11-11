# Changelog

All notable changes to the Stagehand AI Automation project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
    - `v2-stagehand/frontend/api_client.py` (5 lines removed)
    - `v2-stagehand/frontend/frontend_config.py` (2 lines removed)
    - `v2-stagehand/frontend/main.py` (38 lines changed, net -22)
    - `v2-stagehand/frontend/stagehand_features.py` (46 lines changed, net -30)

### Fixed
- **Bug Fixes**: Various bug fixes and improvements (see commit 8ea9cd4)
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
- AWS deployment options (ECS and Lambda)
- Azure deployment support

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
- Headless mode may still briefly show browser window in some configurations

---

## Upgrade Guide

### From v0.x to v1.0.0

1. If using Extract Data tab, migrate to Quick Action or Multi-Step workflows
2. Update any scripts that relied on separate extraction endpoint
3. Review and update schema usage to match new patterns

### From v1.0.0 to Current

1. No action needed - changes are backward compatible
2. Update UI usage patterns to leverage automatic navigation in Multi-Step workflows
3. Remove any manual "goto" steps that navigate to the initial URL (now automatic)

---

