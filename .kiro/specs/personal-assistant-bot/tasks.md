# Implementation Plan

## Sprint 1 – MVP básico

- [x] 1. Crear la estructura del proyecto y repositorio
  - Create directory structure for FastAPI application with services, models, and API layers
  - Configure replit.nix with Python 3.12 and required dependencies
  - Generate requirements.txt with version ranges: fastapi>=0.111,<0.120, sqlalchemy[asyncio]>=2.0,<2.1, python-telegram-bot>=21.0,<22.0, google-api-python-client>=2.0,<3.0, aiosqlite>=0.19,<0.20, httpx>=0.25,<0.26, pydantic>=2.0,<3.0
  - Create .env.example file for local testing before using Replit Secrets
  - Set up main.py with FastAPI application initialization
  - _Requirements: 8.1, 8.5, 8.6_

- [x] 2. Definir modelos SQLAlchemy async y crear la tabla tasks
  - Create SQLAlchemy async engine configuration with SQLite + aiosqlite
  - Define Task and GmailChannel models with proper indexes and relationships
  - Implement database initialization and migration utilities
  - _Requirements: 6.1, 6.2_

- [x] 3. Implementar TaskService con CRUD y validación
  - Implement TaskService class with async CRUD methods
  - Add task filtering, pagination, and priority management
  - Implement 10k task limit validation with migration warning
  - Write unit tests for task service operations
  - _Requirements: 1.4, 1.5, 6.3_

- [x] 4. Implementar GeminiService.analyze_text() con extracción de tareas
  - Create GeminiService class with analyze_text() method
  - Implement 3-retry mechanism with exponential backoff (2^n seconds)
  - Add task extraction and priority classification logic
  - Write unit tests with mocked Gemini API responses using pytest-httpx or respx
  - _Requirements: 5.1, 5.2, 5.3, 5.4_

- [x] 5. Implementar TelegramService para comandos /add, /list, /done
  - Implement TelegramService class with command parsing
  - Create handlers for /add, /done, /list, /calendar commands
  - Add message formatting with Markdown and priority emojis
  - Implement webhook validation with X-Telegram-Bot-Api-Secret-Token
  - Use pytest-httpx or respx for mocking Telegram API calls in tests
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6_

- [x] 6. Crear endpoints FastAPI /gmail-hook, /telegram-webhook y /tasks
  - Create POST /gmail-hook endpoint with JSON payload processing
  - Create POST /telegram-webhook endpoint with direct processing (~10s cold-start)
  - Create GET /tasks endpoint with priority, status, source filters
  - Add pagination support and GET /tasks/{id}, PUT /tasks/{id} endpoints
  - Create GET /health endpoint returning {"status":"ok"}
  - _Requirements: 1.1, 3.1, 9.2, 11.1, 11.2_

## Sprint 2 – Integraciones externas

- [x] 7. Desarrollar Proxy (Cloud Function) con back-off y reintentos
  - Implement Cloud Function/Cloud Run proxy for Gmail and Calendar webhooks
  - Add cold-start detection and exponential backoff retry logic (max 5 attempts)
  - Implement request forwarding to Repl with authentication headers
  - Add structured logging for proxy operations and debugging
  - _Requirements: 1.2, 2.1_

- [x] 8. Implementar GmailWatcherService multi-cuenta y registrar users.watch()
  - Implement GmailWatcherService with users.watch() registration
  - Add channel renewal logic for 24h expiration handling
  - Create gmail_channels table management and persistence
  - Implement background scheduler for watcher renewal every 2 hours
  - _Requirements: 1.1, 1.3_

- [x] 9. Implementar CalendarService (creación de eventos y contexto de reuniones)
  - Create CalendarService class with event creation and notification processing
  - Add meeting context generation by finding related tasks
  - Implement retry logic with exponential backoff (≤ 5 attempts)
  - Process eventId, summary, start, attendees fields from webhooks
  - Create POST /calendar-hook endpoint with meeting notification handling
  - Add `await telegram_service.send_meeting_context(context_text, chat_id)` for context delivery
  - Write unit test validating message is sent when related_tasks is not empty
  - _Requirements: 2.1, 2.2, 2.3, 2.4_

- [x] 10. Implementar SummaryService y envío diario
  - Create SummaryService class with task aggregation by priority (urgent/high/normal/low)
  - Implement GET /daily-summary endpoint with CRON_TOKEN validation
  - Add Markdown formatting for Telegram summary messages
  - Create scheduler job `asyncio.create_task(summary_service.run_daily())` in startup_event
  - Schedule automatic sending at 07:00 America/Mexico_City timezone
  - Document external cron option (e.g., cron-job.org) for when Repl is dormant
  - Write integration test simulating endpoint call and internal cron execution
  - _Requirements: 4.1, 4.2, 4.3, 4.4_

- [x] 11. Añadir BackupService con retención de 7 días y límite 10k tareas
  - Create BackupService class with daily backup creation
  - Implement gzip compression and /home/runner/backups storage
  - Add 7-day retention policy with automatic cleanup
  - Integrate backup scheduler with FastAPI startup via asyncio.create_task()
  - _Requirements: 6.4_

## Sprint 3 – Calidad y seguridad

- [x] 12. Implementar manejo de errores, logging y seguridad
  - Create custom exception hierarchy (PersonalAssistantError and subclasses)
  - Add global exception handler with structured JSON logging
  - Implement request_id tracking and error context preservation
  - Add circuit breaker pattern for external API calls
  - Add Pydantic models with input sanitization and validation
  - Implement webhook token validation for Telegram and cron endpoints
  - Add security headers middleware (X-Content-Type-Options, X-Frame-Options, etc.)
  - Configure CORS middleware for allowed origins
  - _Requirements: 9.1, 7.1, 7.2, 7.3, 7.4_

- [x] 13. Exponer /metrics Prometheus y contador tasks_total
  - Implement metrics collection (tasks_total, webhook_requests, request_duration)
  - Create GET /metrics endpoint with Prometheus format
  - Add business metrics tracking (tasks by priority, completion rates)
  - Integrate metrics middleware with FastAPI request processing
  - _Requirements: 9.2_

- [x] 14. Escribir suite de tests para alcanzar ≥80% de cobertura
  - Write unit tests for all service classes with mocked dependencies
  - Create integration tests for database operations and API endpoints
  - Add end-to-end tests for complete webhook-to-task workflows
  - _Requirements: 10.1, 10.2_

## Sprint 4 – DevOps y documentación

- [x] 15. Configurar CI/CD en GitHub Actions con quality gates (black, ruff, detect-secrets, coverage)
  - Configure GitHub Actions workflow with Python 3.12 and dependency installation
  - Add detect-secrets scanning to prevent credential leaks
  - Implement coverage reporting with pytest-cov and 80% threshold enforcement
  - Add code formatting checks with black and ruff
  - Set up all required secrets in Replit Secrets (TELEGRAM_TOKEN, GEMINI_API_KEY, etc.)
  - _Requirements: 7.2, 10.1, 10.2, 10.3, 7.1, 7.4_

- [x] 16. Completar README con guía de proxy, despliegue en Replit y prueba de carga (Locust)
  - Create README.md with Cloud Function proxy setup instructions
  - Document webhook configuration for Gmail, Calendar, and Telegram
  - Add deployment guide for Replit with all required environment variables
  - Include API documentation with OpenAPI/Swagger examples
  - Implement performance tests with Locust for load testing
  - Execute complete end-to-end testing with real webhook payloads
  - Validate all service integrations and monitoring systems
  - _Requirements: 11.3, 11.4, 10.4_

## Duración y Paralelismo

**Sprint 1** (< 1 semana): Entrega rápida del MVP básico sin APIs externas reales, enfocado en estructura y funcionalidad core.

**Sprint 2** (1-2 semanas): Agrupa todas las integraciones externas. Para ejecución a gran escala, ejecutar tareas 7 (Proxy) y 8 (Gmail Watcher) en paralelo.

**Sprint 3** (1 semana): Sprint optimizado con errores + seguridad fusionados (tarea 12) para no alargar el desarrollo.

**Sprint 4** (< 1 semana): Finalización con DevOps y documentación completa.
