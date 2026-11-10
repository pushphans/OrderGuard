from pydantic_settings import BaseSettings, SettingsConfigDict



class Settings(BaseSettings):
    DATABASE_URL : str
    ACCESS_TOKEN_EXPIRY_IN_MINUTES : int
    REFRESH_TOKEN_EXPIRY_IN_DAYS : int
    JWT_SECRET_KEY : str
    ALGORITHM : str



    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True
    )


settings = Settings()
