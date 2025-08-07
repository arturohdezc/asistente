# 🚀 Replit Deployment - Guía Completa

## ⚡ **Deployment Rápido (3 pasos)**

### 1. **Import a Replit**
- Ve a [Replit](https://replit.com) 
- Crea nuevo Repl desde GitHub repository
- El proyecto se auto-configura (NO necesita Nix)

### 2. **Configurar Secrets**
En Replit Secrets (🔒), agrega:
```bash
TELEGRAM_TOKEN=tu_bot_token_real
TELEGRAM_WEBHOOK_SECRET=tu_webhook_secret
GEMINI_API_KEY=tu_gemini_key_real
CRON_TOKEN=tu_cron_token_seguro
```

### 3. **Ejecutar**
Presiona **Run** - ¡Listo! El `start.py` maneja todo automáticamente.

---

## � P**Si hay problemas**

### Error: "couldn't get nix env building"
**Solución**: El proyecto ya NO usa Nix. Si ves este error:
1. Verifica que NO existe archivo `replit.nix` 
2. Tu `.replit` debe verse así:
```toml
run = "python start.py"
modules = ["python-3.12"]

[deployment]
run = ["sh", "-c", "python start.py"]

[[ports]]
localPort = 8080
externalPort = 80

[env]
PYTHONPATH = "$REPL_HOME"
PYTHONUNBUFFERED = "1"
```

### Dependencias no se instalan
El `start.py` instala automáticamente. Si falla:
```bash
# Instalar manualmente
pip install fastapi uvicorn[standard] sqlalchemy[asyncio] aiosqlite pydantic pydantic-settings httpx python-dotenv structlog prometheus-client pytz --user
```

### Variables de entorno faltantes
Agrega en Replit Secrets (mínimo requerido):
- `TELEGRAM_TOKEN`
- `TELEGRAM_WEBHOOK_SECRET` 
- `GEMINI_API_KEY`
- `CRON_TOKEN`

---

## 🎯 **Configurar Webhooks**

### Telegram Bot
```bash
curl -X POST "https://api.telegram.org/bot<TU_TOKEN>/setWebhook" \
  -d "url=https://tu-repl.replit.dev/api/v1/telegram-webhook"
```

### Gmail/Calendar
Usa el proxy en carpeta `proxy/` para manejar cold-starts.

---

## ✅ **Verificar que funciona**

Una vez iniciado, deberías ver:
```
🤖 Personal Assistant Bot - Replit Startup
==================================================
✅ Dependencies installed successfully
✅ Environment variables configured
🚀 Starting Personal Assistant Bot...
INFO: Uvicorn running on http://0.0.0.0:8080
```

### Endpoints disponibles:
- `https://tu-repl.replit.dev/health` - Health check
- `https://tu-repl.replit.dev/docs` - API documentation
- `https://tu-repl.replit.dev/api/v1/metrics` - Métricas

---

## 🤖 **Comandos del Bot**

Una vez configurado el webhook de Telegram:
- `/add <tarea>` - Agregar nueva tarea
- `/list` - Listar tareas pendientes
- `/done <id>` - Marcar tarea completada
- `/calendar <fecha> <evento>` - Crear evento en Calendar

---

## 📊 **Funcionalidades**

Tu bot tendrá:
- ✅ **AI Task Extraction** - Análisis inteligente de emails con Gemini
- ✅ **Multi-Account Gmail** - Monitoreo de múltiples cuentas
- ✅ **Smart Calendar** - Integración con Google Calendar
- ✅ **Telegram Interface** - Gestión completa via comandos
- ✅ **Daily Summaries** - Resúmenes automáticos diarios
- ✅ **Auto Backups** - Respaldos automáticos de base de datos
- ✅ **REST API** - API completa con documentación
- ✅ **Monitoring** - Métricas Prometheus integradas

¡Tu asistente personal está listo! 🎉