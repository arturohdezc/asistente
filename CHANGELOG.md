# Changelog

All notable changes to this project will be documented in this file.

## [1.2.2] - 2025-08-07 - Enhanced Calendar Command with Natural Language Processing

### ✨ Enhanced
- **Calendar Command Intelligence**: `/calendar` command now uses Gemini AI to parse natural language date/time inputs
  - Supports flexible formats: "Meeting tomorrow at 2pm", "Team standup Monday 9:30am", "Project review next Friday at 3:00 PM for 2 hours"
  - Automatically extracts event title, date/time, duration, and description
  - Falls back gracefully when date/time cannot be extracted
  - Maintains backward compatibility with exact format inputs

### 🔧 Technical Improvements
- **New Gemini Service Method**: Added `analyze_calendar_event()` for calendar-specific text analysis
- **Enhanced Data Models**: Added `CalendarEventData` and `CalendarAnalysisResult` classes
- **Improved Error Handling**: Better user feedback when date/time extraction fails
- **Comprehensive Testing**: Added unit tests for calendar analysis functionality

### 📚 Updated
- **Help Messages**: Updated `/calendar` command help to reflect new flexible usage
- **User Experience**: More intuitive calendar event creation with natural language

## [1.2.1] - 2025-08-07 - Replit Environment Fix

### 🔧 Fixed
- **Replit Environment Issues**: Added minimal `replit.nix` with core dependencies
- **Dependency Detection**: `start.py` now checks available packages instead of installing
- **Externally-Managed Environment**: Handles Nix environment restrictions properly

### 📚 Updated
- **Deployment Guide**: Updated with correct Replit environment handling
- **Start Script**: Improved dependency checking and error handling

## [1.2.0] - 2025-08-07 - Project Cleanup & Simplified Deployment

### 🗑️ Removed
- **Cleaned Redundant Files**: Removed duplicate .md files and scripts
  - `DEPLOYMENT_SUCCESS.md`, `REPLIT_NIX_TROUBLESHOOTING.md`
  - `install_replit.py`, `test_replit.py`, `run_simple.py`
  - `.replit.backup`, `INSTRUCCIONES_REPLIT.md`, `REPLIT_QUICK_START.md`

### 🔧 Simplified
- **Single Deployment Guide**: Consolidated all Replit info into `REPLIT_DEPLOYMENT.md`
- **No-Nix Configuration**: `.replit` now uses only Python modules
- **Streamlined Startup**: `start.py` handles all dependency installation automatically

### 📚 Documentation
- **Unified Guide**: Single comprehensive deployment guide
- **Cleaner README**: Removed redundant troubleshooting links
- **Simplified Structure**: Easier to navigate and maintain

## [1.1.0] - 2025-08-06 - Replit Deployment Optimization

### 🚀 Added
- **Replit Deployment Guide**: Comprehensive guide in `REPLIT_DEPLOYMENT.md`
- **Robust Startup Script**: `start.py` with automatic dependency installation and environment validation
- **Cross-platform Compatibility**: Flexible directory creation with fallback paths
- **Development Mode**: `run_simple.py` for quick local testing

### 🔧 Changed
- **Pydantic v2 Migration**: 
  - Migrated from `pydantic.BaseSettings` to `pydantic-settings.BaseSettings`
  - Updated `@validator` to `@field_validator` with `@classmethod`
  - Replaced `class Config` with `model_config` dictionary
- **Environment Variables**:
  - Simplified `X_TELEGRAM_BOT_API_SECRET_TOKEN` → `TELEGRAM_WEBHOOK_SECRET`
  - Added validation with sensible defaults for optional variables
- **Dependencies**:
  - Removed strict version constraints from `requirements.txt`
  - Simplified dependency management for better Replit compatibility
- **Configuration**:
  - Updated `replit.nix` to handle only system dependencies
  - Let pip manage Python packages for better compatibility

### 🐛 Fixed
- **Pydantic Import Error**: Fixed `BaseSettings has been moved to pydantic-settings` error
- **Environment Variable Issues**: Resolved field validation errors with special characters
- **Directory Creation**: Fixed cross-platform directory creation issues
- **Dependency Conflicts**: Resolved version constraint conflicts in Replit environment

### 📚 Documentation
- Updated README.md with simplified Replit deployment instructions
- Updated specs in `.kiro/specs/` to reflect Pydantic v2 changes
- Added troubleshooting section for common deployment issues
- Updated environment variable documentation

### 🧪 Testing
- Added `test_replit.py` for Replit-specific testing
- Verified cross-platform compatibility (macOS, Linux/Replit)
- Tested automatic dependency installation and environment setup

## [1.0.0] - 2025-08-05 - Initial Release

### 🚀 Features
- **AI-Powered Task Management**: Integration with Gemini 1.5 Pro for intelligent task extraction
- **Multi-Service Integration**: Gmail, Google Calendar, and Telegram Bot APIs
- **Real-time Webhooks**: Push notifications from Gmail and Calendar
- **Automated Summaries**: Daily task summaries via Telegram
- **Background Services**: Automatic backups and Gmail watcher renewal
- **REST API**: Complete task management API with filtering and pagination
- **Monitoring**: Prometheus metrics and structured logging
- **Security**: Circuit breakers, rate limiting, and webhook validation
- **High Test Coverage**: >80% test coverage with comprehensive test suite

### 🏗️ Architecture
- **FastAPI Application**: Modern async Python web framework
- **SQLite Database**: Lightweight database with async support
- **Cloud Function Proxy**: Handles cold starts and webhook reliability
- **Modular Services**: Clean separation of concerns with service layer
- **Background Tasks**: Async task scheduling for maintenance operations

### 📋 Initial Implementation
- Complete implementation of all core features as specified in design documents
- Full test suite with unit, integration, and end-to-end tests
- CI/CD pipeline with GitHub Actions
- Comprehensive documentation and deployment guides