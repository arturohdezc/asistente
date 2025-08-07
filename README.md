# Personal Assistant Bot 🤖

[![CI/CD Pipeline](https://github.com/your-org/personal-assistant-bot/workflows/CI/CD%20Pipeline/badge.svg)](https://github.com/your-org/personal-assistant-bot/actions)
[![Coverage](https://codecov.io/gh/your-org/personal-assistant-bot/branch/main/graph/badge.svg)](https://codecov.io/gh/your-org/personal-assistant-bot)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/release/python-3120/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111+-green.svg)](https://fastapi.tiangolo.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

AI-powered personal assistant that integrates Gmail, Google Calendar, and Telegram to automatically manage tasks with intelligent analysis using Gemini 1.5 Pro.

## ✨ Features

- **🧠 AI-Powered Task Extraction**: Automatically extracts actionable tasks from emails using Gemini 1.5 Pro
- **📧 Multi-Account Gmail Integration**: Monitors multiple Gmail accounts with real-time push notifications
- **📅 Smart Calendar Integration**: Creates events and provides meeting context with related tasks
- **💬 Telegram Bot Interface**: Complete task management through Telegram commands
- **📊 Daily Summaries**: Automated daily task summaries sent via Telegram
- **🔄 Automatic Backups**: Daily database backups with 7-day retention
- **📈 Prometheus Metrics**: Comprehensive monitoring and alerting
- **🛡️ Enterprise Security**: Circuit breakers, rate limiting, and security headers
- **🧪 High Test Coverage**: >80% test coverage with comprehensive test suite

## 🏗️ Architecture

```mermaid
graph TB
    subgraph "External Services"
        Gmail[Gmail API]
        Calendar[Google Calendar API]
        Telegram[Telegram Bot API]
        Gemini[Gemini 1.5 Pro API]
    end
    
    subgraph "Cloud Function Proxy"
        Proxy[Webhook Proxy<br/>- Cold start handling<br/>- Retry logic<br/>- Rate limiting]
    end
    
    subgraph "Replit Application"
        FastAPI[FastAPI Application]
        Services[Services Layer<br/>- TaskService<br/>- GeminiService<br/>- TelegramService<br/>- CalendarService]
        Database[(SQLite Database<br/>- Tasks<br/>- Gmail Channels)]
        Background[Background Services<br/>- Daily Summaries<br/>- Backups<br/>- Channel Renewal]
    end
    
    Gmail --> Proxy
    Calendar --> Proxy
    Proxy --> FastAPI
    Telegram --> FastAPI
    FastAPI --> Services
    Services --> Database
    Services --> Gemini
    Services --> Telegram
    Background --> Services
```

## 🚀 Quick Start

> **✅ Replit Ready**: This project has been optimized for easy deployment on Replit with simplified dependencies and robust startup scripts. See [REPLIT_DEPLOYMENT.md](REPLIT_DEPLOYMENT.md) for detailed instructions.

### Prerequisites

- Python 3.12+
- Google Cloud Project with Gmail and Calendar APIs enabled
- Telegram Bot Token
- Gemini API Key
- Replit Account (for deployment)

### Local Development

1. **Clone the repository**
   ```bash
   git clone https://github.com/your-org/personal-assistant-bot.git
   cd personal-assistant-bot
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

4. **Run the application**
   ```bash
   python main.py
   ```

5. **Run tests**
   ```bash
   python run_tests.py
   ```

## 🔧 Configuration

### Environment Variables

| Variable | Description | Required | Example |
|----------|-------------|----------|---------|
| `TELEGRAM_TOKEN` | Telegram Bot API token | ✅ | `1234567890:ABCdefGHIjklMNOpqrsTUVwxyz` |
| `TELEGRAM_WEBHOOK_SECRET` | Telegram webhook secret | ✅ | `your-secret-token` |
| `GMAIL_ACCOUNTS_JSON` | Gmail accounts configuration | ✅ | `{"accounts": [...]}` |
| `CALENDAR_CREDENTIALS_JSON` | Google Calendar service account | ✅ | `{"type": "service_account", ...}` |
| `GEMINI_API_KEY` | Gemini 1.5 Pro API key | ✅ | `AIza...` |
| `CRON_TOKEN` | Token for cron endpoints | ✅ | `secure-cron-token` |
| `DATABASE_URL` | Database connection string | ❌ | `sqlite+aiosqlite:///db.sqlite3` |
| `MAX_TASKS_LIMIT` | Maximum number of tasks | ❌ | `10000` |
| `TIMEZONE` | Application timezone | ❌ | `America/Mexico_City` |

### Gmail Configuration

Create a JSON configuration for Gmail accounts:

```json
{
  "accounts": [
    {
      "email": "user1@gmail.com",
      "credentials": "path/to/oauth2-credentials.json"
    },
    {
      "email": "user2@gmail.com", 
      "credentials": "path/to/oauth2-credentials-2.json"
    }
  ]
}
```

### Google Calendar Configuration

Use a service account JSON key:

```json
{
  "type": "service_account",
  "project_id": "your-project-id",
  "private_key_id": "key-id",
  "private_key": "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n",
  "client_email": "service-account@your-project.iam.gserviceaccount.com",
  "client_id": "client-id",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token"
}
```

## 🌐 Deployment

### Replit Deployment (Recommended)

> **🎉 Simplified Deployment**: The project now includes optimized startup scripts and dependency management for seamless Replit deployment.

1. **Import to Replit**
   - Go to [Replit](https://replit.com)
   - Create new Repl from GitHub repository
   - The project will auto-configure with `replit.nix`

2. **Configure Environment Variables**
   Add these to Replit Secrets (🔒):
   ```bash
   TELEGRAM_TOKEN=your_bot_token
   TELEGRAM_WEBHOOK_SECRET=your_webhook_secret  
   GEMINI_API_KEY=your_gemini_key
   CRON_TOKEN=your_cron_token
   # Optional for full functionality:
   GMAIL_ACCOUNTS_JSON={"accounts": [...]}
   CALENDAR_CREDENTIALS_JSON={"type": "service_account", ...}
   ```

3. **Deploy with One Click**
   - Press the **Run** button
   - The `start.py` script handles everything:
     - ✅ Installs dependencies automatically
     - ✅ Validates environment variables  
     - ✅ Initializes SQLite database
     - ✅ Starts FastAPI server on port 8080

4. **Configure Webhooks**
   ```bash
   # Telegram Bot Webhook
   curl -X POST "https://api.telegram.org/bot<TOKEN>/setWebhook" \
     -d "url=https://your-repl.replit.dev/api/v1/telegram-webhook"
   
   # Gmail/Calendar: Use Cloud Function proxy (see below)
   ```

**Troubleshooting**: 
- 🚨 **Nix Error?** Run `python install_replit.py` for manual setup
- 📖 **Full Guide**: [REPLIT_DEPLOYMENT.md](REPLIT_DEPLOYMENT.md)
- 🔧 **Nix Issues**: [REPLIT_NIX_TROUBLESHOOTING.md](REPLIT_NIX_TROUBLESHOOTING.md)

### Cloud Function Proxy Setup

The proxy handles cold starts and provides reliable webhook processing:

1. **Deploy Gmail Webhook Proxy**
   ```bash
   cd proxy/
   gcloud functions deploy gmail-webhook-proxy \
     --runtime python39 \
     --trigger-http \
     --allow-unauthenticated \
     --entry-point gmail_webhook_proxy \
     --set-env-vars REPLIT_BASE_URL=https://your-repl.replit.dev
   ```

2. **Deploy Calendar Webhook Proxy**
   ```bash
   gcloud functions deploy calendar-webhook-proxy \
     --runtime python39 \
     --trigger-http \
     --allow-unauthenticated \
     --entry-point calendar_webhook_proxy \
     --set-env-vars REPLIT_BASE_URL=https://your-repl.replit.dev
   ```

3. **Configure Google APIs**
   - Gmail: Set webhook URL to Cloud Function URL
   - Calendar: Set webhook URL to Cloud Function URL

## 🤖 Telegram Bot Commands

| Command | Description | Example |
|---------|-------------|---------|
| `/start` | Initialize the bot | `/start` |
| `/help` | Show available commands | `/help` |
| `/add <task>` | Create a new task | `/add Review quarterly reports` |
| `/done <id>` | Mark task as completed | `/done 123` |
| `/list` | List all tasks by priority | `/list` |
| `/calendar <date> <time> <event>` | Create calendar event | `/calendar 2024-01-15 14:30 Team meeting` |

## 📊 API Documentation

### Core Endpoints

- **Health Check**: `GET /health`
- **API Health**: `GET /api/v1/health`
- **Metrics**: `GET /api/v1/metrics` (Prometheus format)
- **Circuit Breakers**: `GET /api/v1/circuit-breakers`

### Task Management

- **List Tasks**: `GET /api/v1/tasks`
- **Get Task**: `GET /api/v1/tasks/{id}`
- **Update Task**: `PUT /api/v1/tasks/{id}`
- **Delete Task**: `DELETE /api/v1/tasks/{id}`

### Webhooks

- **Telegram**: `POST /api/v1/webhook/telegram`
- **Gmail**: `POST /api/v1/webhook/gmail`
- **Calendar**: `POST /api/v1/webhook/calendar`

### Summaries & Backups

- **Daily Summary**: `GET /api/v1/daily-summary`
- **Cron Summary**: `POST /api/v1/cron/daily-summary`
- **Create Backup**: `POST /api/v1/backup/create`
- **List Backups**: `GET /api/v1/backup/list`
- **Backup Stats**: `GET /api/v1/backup/stats`

Full API documentation available at `/docs` when running the application.

## 🧪 Testing

### Running Tests

```bash
# Run all tests with coverage
python run_tests.py

# Run specific test types
python -m pytest tests/unit/ -v
python -m pytest tests/integration/ -v

# Run with coverage report
python -m pytest --cov=. --cov-report=html
```

### Test Structure

```
tests/
├── unit/                 # Unit tests
│   ├── core/            # Core functionality tests
│   └── services/        # Service layer tests
├── integration/         # Integration tests
│   └── test_api_endpoints.py
└── conftest.py          # Test configuration
```

### Performance Testing with Locust

1. **Install Locust**
   ```bash
   pip install locust
   ```

2. **Create Load Test Script**
   ```python
   # locustfile.py
   from locust import HttpUser, task, between
   
   class PersonalAssistantUser(HttpUser):
       wait_time = between(1, 3)
       
       @task(3)
       def health_check(self):
           self.client.get("/health")
       
       @task(2)
       def list_tasks(self):
           self.client.get("/api/v1/tasks")
       
       @task(1)
       def get_metrics(self):
           self.client.get("/api/v1/metrics")
   ```

3. **Run Load Tests**
   ```bash
   # Local testing
   locust -f locustfile.py --host=http://localhost:8080
   
   # Production testing
   locust -f locustfile.py --host=https://your-repl.replit.dev \
          --users 100 --spawn-rate 10 --run-time 5m --html report.html
   ```

## 📈 Monitoring & Observability

### Prometheus Metrics

The application exposes comprehensive metrics at `/api/v1/metrics`:

- **HTTP Metrics**: Request count, duration, status codes
- **Task Metrics**: Tasks created, completed, current counts by priority
- **External API Metrics**: Request counts and durations for Gemini, Telegram, Gmail, Calendar
- **Circuit Breaker Metrics**: State, failure counts, success rates
- **Business Metrics**: Daily summaries sent, backups created, notifications processed

### Grafana Dashboard

Example Grafana queries:

```promql
# Request rate
rate(http_requests_total[5m])

# Task creation rate
rate(tasks_total[1h])

# Circuit breaker status
circuit_breaker_state

# API response times
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))
```

### Logging

Structured logging with request IDs:

```json
{
  "timestamp": "2024-01-01T12:00:00Z",
  "level": "info",
  "message": "Task created",
  "request_id": "uuid-here",
  "task_id": 123,
  "source": "user@example.com",
  "priority": "normal"
}
```

## 🛡️ Security

### Security Features

- **Circuit Breakers**: Prevent cascading failures
- **Rate Limiting**: 1000 requests/minute per IP
- **Input Sanitization**: XSS and injection prevention
- **Security Headers**: CSP, HSTS, X-Frame-Options, etc.
- **Token Validation**: Webhook token verification
- **Secret Management**: Environment-based configuration

### Security Headers

```http
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
Strict-Transport-Security: max-age=31536000; includeSubDomains
Content-Security-Policy: default-src 'self'
```

### Rate Limiting

- General API: 1000 requests/minute
- Webhooks: 100 requests/minute
- Per-IP tracking with in-memory storage

## 🔄 CI/CD Pipeline

### GitHub Actions Workflow

The CI/CD pipeline includes:

1. **Code Quality Checks**
   - Black formatting
   - Ruff linting
   - Secret detection with detect-secrets

2. **Testing**
   - Unit tests with coverage
   - Integration tests
   - Security scanning with Bandit

3. **Build & Validation**
   - Application startup validation
   - OpenAPI schema generation

4. **Deployment**
   - Staging deployment (develop branch)
   - Production deployment (main branch)
   - Smoke tests

5. **Performance Testing**
   - Locust load testing on staging

### Quality Gates

- ✅ Code formatting (Black)
- ✅ Linting (Ruff)
- ✅ Security scan (Bandit, detect-secrets)
- ✅ Test coverage ≥80%
- ✅ All tests passing
- ✅ No high-severity vulnerabilities

## 🐛 Troubleshooting

### Common Issues

1. **Cold Start Timeouts**
   - Use Cloud Function proxy for webhooks
   - Implement proper retry logic
   - Monitor circuit breaker states

2. **Gmail API Quota Exceeded**
   - Check API usage in Google Cloud Console
   - Implement exponential backoff
   - Monitor rate limiting metrics

3. **Database Lock Errors**
   - Check concurrent operations
   - Review SQLite WAL mode configuration
   - Consider PostgreSQL for high load

4. **Telegram Webhook Failures**
   - Verify webhook URL accessibility
   - Check secret token configuration
   - Monitor webhook metrics

### Debug Mode

Enable debug logging:

```bash
export DEBUG=true
export LOG_LEVEL=DEBUG
python main.py
```

### Health Checks

Monitor application health:

```bash
# Application health
curl https://your-repl.replit.dev/health

# API health
curl https://your-repl.replit.dev/api/v1/health

# Circuit breaker status
curl https://your-repl.replit.dev/api/v1/circuit-breakers
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests (`python run_tests.py`)
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

### Development Guidelines

- Follow PEP 8 style guide
- Write comprehensive tests
- Update documentation
- Use conventional commit messages
- Ensure CI/CD pipeline passes

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [FastAPI](https://fastapi.tiangolo.com/) - Modern web framework
- [SQLAlchemy](https://www.sqlalchemy.org/) - Database ORM
- [python-telegram-bot](https://python-telegram-bot.org/) - Telegram Bot API
- [Google APIs](https://developers.google.com/) - Gmail and Calendar integration
- [Gemini AI](https://ai.google.dev/) - AI-powered text analysis
- [Prometheus](https://prometheus.io/) - Monitoring and alerting

## 📞 Support

- 📧 Email: support@example.com
- 💬 Telegram: @PersonalAssistantBot
- 🐛 Issues: [GitHub Issues](https://github.com/your-org/personal-assistant-bot/issues)
- 📖 Documentation: [Wiki](https://github.com/your-org/personal-assistant-bot/wiki)

---

Made with ❤️ by the Personal Assistant Bot Team