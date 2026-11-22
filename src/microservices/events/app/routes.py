from fastapi import APIRouter

from app.models import EventResponse, MovieEvent, PaymentEvent, UserEvent
from app.service import (
    publish_movie_event,
    publish_payment_event,
    publish_user_event,
)

router = APIRouter(prefix="/api/events", tags=["events"])


@router.get("/health", tags=["health"])
async def events_health() -> dict:
    return {"status": True}


@router.post("/movie", response_model=EventResponse, status_code=201)
async def create_movie_event(payload: MovieEvent) -> EventResponse:
    return await publish_movie_event(payload)


@router.post("/user", response_model=EventResponse, status_code=201)
async def create_user_event(payload: UserEvent) -> EventResponse:
    return await publish_user_event(payload)


@router.post("/payment", response_model=EventResponse, status_code=201)
async def create_payment_event(payload: PaymentEvent) -> EventResponse:
    return await publish_payment_event(payload)
