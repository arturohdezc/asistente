"""
Personal Assistant Bot - Main Application Entry Point

A FastAPI-based personal assistant that integrates Gmail, Google Calendar,
and Telegram to manage tasks with AI-powered analysis using Gemini 1.5 Pro.
"""

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from config.settings import settings
from database import init_database, close_database
from api.routes import router
from core.middleware import (
    request_id_middleware,
    security_headers_middleware,
    input_sanitization_middleware,
    rate_limit_middleware,
    create_global_exception_handler,
)
from core.exceptions import PersonalAssistantError


# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown events."""
    logger.info("🚀 Starting Personal Assistant Bot...")

    # Initialize database
    await init_database()
    logger.info("✅ Database initialized")

    # TODO: Start background services (backup, gmail watcher, summary scheduler)
    # This will be implemented in later sprints

    # Start background services
    from services.summary_service import SummaryService
    from services.backup_service import BackupService
    from services.task_service import TaskService
    from services.telegram_service import TelegramService
    from database import async_session

    # Note: In production, you would get these from dependency injection
    # For now, we'll create instances but the scheduler won't run without chat IDs configured
    summary_service = SummaryService()
    backup_service = BackupService()

    # Start the schedulers as background tasks
    asyncio.create_task(summary_service.run_daily_scheduler(None, None))
    asyncio.create_task(backup_service.run_daily_backup_scheduler())
    logger.info("✅ Background services started (summary scheduler, backup scheduler)")

    yield

    logger.info("🛑 Shutting down Personal Assistant Bot...")
    await close_database()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""

    app = FastAPI(
        title="Personal Assistant Bot",
        description="AI-powered personal assistant integrating Gmail, Calendar, and Telegram",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # Add security middleware (order matters!)
    app.add_middleware(
        TrustedHostMiddleware, allowed_hosts=["*.replit.dev", "localhost", "127.0.0.1"]
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["https://api.telegram.org"],
        allow_credentials=False,
        allow_methods=["POST", "GET"],
        allow_headers=["*"],
    )

    # Add custom middleware
    app.middleware("http")(rate_limit_middleware)
    app.middleware("http")(input_sanitization_middleware)
    app.middleware("http")(security_headers_middleware)
    app.middleware("http")(request_id_middleware)

    # Add global exception handler
    app.add_exception_handler(Exception, create_global_exception_handler())
    app.add_exception_handler(PersonalAssistantError, create_global_exception_handler())

    # Include API routes
    app.include_router(router, prefix="/api/v1")

    return app


# Create the FastAPI app instance
app = create_app()


@app.get("/")
async def root():
    """Root endpoint with basic information."""
    return {
        "message": "Personal Assistant Bot API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8080,
        reload=True if settings.debug else False,
        log_level="info",
    )
