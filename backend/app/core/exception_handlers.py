from __future__ import annotations

import json
import logging
import traceback
from typing import cast

from fastapi import FastAPI, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.status import HTTP_422_UNPROCESSABLE_CONTENT
from starlette.types import ExceptionHandler

from app.core.errors import ApiError, error_envelope, message_for_code
from app.core.request_context import get_client_event_id, get_correlation_id
from app.core.request_diagnostics import safe_request_body, sanitize_request_body

logger = logging.getLogger("app.access")
app_logger = logging.getLogger("app.main")


def _error_details(value: object) -> list[dict] | dict:
    if isinstance(value, dict):
        return value
    if isinstance(value, list):
        return [item if isinstance(item, dict) else {"detail": item} for item in value]
    return [{"detail": value}]


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    body = exc.body
    if isinstance(body, dict):
        body = sanitize_request_body(body)

    safe_errors = sanitize_request_body(jsonable_encoder(exc.errors()))
    details = _error_details(safe_errors)
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
        details=details,
        correlation_id=get_correlation_id() or getattr(request.state, "correlation_id", None),
        client_event_id=get_client_event_id() or getattr(request.state, "client_event_id", None),
    )
    return JSONResponse(status_code=HTTP_422_UNPROCESSABLE_CONTENT, content=envelope)


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    safe_body = await safe_request_body(request)
    details: list[dict] | dict
    if isinstance(exc.detail, str):
        code = exc.detail
        details = []
    elif isinstance(exc.detail, list):
        code = "validation_error"
        details = _error_details(exc.detail)
    elif isinstance(exc.detail, dict):
        code = str(exc.detail.get("code") or "request_failed")
        raw_details = exc.detail.get("details", [])
        if isinstance(raw_details, (list, dict)):
            details = _error_details(raw_details)
        else:
            details = _error_details(raw_details)
    else:
        code = "request_failed"
        details = []
    logger.warning(
        json.dumps(
            {
                "event": "http_exception",
                "correlation_id": get_correlation_id() or getattr(request.state, "correlation_id", "") or "-",
                "client_event_id": get_client_event_id(),
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
    message = (
        str(exc.detail.get("message"))
        if isinstance(exc.detail, dict) and exc.detail.get("message")
        else message_for_code(code, fallback="Request failed.")
    )
    envelope = error_envelope(
        status=exc.status_code,
        code=code,
        message=message,
        details=details,
        correlation_id=get_correlation_id() or getattr(request.state, "correlation_id", None),
        client_event_id=get_client_event_id() or getattr(request.state, "client_event_id", None),
    )
    return JSONResponse(status_code=exc.status_code, content=envelope)


async def api_error_handler(request: Request, exc: ApiError) -> JSONResponse:
    envelope = error_envelope(
        status=exc.status,
        code=exc.code,
        message=exc.message,
        details=exc.details,
        retry_after_sec=exc.retry_after_sec,
        correlation_id=get_correlation_id() or getattr(request.state, "correlation_id", None),
        client_event_id=get_client_event_id() or getattr(request.state, "client_event_id", None),
    )
    return JSONResponse(status_code=exc.status, content=envelope)


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    safe_body = await safe_request_body(request)
    app_logger.error(
        json.dumps(
            {
                "event": "unhandled_exception",
                "correlation_id": get_correlation_id() or getattr(request.state, "correlation_id", "") or "-",
                "client_event_id": get_client_event_id(),
                "path": request.url.path,
                "method": request.method,
                "query": dict(request.query_params),
                "body": safe_body,
                "exception_type": type(exc).__name__,
                "error": str(exc)[:1000],
                "traceback": traceback.format_exc(limit=25),
            },
            ensure_ascii=False,
        )
    )
    envelope = error_envelope(
        status=500,
        code="internal_server_error",
        message="Internal server error.",
        details=[],
        correlation_id=get_correlation_id() or getattr(request.state, "correlation_id", None),
        client_event_id=get_client_event_id() or getattr(request.state, "client_event_id", None),
    )
    response = JSONResponse(status_code=500, content=envelope)
    correlation_id = get_correlation_id() or getattr(request.state, "correlation_id", "")
    if correlation_id:
        response.headers["x-correlation-id"] = correlation_id
    client_event_id = get_client_event_id() or getattr(request.state, "client_event_id", None)
    if client_event_id:
        response.headers["x-client-event-id"] = client_event_id
    return response


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(RequestValidationError, cast(ExceptionHandler, validation_exception_handler))
    app.add_exception_handler(HTTPException, cast(ExceptionHandler, http_exception_handler))
    app.add_exception_handler(ApiError, cast(ExceptionHandler, api_error_handler))
    app.add_exception_handler(Exception, unhandled_exception_handler)
