from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )



    # HTTP
    host: str = "0.0.0.0"
    port: int = 8082
    log_level: str = "INFO"

    # Kafka
    # kafka_bootstrap_servers: str = "kafka:9092" # если запускаем с помощью Docker-compose
    # kafka_bootstrap_servers: str = "localhost:9092"

    # Из глобального окружения может быть переданы "KAFKA_BOOTSTRAP_SERVERS", "KAFKA_BROKERS"
    kafka_bootstrap_servers: str = Field(
        default="kafka:9092",
        validation_alias=AliasChoices("KAFKA_BOOTSTRAP_SERVERS", "KAFKA_BROKERS"),
    )
    kafka_client_id: str = "events-service"
    kafka_consumer_group: str = "events-service"

    # Топики (имена должны совпадать с KAFKA_CREATE_TOPICS в docker-compose)
    topic_movie_events: str = "movie-events"
    topic_user_events: str = "user-events"
    topic_payment_events: str = "payment-events"

    # Producer
    kafka_acks: str = "all"
    kafka_enable_idempotence: bool = True
    kafka_request_timeout_ms: int = 30_000

    # Consumer
    kafka_auto_offset_reset: str = "earliest"       # earliest — читать всё с начала
    kafka_enable_auto_commit: bool = True
    kafka_max_poll_records: int = 100

    # Стартовый retry: Kafka может ещё не подняться, когда стартует сервис
    kafka_start_max_attempts: int = 15
    kafka_start_retry_delay: float = 3.0


settings = Settings()
