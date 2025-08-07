# 🚀 Replit Deployment Guide

## Resumen de Cambios Realizados

### ✅ Problemas Solucionados

1. **Pydantic v2 Compatibility**: 
   - Cambiado `BaseSettings` import a `pydantic-settings`
   - Actualizado `@validator` a `@field_validator` con `@classmethod`
   - Configurado `model_config` en lugar de `class Config`

2. **Variable de Entorno Simplificada**:
   - Cambiado `X_TELEGRAM_BOT_API_SECRET_TOKEN` a `TELEGRAM_WEBHOOK_SECRET`
   - Evita problemas con caracteres especiales en nombres de variables

3. **Dependencias Simplificadas**:
   - Removido límites de versión estrictos que causaban conflictos
   - Creado `requirements-replit-simple.txt` sin versiones específicas

4. **Rutas Flexibles**:
   - Configuración automática de fallback para directorios que no se pueden crear
   - Soporte tanto para rutas de Replit (`/home/runner/`) como locales (`./`)

## 📋 Pasos para Deployment en Replit

### 1. Configurar Variables de Entorno en Replit Secrets

Ve a tu Repl → Secrets (🔒) y agrega:

```bash
# Requeridas
TELEGRAM_TOKEN=tu_token_real_aqui
TELEGRAM_WEBHOOK_SECRET=tu_secret_webhook
GEMINI_API_KEY=tu_api_key_gemini
CRON_TOKEN=tu_token_cron_seguro

# Opcionales (para funcionalidad completa)
GMAIL_ACCOUNTS_JSON={"accounts": [{"email": "tu@gmail.com", "credentials": "..."}]}
CALENDAR_CREDENTIALS_JSON={"type": "service_account", "project_id": "..."}

# Configuración (opcional, usa defaults si no se especifica)
DATABASE_URL=sqlite+aiosqlite:///home/runner/db.sqlite3
BACKUP_DIRECTORY=/home/runner/backups
DEBUG=false
```

### 2. Ejecutar la Aplicación

En Replit, simplemente presiona el botón **Run** o ejecuta:

```bash
python start.py
```

El script automáticamente:
- ✅ Instala dependencias faltantes
- ✅ Verifica variables de entorno
- ✅ Inicializa la base de datos SQLite
- ✅ Inicia el servidor FastAPI en puerto 8080

### 3. Verificar que Funciona

Una vez iniciado, deberías ver:

```
🤖 Personal Assistant Bot - Replit Startup
==================================================
📦 Installing dependencies...
✅ Dependencies installed successfully
✅ Environment variables configured
🚀 Starting Personal Assistant Bot...
✅ Database initialized
✅ Background services started
INFO: Uvicorn running on http://0.0.0.0:8080
```

### 4. Configurar Webhooks

#### Telegram Bot Webhook
```bash
curl -X POST "https://api.telegram.org/bot<TU_TOKEN>/setWebhook" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://tu-repl-name.tu-usuario.repl.co/api/v1/telegram-webhook",
    "secret_token": "tu_webhook_secret"
  }'
```

#### Gmail & Calendar Webhooks
Necesitas deployar el proxy (Cloud Function) que está en la carpeta `proxy/`:
- El proxy maneja cold-starts de Replit
- Reenvía webhooks de Gmail/Calendar a tu Repl
- Ver `proxy/README.md` para instrucciones

### 5. Probar Endpoints

```bash
# Health check
curl https://tu-repl-name.tu-usuario.repl.co/health

# API docs
https://tu-repl-name.tu-usuario.repl.co/docs

# Métricas
https://tu-repl-name.tu-usuario.repl.co/api/v1/metrics
```

## 🔧 Troubleshooting

### Error: "Import error: BaseSettings has been moved"
✅ **Solucionado**: Actualizado a `pydantic-settings`

### Error: "Field required telegram_webhook_secret"
✅ **Solucionado**: Usar `TELEGRAM_WEBHOOK_SECRET` en lugar de `X_TELEGRAM_BOT_API_SECRET_TOKEN`

### Error: "Operation not supported: /home/runner"
✅ **Solucionado**: Fallback automático a rutas locales

### Dependencias no se instalan
- El script intenta `requirements-replit-simple.txt` primero
- Si falla, intenta `requirements.txt`
- Continúa aunque algunas dependencias fallen

### Cold Start Issues
- El proxy en `proxy/` maneja esto automáticamente
- Implementa reintentos exponenciales
- Detecta cuando Replit está "dormido"

## 📊 Funcionalidades Disponibles

Una vez deployado, tu bot tendrá:

### ✅ Comandos de Telegram
- `/add <tarea>` - Agregar nueva tarea
- `/list` - Listar tareas pendientes
- `/done <id>` - Marcar tarea como completada
- `/calendar <fecha> <evento>` - Crear evento en Calendar

### ✅ Webhooks Automáticos
- Gmail: Analiza emails y extrae tareas con IA
- Calendar: Notifica reuniones y busca contexto
- Telegram: Procesa comandos en tiempo real

### ✅ Servicios Background
- Resumen diario automático (7:00 AM México)
- Backup diario de base de datos
- Renovación automática de Gmail watchers

### ✅ API REST
- `GET /api/v1/tasks` - Listar tareas con filtros
- `PUT /api/v1/tasks/{id}` - Actualizar tarea
- `GET /api/v1/daily-summary` - Resumen diario
- `GET /api/v1/metrics` - Métricas Prometheus

## 🎯 Próximos Pasos

1. **Configurar Tokens Reales**: Reemplaza los tokens de prueba
2. **Deployar Proxy**: Para webhooks de Gmail/Calendar
3. **Configurar Cron**: Para resúmenes diarios cuando Repl esté dormido
4. **Monitoreo**: Usar `/metrics` para observabilidad

¡Tu asistente personal ya está listo para usar! 🎉