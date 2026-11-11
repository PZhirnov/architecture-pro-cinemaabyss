from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    port: int = 8000

    monolith_url: str = "http://localhost:8080"
    movies_service_url: str = "http://localhost:8081"
    events_service_url: str = "http://localhost:8082"

    gradual_migration: bool = True
    movies_migration_percent: int = 50

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
