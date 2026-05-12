import json
import logging
import os
import time

from fastapi import FastAPI, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.status import HTTP_422_UNPROCESSABLE_CONTENT
from fastapi.middleware.cors import CORSMiddleware

from app.core.errors import ApiError, error_envelope, message_for_code
from app.core.request_context import get_correlation_id, normalize_correlation_id, set_correlation_id

from app.api.v1.router import api_v1
from app.core.logging import configure_logging
from app.infrastructure.db import models  # noqa: F401
from app.infrastructure.db.schema_compat import ensure_search_preference_columns
from app.infrastructure.db.seed import ensure_seed_users
from app.infrastructure.db.session import Base, engine

configure_logging()

run_db_init = os.getenv("RUN_DB_INIT", "false").lower() in {"1", "true", "yes"}
run_seed_users = os.getenv("RUN_SEED_USERS", "false").lower() in {"1", "true", "yes"}

if run_db_init:
    Base.metadata.create_all(bind=engine)
ensure_search_preference_columns(engine)
if run_seed_users:
    ensure_seed_users()

logger = logging.getLogger("app.access")


def _sanitize_request_body(body):
    if isinstance(body, dict):
        sanitized = {}
        for key, value in body.items():
            key_lower = key.lower()
            if "password" in key_lower or "token" in key_lower:
                sanitized[key] = "***"
            else:
                sanitized[key] = _sanitize_request_body(value)
        return sanitized
    if isinstance(body, list):
        return [_sanitize_request_body(item) for item in body]
    return body


async def _safe_request_body(request: Request):
    try:
        body = await request.body()
    except Exception:
        return None
    if not body:
        return None
    try:
        parsed = json.loads(body)
    except Exception:
        return body.decode("utf-8", errors="replace")[:2000]
    return _sanitize_request_body(parsed)


def _parse_cors_origins() -> list[str]:
    env_value = os.getenv("CORS_ALLOW_ORIGINS", "").strip()
    if env_value:
        origins = [item.strip() for item in env_value.split(",") if item.strip()]
        if origins:
            return origins

    return [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3101",
        "http://127.0.0.1:3101",
        "http://45.136.18.49:3000",
        "http://45.136.18.49:3101",
        "http://45.136.18.49:3200",
        "http://45.136.18.49:3300",
        "http://192.168.56.1:3000",
    ]


app = FastAPI(title="Viru API", version="0.1.0")


class AccessLogMiddleware:
    def __init__(self, app: FastAPI) -> None:
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        start = time.perf_counter()
        status_code = None

        async def send_wrapper(message):
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message.get("status")
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            elapsed_ms = int((time.perf_counter() - start) * 1000)
            headers = {k.decode(): v.decode() for k, v in scope.get("headers", [])}
            log_payload = {
                "event": "http",
                "correlation_id": get_correlation_id() or headers.get("x-correlation-id") or "-",
                "method": scope.get("method"),
                "path": scope.get("path"),
                "status": status_code or 500,
                "elapsed_ms": elapsed_ms,
                "client": scope.get("client")[0] if scope.get("client") else None,
                "origin": headers.get("origin"),
                "referer": headers.get("referer"),
                "user_agent": headers.get("user-agent"),
                "content_type": headers.get("content-type"),
                "ac_request_method": headers.get("access-control-request-method"),
                "ac_request_headers": headers.get("access-control-request-headers"),
            }
            logger.info(json.dumps(log_payload, ensure_ascii=False))
app.add_middleware(
    CORSMiddleware,
    allow_origins=_parse_cors_origins(),
    allow_origin_regex=os.getenv(
        "CORS_ALLOW_ORIGIN_REGEX",
        r"^https?://(45\.136\.18\.49|localhost|127\.0\.0\.1)(?::\d+)?$",
    ),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(AccessLogMiddleware)
app.include_router(api_v1, prefix="/api/v1")


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    body = exc.body
    if isinstance(body, dict) and "password" in body:
        body = {**body, "password": "***"}

    safe_errors = jsonable_encoder(exc.errors())
    logger.error(
        json.dumps(
            {
                "event": "validation_error",
                "path": request.url.path,
                "method": request.method,
                "errors": safe_errors,
                "body": body,
            },
            ensure_ascii=False,
        )
    )
    envelope = error_envelope(
        status=HTTP_422_UNPROCESSABLE_CONTENT,
        code="validation_error",
        message=message_for_code("validation_error"),
        details=safe_errors,
    )
    return JSONResponse(status_code=HTTP_422_UNPROCESSABLE_CONTENT, content=envelope)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    safe_body = await _safe_request_body(request)
    if isinstance(exc.detail, str):
        code = exc.detail
        details = []
    elif isinstance(exc.detail, list):
        code = "validation_error"
        details = exc.detail
    elif isinstance(exc.detail, dict):
        code = str(exc.detail.get("code") or "request_failed")
        raw_details = exc.detail.get("details", [])
        if isinstance(raw_details, (list, dict)):
            details = raw_details
        else:
            details = [{"detail": raw_details}]
    else:
        code = "request_failed"
        details = []
    logger.warning(
        json.dumps(
            {
                "event": "http_exception",
                "correlation_id": get_correlation_id() or getattr(request.state, "correlation_id", "") or "-",
                "path": request.url.path,
                "method": request.method,
                "query": dict(request.query_params),
                "status": exc.status_code,
                "code": code,
                "detail": exc.detail,
                "body": safe_body,
            },
            ensure_ascii=False,
        )
    )
    envelope = error_envelope(
        status=exc.status_code,
        code=code,
        message=str(exc.detail.get("message")) if isinstance(exc.detail, dict) and exc.detail.get("message") else message_for_code(code, fallback="Request failed."),
        details=details,
    )
    return JSONResponse(status_code=exc.status_code, content=envelope)


@app.exception_handler(ApiError)
async def api_error_handler(request: Request, exc: ApiError):
    envelope = error_envelope(
        status=exc.status,
        code=exc.code,
        message=exc.message,
        details=exc.details,
        retry_after_sec=exc.retry_after_sec,
    )
    return JSONResponse(status_code=exc.status, content=envelope)


@app.middleware("http")
async def correlation_middleware(request: Request, call_next):
    correlation_id = normalize_correlation_id(request.headers.get("x-correlation-id"))
    request.state.correlation_id = correlation_id
    set_correlation_id(correlation_id)
    response = await call_next(request)
    response.headers["x-correlation-id"] = correlation_id
    return response


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/ready")
def ready() -> dict[str, str]:
    return {"status": "ready"}
