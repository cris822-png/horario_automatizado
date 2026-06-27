from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    DATABASE_URL: str = "postgresql+asyncpg://turno:turno@localhost:5432/turnodeportivo"
    SECRET_KEY: str = "cambia-esto-en-produccion-minimo-32-caracteres"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480
    ENV: str = "development"
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://localhost:8080"
    FCM_SERVER_KEY: str = ""
    WHATSAPP_API_TOKEN: str = ""
    WHATSAPP_PHONE_ID: str = ""
    HORAS_MAX_SEMANA: int = 40
    DESCANSO_MIN_ENTRE_TURNOS_HORAS: int = 12
    DIAS_DESCANSO_MIN_SEMANA: int = 2

    @property
    def allowed_origins_list(self) -> List[str]:
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",")]


settings = Settings()
