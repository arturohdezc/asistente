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

### Error: "externally-managed-environment"

**Solución**: Replit usa un entorno Nix que no permite pip install. Esto es normal.

- ✅ **La aplicación funciona** - Las dependencias están en `replit.nix`
- ✅ **Ignora los errores de pip** - El `start.py` continúa automáticamente
- ✅ **Verifica que funciona** - Ve a tu URL de Repl, debería mostrar la app

### Error: "couldn't get nix env building"

**Solución**: Si el canal Nix falla:

1. En Replit Shell: `nix-channel --update`
2. O cambia el canal en `.replit` a `stable-22.11`

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

### Endpoints disponibles

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
