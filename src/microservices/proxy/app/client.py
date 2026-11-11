"""
HTTP-клиент и хелпер проксирования
"""
import httpx
from fastapi import Request, Response, HTTPException

# Один общий AsyncClient на всё приложение — переиспользует пул соединений
http_client = httpx.AsyncClient(timeout=30.0)

# Заголовки, которые нельзя пробрасывать «как есть»
_SKIP_REQ_HEADERS = {"host", "content-length"}
_SKIP_RESP_HEADERS = {"content-length", "content-encoding", "transfer-encoding", "connection"}


async def proxy_request(base_url: str, path: str, request: Request) -> Response:
    """Пробрасывает входящий запрос к целевому сервису и возвращает его ответ."""
    url = f"{base_url}{path}"

    headers = {k: v for k, v in request.headers.items() if k.lower() not in _SKIP_REQ_HEADERS}
    body = await request.body()

    try:
        upstream = await http_client.request(
            method=request.method,
            url=url,
            headers=headers,
            content=body,
            params=request.query_params,
        )
    except httpx.RequestError as exc:
        raise HTTPException(status_code=502, detail=f"Upstream error: {exc}") from exc

    response_headers = {
        k: v for k, v in upstream.headers.items() if k.lower() not in _SKIP_RESP_HEADERS
    }

    return Response(
        content=upstream.content,
        status_code=upstream.status_code,
        headers=response_headers,
        media_type=upstream.headers.get("content-type"),
    )
