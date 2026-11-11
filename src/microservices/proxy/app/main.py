from contextlib import asynccontextmanager
from pathlib import Path

import yaml
from fastapi import FastAPI, Response

from app.client import http_client
from app.config import settings
from app.routes import router

# --- Загрузка статической OpenAPI-спецификации ---
OPENAPI_SPEC_PATH = Path(__file__).parent / "api-specification.yaml"
_openapi_spec: dict = yaml.safe_load(OPENAPI_SPEC_PATH.read_text(encoding="utf-8"))


@asynccontextmanager
async def lifespan(app: FastAPI):
    print(
        f"[proxy] monolith={settings.monolith_url} "
        f"movies={settings.movies_service_url} "
        f"events={settings.events_service_url} "
        f"migration={settings.gradual_migration} "
        f"movies_percent={settings.movies_migration_percent}%"
    )
    yield
    await http_client.aclose()


app = FastAPI(
    title="CinemaAbyss API Gateway",
    version="1.0.0",
    docs_url="/docs",          # Swagger UI
    redoc_url="/redoc",        # ReDoc
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# Главное: отдаём в /openapi.json нашу статическую спеку,
# а не автогенерируемую из catch-all роутов.
def custom_openapi() -> dict:
    return _openapi_spec


app.openapi = custom_openapi  # type: ignore[method-assign]


# Дополнительно: отдать сам YAML (удобно для импорта в Postman/Insomnia/генераторов клиентов)
@app.get("/openapi.yaml", include_in_schema=False)
async def openapi_yaml() -> Response:
    return Response(
        content=OPENAPI_SPEC_PATH.read_text(encoding="utf-8"),
        media_type="application/yaml",
    )


app.include_router(router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=settings.port)

