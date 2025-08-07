# Requirements Document

## Introduction

El proyecto personal_assistant_bot es un asistente personal inteligente desplegado en Replit que integra múltiples servicios (Gmail, Google Calendar, Telegram) para gestionar tareas y proporcionar contexto relevante. El sistema utiliza Gemini 1.5 Pro para análisis de texto y extracción de tareas, manteniendo persistencia en SQLite y ofreciendo una API REST completa.

## Requirements

### Requirement 1

**User Story:** Como usuario con múltiples cuentas de Gmail, quiero que el sistema reciba notificaciones automáticamente y extraiga tareas con clasificación de urgencia, para gestionar eficientemente mis pendientes.

#### Acceptance Criteria

1. WHEN un correo nuevo llega THEN el sistema SHALL recibir notificación vía POST /gmail-hook con proxy < 1s
2. WHEN el proxy recibe webhook THEN el proxy SHALL manejar cold-start con reintentos exponenciales (máx 5)
3. WHEN procesa correo THEN el sistema SHALL leer N cuentas desde GMAIL_ACCOUNTS_JSON
4. WHEN analiza contenido THEN analyze_text() SHALL devolver {"tasks": [], "context": "", "priority": "urgent|high|normal|low"}
5. WHEN inserta tarea THEN el sistema SHALL guardar id, title, due, status, source, priority
6. WHEN fecha límite < 24h THEN el sistema SHALL clasificar como "urgent"

### Requirement 2

**User Story:** Como usuario, quiero recibir contexto relevante sobre mis tareas cuando tengo reuniones programadas, para estar mejor preparado.

#### Acceptance Criteria

1. WHEN llega un aviso de Calendar THEN el sistema SHALL recibir la notificación vía POST /calendar-hook
2. WHEN se procesa el aviso de Calendar THEN el sistema SHALL buscar tareas relacionadas en la base de datos
3. WHEN encuentra tareas relacionadas THEN el sistema SHALL generar un contexto en texto plano
4. WHEN genera el contexto THEN el sistema SHALL incluir información como "Tienes 3 pendientes relacionados..."

### Requirement 3

**User Story:** Como usuario, quiero interactuar con el asistente a través de Telegram con comandos completos, para gestionar mis tareas y calendario de forma conversacional.

#### Acceptance Criteria

1. WHEN recibo mensajes THEN el sistema SHALL procesarlos vía POST /telegram-webhook con validación de token
2. WHEN uso /add `texto` THEN el sistema SHALL crear tarea con status "open"
3. WHEN uso /done `id` THEN el sistema SHALL cambiar tasks.status a "done" con confirmación
4. WHEN uso /calendar `YYYY-MM-DD hh:mm` `texto` THEN el sistema SHALL crear evento en Google Calendar
5. WHEN uso /list THEN el sistema SHALL agrupar por urgent/high/normal/low y mostrar cuenta origen
6. WHEN comando falla THEN el sistema SHALL mostrar mensaje de error específico

### Requirement 4

**User Story:** Como usuario, quiero recibir un resumen diario formateado automáticamente por Telegram, para planificar mi día desde temprano.

#### Acceptance Criteria

1. WHEN cron llama GET /daily-summary?token=CRON_TOKEN THEN el sistema SHALL validar token y generar resumen
2. WHEN genera resumen THEN el sistema SHALL usar formato Markdown agrupado por priority
3. WHEN envía resumen THEN el sistema SHALL usar Telegram DM a las 07:00 America/Mexico_City
4. WHEN falla envío THEN el sistema SHALL registrar error y reintentar con backoff

### Requirement 5

**User Story:** Como desarrollador, quiero que el sistema use Gemini 1.5 Pro con manejo robusto de errores, para análisis confiable de texto.

#### Acceptance Criteria

1. WHEN analiza texto THEN el sistema SHALL usar Gemini 1.5 Pro vía REST con GEMINI_API_KEY
2. WHEN falla llamada THEN el sistema SHALL implementar 3 reintentos con backoff 2^n segundos
3. WHEN analyze_text() responde THEN el sistema SHALL devolver {"tasks": [], "context": "", "priority": ""}
4. WHEN extrae tareas THEN el sistema SHALL incluir clasificación automática de urgencia

### Requirement 6

**User Story:** Como usuario, quiero que mis datos persistan de forma segura con backup automático, para no perder información y manejar escalabilidad.

#### Acceptance Criteria

1. WHEN inicia THEN el sistema SHALL usar SQLite + SQLAlchemy con db.sqlite3 en /home/runner
2. WHEN crea tabla tasks THEN el sistema SHALL incluir id, title, due, status, source, priority
3. WHEN supera 10k tareas THEN el sistema SHALL mostrar aviso de migración a Postgres
4. WHEN ejecuta backup diario THEN el sistema SHALL guardar en /backups con retención 7 días

### Requirement 7

**User Story:** Como desarrollador, quiero que todas las credenciales estén seguras en Replit Secrets con validación automática, para evitar exposición accidental.

#### Acceptance Criteria

1. WHEN configura THEN todas las claves SHALL estar en Replit Secrets (no variables de entorno)
2. WHEN ejecuta CI THEN detect-secrets SHALL escanear repositorio y fallar si encuentra secretos
3. WHEN hace pull-request con secreto THEN el pipeline SHALL bloquear el merge
4. WHEN carga secrets THEN el sistema SHALL usar TELEGRAM_TOKEN, GMAIL_ACCOUNTS_JSON, CALENDAR_CREDENTIALS_JSON, GEMINI_API_KEY, CRON_TOKEN

### Requirement 8

**User Story:** Como desarrollador, quiero que el sistema esté construido con tecnologías modernas y sea fácil de desplegar en Replit.

#### Acceptance Criteria

1. WHEN se despliega THEN el sistema SHALL usar Python 3.12 + FastAPI + Uvicorn
2. WHEN se instalan dependencias THEN el sistema SHALL incluir python-telegram-bot ≥ 21
3. WHEN se configuran APIs THEN el sistema SHALL usar google-api-python-client y google-auth
4. WHEN se ejecuta THEN el sistema SHALL usar sqlalchemy, pydantic, httpx
5. WHEN se despliega en Replit THEN el sistema SHALL usar replit.nix para dependencias
6. WHEN inicia THEN main.py SHALL arrancar FastAPI en puerto 8080

### Requirement 9

**User Story:** Como administrador del sistema, quiero monitoreo completo con logs estructurados y métricas, para diagnosticar problemas y medir rendimiento.

#### Acceptance Criteria

1. WHEN registra eventos THEN el sistema SHALL usar logs JSON con nivel, timestamp, request_id
2. WHEN accedo a GET /metrics THEN el sistema SHALL devolver métricas Prometheus incluyendo tasks_total
3. WHEN verifico estado THEN GET /health SHALL devolver {"status":"ok"}
4. WHEN accedo a docs THEN FastAPI SHALL proporcionar OpenAPI automática

### Requirement 10

**User Story:** Como desarrollador, quiero alta cobertura de tests y código bien formateado, para asegurar la calidad y mantenibilidad del sistema.

#### Acceptance Criteria

1. WHEN ejecuta pytest --cov THEN el sistema SHALL mostrar cobertura ≥ 80%
2. WHEN la cobertura baja de 80% THEN el pipeline CI SHALL fallar
3. WHEN revisa código THEN el sistema SHALL estar formateado con black y ruff
4. WHEN ejecuta localmente THEN python main.py SHALL funcionar correctamente

### Requirement 11

**User Story:** Como futuro usuario de integraciones, quiero endpoints REST adicionales y documentación completa, para facilitar extensiones del sistema.

#### Acceptance Criteria

1. WHEN implementa API THEN el sistema SHALL incluir GET /tasks/`id` y PUT /tasks/`id`
2. WHEN revisa documentación THEN README.md SHALL explicar configuración de Cloud Function proxy
3. WHEN configura webhooks THEN README.md SHALL incluir instrucciones completas
4. WHEN despliega THEN la documentación SHALL cubrir todos los pasos y variables requeridas