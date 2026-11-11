import asyncio
import json
import logging

from aiokafka import AIOKafkaConsumer

from app.config import settings

logger = logging.getLogger("events-service.consumer")


class EventsConsumer:
    def __init__(self) -> None:
        self._consumer: AIOKafkaConsumer | None = None
        self._task: asyncio.Task | None = None

    async def start(self) -> None:
        self._consumer = AIOKafkaConsumer(
            settings.topic_movie_events,
            settings.topic_user_events,
            settings.topic_payment_events,
            bootstrap_servers=settings.kafka_bootstrap_servers,
            group_id=settings.kafka_consumer_group,
            client_id=f"{settings.kafka_client_id}-consumer",
            auto_offset_reset=settings.kafka_auto_offset_reset,
            enable_auto_commit=settings.kafka_enable_auto_commit,
            max_poll_records=settings.kafka_max_poll_records,
            value_deserializer=lambda b: json.loads(b.decode("utf-8")),
        )
        await self._consumer.start()
        self._task = asyncio.create_task(self._consume_loop(), name="events-consumer")
        logger.info(
            "consumer started: topics=%s group=%s",
            sorted(self._consumer.subscription()),
            settings.kafka_consumer_group,
        )

    async def stop(self) -> None:
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        if self._consumer is not None:
            await self._consumer.stop()
            self._consumer = None
            logger.info("consumer stopped")

    async def _consume_loop(self) -> None:
        assert self._consumer is not None
        while True:
            try:
                async for msg in self._consumer:
                    logger.info(
                        "event received: topic=%s partition=%d offset=%d key=%s value=%s",
                        msg.topic,
                        msg.partition,
                        msg.offset,
                        msg.key.decode() if msg.key else None,
                        msg.value,
                    )
            except asyncio.CancelledError:
                logger.info("consume loop cancelled")
                raise
            except Exception as exc:
                # Сетевые ошибки/ребаланс — не падаем, переподключаемся через паузу
                logger.exception("consume loop error, retrying in 2s: %s", exc)
                await asyncio.sleep(2)


consumer = EventsConsumer()
