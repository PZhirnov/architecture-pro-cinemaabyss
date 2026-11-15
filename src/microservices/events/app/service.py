import logging
from datetime import datetime, timezone

from app.config import settings
from app.models import Event, EventResponse, MovieEvent, PaymentEvent, UserEvent
from app.producer import producer

logger = logging.getLogger("events-service.service")


async def _publish(
    topic: str,
    key: str,
    event_type: str,
    business_id: int,
    action: str,
    payload: dict,
) -> EventResponse:
    event = Event(
        id=f"{event_type}-{business_id}-{action}",
        type=event_type,
        timestamp=datetime.now(timezone.utc),
        payload=payload,
    )
    message = event.model_dump(mode="json")
    partition, offset = await producer.send(topic, key=key, value=message)

    logger.info(
        "event published: id=%s type=%s topic=%s partition=%d offset=%d",
        event.id, event_type, topic, partition, offset,
    )
    return EventResponse(status="success", partition=partition, offset=offset, event=event)


async def publish_movie_event(payload: MovieEvent) -> EventResponse:
    return await _publish(
        topic=settings.topic_movie_events,
        key=str(payload.movie_id),
        event_type="movie",
        business_id=payload.movie_id,
        action=payload.action,
        payload=payload.model_dump(mode="json", exclude_none=True),
    )


async def publish_user_event(payload: UserEvent) -> EventResponse:
    return await _publish(
        topic=settings.topic_user_events,
        key=str(payload.user_id),
        event_type="user",
        business_id=payload.user_id,
        action=payload.action,
        payload=payload.model_dump(mode="json", exclude_none=True),
    )


async def publish_payment_event(payload: PaymentEvent) -> EventResponse:
    return await _publish(
        topic=settings.topic_payment_events,
        key=str(payload.payment_id),
        event_type="payment",
        business_id=payload.payment_id,
        action=payload.status,
        payload=payload.model_dump(mode="json", exclude_none=True),
    )
