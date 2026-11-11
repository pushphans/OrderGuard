from pydantic_settings import BaseSettings, SettingsConfigDict



class Settings(BaseSettings):
    DATABASE_URL : str
    JWT_SECRET_KEY : str
    ALGORITHM : str
    MAIN_BACKEND_URL : str
    SERVICE_SECRET : str
    GROQ_API_KEY : str | None = None



    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True
    )



settings = Settings()
