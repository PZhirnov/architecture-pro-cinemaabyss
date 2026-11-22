import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import settings
from app.consumer import consumer
from app.producer import producer
from app.routes import router

logging.basicConfig(
    level=settings.log_level,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("events-service")


async def _start_kafka() -> None:
    """Kafka может ещё не принимать соединения — ретраим с паузой."""
    last_exc: Exception | None = None
    for attempt in range(1, settings.kafka_start_max_attempts + 1):
        try:
            await producer.start()
            await consumer.start()
            return
        except Exception as exc:
            last_exc = exc
            logger.warning(
                "kafka start attempt %d/%d failed: %s",
                attempt, settings.kafka_start_max_attempts, exc,
            )
            await producer.stop()
            await consumer.stop()
            await asyncio.sleep(settings.kafka_start_retry_delay)
    raise RuntimeError(f"Kafka unavailable after retries: {last_exc}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(
        "starting: kafka=%s group=%s topics=[%s,%s,%s]",
        settings.kafka_bootstrap_servers,
        settings.kafka_consumer_group,
        settings.topic_movie_events,
        settings.topic_user_events,
        settings.topic_payment_events,
    )
    await _start_kafka()
    try:
        yield
    finally:
        await consumer.stop()
        await producer.stop()
        logger.info("stopped")


app = FastAPI(
    title="CinemaAbyss Events Service",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(router)


@app.get("/health", include_in_schema=False)
async def health() -> dict:
    """Плоский health для docker-healthcheck."""
    return {"status": True}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level.lower(),
    )