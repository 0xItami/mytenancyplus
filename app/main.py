import time
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from uuid import uuid4

import structlog
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from sqlalchemy import text

from app.api.router import api_router
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db.session import engine

configure_logging()
logger = structlog.get_logger()
settings = get_settings()
REQUESTS = Counter("http_requests_total", "HTTP requests", ["method", "path", "status"])
LATENCY = Histogram("http_request_duration_seconds", "HTTP request duration", ["method", "path"])


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    async with engine.connect() as connection:
        await connection.execute(text("SELECT 1"))
    await logger.ainfo("application_started", environment=settings.environment)
    yield
    await engine.dispose()
    await logger.ainfo("application_stopped")


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    summary="Multi-tenant property operations platform",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

CallNext = Callable[[Request], Awaitable[Response]]


@app.middleware("http")
async def request_context(request: Request, call_next: CallNext) -> Response:
    request_id = request.headers.get("X-Request-ID", str(uuid4()))
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(request_id=request_id)
    started = time.perf_counter()
    response = await call_next(request)
    route = request.scope.get("route")
    path = getattr(route, "path", request.url.path)
    duration = time.perf_counter() - started
    REQUESTS.labels(request.method, path, response.status_code).inc()
    LATENCY.labels(request.method, path).observe(duration)
    response.headers["X-Request-ID"] = request_id
    await logger.ainfo(
        "request_completed",
        method=request.method,
        path=path,
        status=response.status_code,
        duration_ms=round(duration * 1000, 2),
    )
    return response


@app.get("/metrics", include_in_schema=False)
async def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


app.include_router(api_router, prefix="/api/v1")
