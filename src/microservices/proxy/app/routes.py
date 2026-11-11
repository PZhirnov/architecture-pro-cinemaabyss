"""
Маршрутизация и распределение трафика
"""

import random

from fastapi import APIRouter, HTTPException, Request, Response

from app.client import proxy_request
from app.config import settings

router = APIRouter()

PROXY_METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"]


@router.get("/health", tags=["health"])
async def proxy_health() -> Response:
    """Health-check самого API Gateway."""
    return Response(content="Proxy is healthy", media_type="text/plain")


def _pick_movies_backend() -> str:
    """Тест - Стратегия Strangler Fig: часть трафика на новый сервис, часть — на монолит."""
    # if (
    #     settings.gradual_migration
    #     and random.uniform(0, 100) < settings.movies_migration_percent
    # ):
    #     return settings.movies_service_url
    # return settings.monolith_url

    """Трафиком будем управлять из кубера"""
    return settings.movies_service_url

def _resolve_backend(path: str) -> str:
    """Определяет целевой сервис по пути запроса."""
    # Health-эндпоинты микросервисов — всегда в свой сервис
    if path == "/api/movies/health":
        return settings.movies_service_url
    if path == "/api/events/health":
        return settings.events_service_url

    # Фильмы — с миграцией
    if path == "/api/movies" or path.startswith("/api/movies/"):
        return _pick_movies_backend()

    # События — в events-service
    if path == "/api/events" or path.startswith("/api/events/"):
        return settings.events_service_url

    # Монолитные домены
    for prefix in ("/api/users", "/api/payments", "/api/subscriptions"):
        if path == prefix or path.startswith(prefix + "/"):
            return settings.monolith_url

    raise HTTPException(status_code=404, detail=f"Route not found: {path}")


@router.api_route("/api/{full_path:path}", methods=PROXY_METHODS, include_in_schema=False)
async def proxy(full_path: str, request: Request) -> Response:
    """Единая точка проксирования всех /api/* запросов."""
    path = f"/api/{full_path}"
    backend = _resolve_backend(path)
    return await proxy_request(backend, path, request)
