"""Application settings and configuration"""
import os
from dataclasses import dataclass
from typing import List, Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


@dataclass
class DatabaseConfig:
    """Database configuration"""
    host: str
    port: int
    database: str
    username: str
    password: str
    pool_min_size: int = 5
    pool_max_size: int = 20


@dataclass
class BotConfig:
    """Bot configuration"""
    token: str
    admin_ids: List[int]


@dataclass
class AIConfig:
    """OpenAI API configuration"""
    api_key: str
    model: str = "gpt-4o-mini"
    max_tokens: int = 900


@dataclass
class GoogleSheetsConfig:
    """Google Sheets configuration"""
    spreadsheet_id: str
    worksheet_name: str
    credentials_json: Optional[str] = None
    credentials_path: Optional[str] = None


@dataclass
class WebhookConfig:
    """Webhook configuration"""
    webhook_path: str
    webhook_url: str
    certificate_path: Optional[str] = None


@dataclass
class Settings:
    """Application settings"""
    database: DatabaseConfig
    bot: BotConfig
    ai: AIConfig
    google_sheets: GoogleSheetsConfig
    webhook: Optional[WebhookConfig] = None

    @classmethod
    def from_env(cls) -> "Settings":
        """Load settings from environment variables"""
        # Database config
        db_config = DatabaseConfig(
            host=os.getenv("DB_HOST", "178.208.85.128"),
            port=int(os.getenv("DB_PORT", "3306")),
            database=os.getenv("DB_NAME", "order_bot"),
            username=os.getenv("DB_USER", "telegram_bot"),
            password=os.getenv("DB_PASSWORD", ""),
            pool_min_size=int(os.getenv("DB_POOL_MIN", "5")),
            pool_max_size=int(os.getenv("DB_POOL_MAX", "20")),
        )

        # Bot config
        admin_ids_str = os.getenv("BOT_ADMIN_IDS", "")
        admin_ids = [int(id.strip()) for id in admin_ids_str.split(",") if id.strip()]
        
        bot_config = BotConfig(
            token=os.getenv("BOT_TOKEN", ""),
            admin_ids=admin_ids,
        )

        # AI config
        ai_config = AIConfig(
            api_key=os.getenv("OPENAI_API_KEY", ""),
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            max_tokens=int(os.getenv("OPENAI_MAX_TOKENS", "900")),
        )

        # Google Sheets config
        google_sheets_config = GoogleSheetsConfig(
            spreadsheet_id=os.getenv("GOOGLE_SHEETS_ID", ""),
            worksheet_name=os.getenv("GOOGLE_SHEETS_WORKSHEET", "Заказы"),
            credentials_json=os.getenv("GOOGLE_SHEETS_CREDENTIALS_JSON", None),
            credentials_path=os.getenv("GOOGLE_SHEETS_CREDENTIALS_PATH", None),
        )

        # Webhook config (optional)
        webhook_config = None
        webhook_url = os.getenv("WEBHOOK_URL", "")
        webhook_path = os.getenv("WEBHOOK_PATH", "")
        if webhook_url and webhook_path:
            webhook_config = WebhookConfig(
                webhook_path=webhook_path,
                webhook_url=webhook_url,
                certificate_path=os.getenv("WEBHOOK_CERTIFICATE_PATH", None),
            )

        return cls(
            database=db_config,
            bot=bot_config,
            ai=ai_config,
            google_sheets=google_sheets_config,
            webhook=webhook_config,
        )


# Global settings instance
_settings: Settings = None


def get_settings() -> Settings:
    """Get application settings (singleton)"""
    global _settings
    if _settings is None:
        _settings = Settings.from_env()
    return _settings

