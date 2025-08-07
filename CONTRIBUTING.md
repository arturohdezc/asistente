# Contributing to Personal Assistant Bot

Thank you for your interest in contributing to Personal Assistant Bot! This document provides guidelines and information for contributors.

## 🤝 How to Contribute

### Reporting Issues

1. **Search existing issues** first to avoid duplicates
2. **Use the issue template** when creating new issues
3. **Provide detailed information** including:
   - Steps to reproduce
   - Expected vs actual behavior
   - Environment details (Python version, OS, etc.)
   - Relevant logs or error messages

### Suggesting Features

1. **Check the roadmap** to see if the feature is already planned
2. **Open a feature request** with detailed description
3. **Explain the use case** and why it would be valuable
4. **Consider implementation complexity** and maintenance burden

### Code Contributions

1. **Fork the repository** and create a feature branch
2. **Follow the development setup** instructions in README.md
3. **Write tests** for your changes (maintain >80% coverage)
4. **Follow code style** guidelines (Black, Ruff)
5. **Update documentation** as needed
6. **Submit a pull request** with clear description

## 🛠️ Development Setup

### Prerequisites

- Python 3.12+
- Git
- Virtual environment tool (venv, conda, etc.)

### Setup Steps

```bash
# Clone your fork
git clone https://github.com/your-username/personal-assistant-bot.git
cd personal-assistant-bot

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install pre-commit hooks
pre-commit install

# Run tests to verify setup
python run_tests.py
```

### Environment Configuration

Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
# Edit .env with your test configuration
```

For testing, you can use dummy values for most settings.

## 📝 Code Style Guidelines

### Python Style

- **Follow PEP 8** with 100-character line limit
- **Use Black** for automatic formatting
- **Use Ruff** for linting
- **Add type hints** for all function parameters and returns
- **Write docstrings** for all public functions and classes

### Code Formatting

```bash
# Format code
black .

# Check linting
ruff check .

# Fix auto-fixable issues
ruff check . --fix
```

### Import Organization

```python
# Standard library imports
import asyncio
import json
from datetime import datetime
from typing import Dict, List, Optional

# Third-party imports
from fastapi import FastAPI, HTTPException
from sqlalchemy import select

# Local imports
from core.exceptions import PersonalAssistantError
from models.task import Task
from services.task_service import TaskService
```

## 🧪 Testing Guidelines

### Test Requirements

- **Maintain >80% coverage** for all new code
- **Write unit tests** for individual functions/methods
- **Write integration tests** for API endpoints
- **Mock external dependencies** (APIs, databases)
- **Use descriptive test names** that explain what is being tested

### Test Structure

```python
class TestTaskService:
    """Test cases for TaskService."""
    
    @pytest.fixture
    def mock_db_session(self):
        """Mock database session."""
        return AsyncMock(spec=AsyncSession)
    
    @pytest.mark.asyncio
    async def test_create_task_success(self, task_service, mock_db_session):
        """Test successful task creation."""
        # Arrange
        task_data = {"title": "Test task", "source": "test@example.com"}
        
        # Act
        result = await task_service.create_task(**task_data)
        
        # Assert
        assert result.title == task_data["title"]
        mock_db_session.commit.assert_called_once()
```

### Running Tests

```bash
# Run all tests
python run_tests.py

# Run specific test file
python -m pytest tests/unit/services/test_task_service.py -v

# Run with coverage
python -m pytest --cov=. --cov-report=html

# Run integration tests only
python -m pytest tests/integration/ -v
```

## 📚 Documentation Guidelines

### Code Documentation

- **Write clear docstrings** using Google style
- **Document complex algorithms** with inline comments
- **Explain business logic** and design decisions
- **Keep comments up-to-date** with code changes

### API Documentation

- **Use FastAPI automatic documentation** features
- **Add response examples** for complex endpoints
- **Document error responses** and status codes
- **Include request/response schemas**

### README Updates

- **Update feature lists** when adding new functionality
- **Add configuration examples** for new settings
- **Update API documentation** links and examples
- **Keep troubleshooting section** current

## 🔄 Pull Request Process

### Before Submitting

1. **Ensure all tests pass** locally
2. **Run code quality checks** (Black, Ruff, detect-secrets)
3. **Update documentation** as needed
4. **Add changelog entry** if applicable
5. **Rebase on latest main** branch

### PR Description Template

```markdown
## Description
Brief description of changes and motivation.

## Type of Change
- [ ] Bug fix (non-breaking change that fixes an issue)
- [ ] New feature (non-breaking change that adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update

## Testing
- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] Manual testing completed
- [ ] Performance impact assessed

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] Tests added and passing
- [ ] No new warnings introduced
```

### Review Process

1. **Automated checks** must pass (CI/CD pipeline)
2. **Code review** by at least one maintainer
3. **Testing verification** in staging environment
4. **Documentation review** for user-facing changes
5. **Final approval** and merge by maintainer

## 🏗️ Architecture Guidelines

### Service Layer

- **Keep services focused** on single responsibilities
- **Use dependency injection** for testability
- **Handle errors gracefully** with custom exceptions
- **Log important operations** with structured logging

### API Layer

- **Follow RESTful conventions** for endpoints
- **Use appropriate HTTP status codes**
- **Validate input data** with Pydantic models
- **Handle errors consistently** with global exception handler

### Database Layer

- **Use async SQLAlchemy** for all database operations
- **Define proper indexes** for query performance
- **Handle database errors** gracefully
- **Use migrations** for schema changes

### External Integrations

- **Implement circuit breakers** for reliability
- **Add retry logic** with exponential backoff
- **Monitor API quotas** and rate limits
- **Mock external services** in tests

## 🚀 Release Process

### Version Numbering

We follow [Semantic Versioning](https://semver.org/):

- **MAJOR**: Breaking changes
- **MINOR**: New features (backward compatible)
- **PATCH**: Bug fixes (backward compatible)

### Release Checklist

1. **Update version** in `pyproject.toml`
2. **Update CHANGELOG.md** with release notes
3. **Run full test suite** and performance tests
4. **Create release branch** from main
5. **Deploy to staging** and run smoke tests
6. **Create GitHub release** with release notes
7. **Deploy to production** after approval
8. **Monitor metrics** post-deployment

## 🎯 Contribution Areas

### High Priority

- **Performance optimizations** for high-load scenarios
- **Additional AI integrations** (Claude, GPT-4, etc.)
- **Enhanced security features** (OAuth2, JWT, etc.)
- **Mobile app integration** (React Native, Flutter)
- **Advanced analytics** and reporting

### Medium Priority

- **Additional calendar providers** (Outlook, Apple Calendar)
- **Email providers** beyond Gmail (Outlook, Yahoo)
- **Notification channels** (Slack, Discord, SMS)
- **Task templates** and automation rules
- **Multi-language support** (i18n)

### Documentation

- **API examples** in multiple languages
- **Video tutorials** for setup and usage
- **Architecture diagrams** and explanations
- **Performance tuning** guides
- **Troubleshooting** documentation

## 📞 Getting Help

### Communication Channels

- **GitHub Issues**: Bug reports and feature requests
- **GitHub Discussions**: General questions and ideas
- **Email**: team@example.com for private matters
- **Telegram**: @PersonalAssistantBot for community chat

### Maintainer Response Times

- **Critical bugs**: Within 24 hours
- **Feature requests**: Within 1 week
- **Pull requests**: Within 3-5 business days
- **General questions**: Within 1 week

## 🏆 Recognition

Contributors will be recognized in:

- **README.md** contributors section
- **Release notes** for significant contributions
- **GitHub contributors** page
- **Annual contributor** highlights

Thank you for contributing to Personal Assistant Bot! 🎉