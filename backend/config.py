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
    WATER_QUALITY_CODE: str = "16133028"


    DATABASE_URL: str = f"sqlite+aiosqlite:///{DEFAULT_SQLITE_PATH.as_posix()}"

    COLLECT_INTERVAL_MINUTES: int = 30
    ACCESS_PASSWORD: str = ""
    AUTH_COOKIE_NAME: str = "sanya_monitor_auth"
    AUTH_MAX_AGE_HOURS: int = 12
    LOG_DIR: str = str((BACKEND_DIR.parent / "logs" / "backend").resolve())
    LOG_LEVEL: str = "INFO"
    LOG_FILE_MAX_BYTES: int = 10 * 1024 * 1024
    LOG_FILE_BACKUP_COUNT: int = 5
    SQLALCHEMY_ECHO: bool = False
    ENABLE_AI_IMAGE_GEN: bool = True
    DEVICE_STATUS_CACHE_SECONDS: int = 60
    ANALYTICS_DASHBOARD_CACHE_SECONDS: int = 60

    APP_TITLE: str = "三亚市天涯区橡胶林近自然化改造和农田提升监测平台"
    DEBUG: bool = True

    LLM_API_KEY: str = ""
    LLM_BASE_URL: str = "https://api.deepseek.com/v1"
    LLM_MODEL: str = "deepseek-chat"

    IMAGE_GEN_API_KEY: str = ""
    IMAGE_GEN_BASE_URL: str = "https://yinli.one/v1"
    IMAGE_GEN_MODEL: str = "gemini-2.5-flash-image-preview"

    QWEATHER_ENABLED: bool = True
    QWEATHER_API_HOST: str = ""
    QWEATHER_API_KEY: str = ""
    QWEATHER_LOCATION: str = "109.430,18.360"
    QWEATHER_LANG: str = "zh"
    QWEATHER_UNIT: str = "m"
    QWEATHER_CACHE_SECONDS: int = 1800

    GUIDELINE_BASELINE_DAYS: int = 30
    GUIDELINE_RECENT_DAYS: int = 30
    GUIDELINE_REFERENCE_RUNOFF_CODE: str = "16132922"
    GUIDELINE_INSECT_WARNING_THRESHOLD: int = 20
    GUIDELINE_SPORE_WARNING_THRESHOLD: int = 10
    WARNING_INSECT_THRESHOLDS: str = "40,80,100,120"
    WARNING_SPORE_THRESHOLDS: str = "10,30,60,90"
    WARNING_RAINFALL_THRESHOLDS: str = "10,25,50,80"
    WARNING_SAND_THRESHOLDS: str = "0.0003,0.0008,0.0015,0.003"
    WARNING_HISTORY_NOTE: str = "历史同口径对比数据暂缺，当前仅展示本期监测判定，后续可补充同比和环比分析。"

    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator(
        "DEBUG",
        "SQLALCHEMY_ECHO",
        "ENABLE_AI_IMAGE_GEN",
        "QWEATHER_ENABLED",
        mode="before",
    )
    @classmethod
    def parse_bool_fields(cls, value):
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
