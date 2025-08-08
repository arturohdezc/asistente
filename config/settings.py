from pydantic import Field, field_validator
from pydantic_settings import BaseSettings
from typing import Dict, List, Optional
import json
import os
from pathlib import Path

class Settings(BaseSettings):
    """Application settings using Pydantic BaseSettings"""
    
    # Telegram Configuration
    telegram_token: str = Field(..., env="TELEGRAM_TOKEN")
    telegram_webhook_secret: str = Field(..., env="TELEGRAM_WEBHOOK_SECRET")
    
    # Gmail Configuration
    gmail_accounts_json: str = Field(..., env="GMAIL_ACCOUNTS_JSON")
    
    # Google Calendar Configuration
    calendar_credentials_json: str = Field(..., env="CALENDAR_CREDENTIALS_JSON")
    
    # Gemini AI Configuration
    gemini_api_key: str = Field(..., env="GEMINI_API_KEY")
    gemini_model: str = Field(default="gemini-1.5-flash", env="GEMINI_MODEL")
    
    # Cron Configuration
    cron_token: str = Field(..., env="CRON_TOKEN")
    
    # Database Configuration
    database_url: str = Field(
        default="sqlite+aiosqlite:///./db.sqlite3",
        env="DATABASE_URL"
    )
    
    # Backup Configuration
    backup_directory: str = Field(
        default="./backups",
        env="BACKUP_DIRECTORY"
    )
    backup_retention_days: int = Field(default=7, env="BACKUP_RETENTION_DAYS")
    
    # Application Limits
    max_tasks_limit: int = Field(default=10000, env="MAX_TASKS_LIMIT")
    
    # Timezone
    timezone: str = Field(default="America/Mexico_City", env="TIMEZONE")
    
    # Development Settings
    debug: bool = Field(default=False, env="DEBUG")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    
    model_config = {
        "env_file": ".env",
        "case_sensitive": False,
        "extra": "ignore"
    }
        
    @field_validator('gmail_accounts_json')
    @classmethod
    def validate_gmail_accounts_json(cls, v):
        """Validate Gmail accounts JSON format"""
        try:
            accounts = json.loads(v)
            if not isinstance(accounts, dict) or 'accounts' not in accounts:
                raise ValueError('Gmail accounts JSON must contain "accounts" key')
            return v
        except json.JSONDecodeError:
            raise ValueError('Invalid JSON format for Gmail accounts')
    
    @field_validator('calendar_credentials_json')
    @classmethod
    def validate_calendar_credentials_json(cls, v):
        """Validate Calendar credentials JSON format"""
        try:
            credentials = json.loads(v)
            if not isinstance(credentials, dict):
                raise ValueError('Calendar credentials must be valid JSON object')
            return v
        except json.JSONDecodeError:
            raise ValueError('Invalid JSON format for Calendar credentials')
    
    @field_validator('backup_directory')
    @classmethod
    def validate_backup_directory(cls, v):
        """Ensure backup directory exists"""
        backup_path = Path(v)
        try:
            backup_path.mkdir(parents=True, exist_ok=True)
        except (OSError, PermissionError) as e:
            # If we can't create the directory, use a local fallback
            print(f"Warning: Could not create backup directory {v}: {e}")
            fallback_path = Path("./backups")
            fallback_path.mkdir(parents=True, exist_ok=True)
            return str(fallback_path)
        return v
    
    def get_gmail_accounts(self) -> List[Dict]:
        """Parse and return Gmail accounts list"""
        accounts_data = json.loads(self.gmail_accounts_json)
        return accounts_data.get('accounts', [])
    
    def get_calendar_credentials(self) -> Dict:
        """Parse and return Calendar credentials"""
        return json.loads(self.calendar_credentials_json)

# Global settings instance
settings = Settings()