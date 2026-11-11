import json
import logging

from aiokafka import AIOKafkaProducer

from app.config import settings

logger = logging.getLogger("events-service.producer")


class EventsProducer:
    def __init__(self) -> None:
        self._producer: AIOKafkaProducer | None = None

    async def start(self) -> None:
        self._producer = AIOKafkaProducer(
            bootstrap_servers=settings.kafka_bootstrap_servers,
            client_id=settings.kafka_client_id,
            acks=settings.kafka_acks,
            enable_idempotence=settings.kafka_enable_idempotence,
            request_timeout_ms=settings.kafka_request_timeout_ms,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            key_serializer=lambda k: str(k).encode("utf-8") if k is not None else None,
        )
        await self._producer.start()
        logger.info(
            "producer started: bootstrap=%s idempotence=%s acks=%s",
            settings.kafka_bootstrap_servers,
            settings.kafka_enable_idempotence,
            settings.kafka_acks,
        )

    async def stop(self) -> None:
        if self._producer is not None:
            await self._producer.stop()
            self._producer = None
            logger.info("producer stopped")

    async def send(self, topic: str, key: str, value: dict) -> tuple[int, int]:
        if self._producer is None:
            raise RuntimeError("Producer is not started")
        metadata = await self._producer.send_and_wait(topic, key=key, value=value)
        return metadata.partition, metadata.offset


producer = EventsProducer()