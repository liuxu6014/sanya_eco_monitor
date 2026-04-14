from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_DIR = Path(__file__).resolve().parent
DEFAULT_SQLITE_PATH = (BACKEND_DIR / "sanya_eco.db").resolve()


class Settings(BaseSettings):
    PLATFORM_BASE_URL: str = "https://zhnlkj.com/iotSmasrt"
    SENSOR_BASE_URL: str = "https://zhnlkj.com/iotSmasrt"
    PLATFORM_USERNAME: str = "zhnl"
    PLATFORM_PASSWORD: str = "123456"

    INSECT_CODE: str = "202603172301"
    SPORE_CODE: str = "202603172302"
    INSECT_LOOKBACK_HOURS: int = 168
    SPORE_LOOKBACK_HOURS: int = 168
    WEATHER_CODE: str = "16110669"
    SOIL_CODE: str = "16110670"
    PREVENTION_CODE: str = "864249073501866"
    SEEDLING_CODE: str = "FM9400487"

    WHXPH_BASE_URL: str = "https://iot.whxph.com:44300/XPHapiv2"
    WHXPH_USERNAME: str = ""
    WHXPH_PASSWORD: str = ""
    RAIN_GAUGE_ID: str = ""
    FLOW_METER_ID: str = ""
    LEVEL_GAUGE_ID: str = ""
    RUNOFF_CODES: str = "16132920,16132921,16132922,16132923,16132924,16132925"
    RAIN_GAUGE_CODES: str = ""
    WATER_QUALITY_CODE: str = ""


    DATABASE_URL: str = f"sqlite+aiosqlite:///{DEFAULT_SQLITE_PATH.as_posix()}"

    COLLECT_INTERVAL_MINUTES: int = 30
    ACCESS_PASSWORD: str = ""
    AUTH_COOKIE_NAME: str = "sanya_monitor_auth"
    AUTH_MAX_AGE_HOURS: int = 12

    APP_TITLE: str = "三亚市天涯区橡胶林近自然化改造和农田提升监测平台"
    DEBUG: bool = True

    LLM_API_KEY: str = ""
    LLM_BASE_URL: str = "https://api.deepseek.com/v1"
    LLM_MODEL: str = "deepseek-chat"

    IMAGE_GEN_API_KEY: str = ""
    IMAGE_GEN_BASE_URL: str = "https://yinli.one/v1"
    IMAGE_GEN_MODEL: str = "gemini-2.5-flash-image-preview"

    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("DEBUG", mode="before")
    @classmethod
    def parse_debug(cls, value):
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"1", "true", "yes", "on", "debug", "development", "dev"}:
                return True
            if normalized in {"0", "false", "no", "off", "release", "production", "prod"}:
                return False
        return value


settings = Settings()
