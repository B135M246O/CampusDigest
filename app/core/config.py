from pathlib import Path
from secrets import token_urlsafe
from typing import Optional
from urllib.parse import urljoin

from pydantic import BaseSettings, EmailStr, Field
from sqlalchemy.engine import URL

BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    APP_TITLE: str = 'CampusDigest'
    APP_DESCRIPTION: str = 'Публичные новости вузов и студенческие объявления'
    HOST: str = '127.0.0.1'
    PORT: int = 8006
    DOMAIN: bool = False
    DOMAIN_NAME: str = 'http://127.0.0.1:8006/'
    DEBUG: bool = False
    POSTGRES_DB: str = 'campusdigest'
    POSTGRES_USER: str = 'campusdigest'
    POSTGRES_PASSWORD: str = 'replace-with-local-database-password'
    DB_HOST: str = 'localhost'
    DB_PORT: int = 5432
    DATABASE_URL: Optional[str] = None
    SECRET: str = Field(default_factory=lambda: token_urlsafe(32))
    PARSER_FREQUENCY: int = Field(30, ge=1)
    STORAGE_DAYS: int = Field(30, ge=0)
    ENABLE_SCHEDULER: bool = False
    FIRST_SUPERUSER_EMAIL: Optional[EmailStr] = None
    FIRST_SUPERUSER_PASSWORD: Optional[str] = None
    FIRST_SUPERUSER_CHAT_ID: Optional[int] = None
    IP: str = '127.0.0.1'
    BOT_ENABLED: bool = False
    WEBHOOK: bool = False
    BOT_TOKEN: Optional[str] = None
    BOT_PERSISTENCE_FILE: str = str(BASE_DIR / 'app/bot/data/bot_persistence_file')
    INSTANT_VIEW: bool = False
    RHASH: Optional[str] = None
    LOG_LOCATION: str = str(BASE_DIR / 'logs/warning.log')
    LOG_ROTATION: str = '12:00'
    LOG_COMPRESSION: str = 'tar.gz'
    LOG_LEVEL: str = 'WARNING'

    @property
    def database_url(self) -> str:
        if self.DATABASE_URL:
            return self.DATABASE_URL
        return URL.create(
            'postgresql+asyncpg', username=self.POSTGRES_USER,
            password=self.POSTGRES_PASSWORD, host=self.DB_HOST,
            port=self.DB_PORT, database=self.POSTGRES_DB,
        ).render_as_string(hide_password=False)

    @property
    def telegram_webhook_url(self) -> str:
        return urljoin(self.DOMAIN_NAME.rstrip('/') + '/', 'telegram/webhook')

    class Config:
        env_file = str(BASE_DIR / '.env')


settings = Settings()
