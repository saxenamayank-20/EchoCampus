from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from backend.app.services.errors import (AuthenticationError, ConflictError, DomainError,
                                         InvalidInputError, InvalidTransitionError, NotFoundError,
                                         NotVerifiedError, PermissionDeniedError)

# domain error -> (http status, short code the frontend can check)
ERROR_MAP: dict[type[DomainError], tuple[int, str]] = {
    AuthenticationError: (401, "unauthorized"),
    NotVerifiedError: (403, "not_verified"),
    PermissionDeniedError: (403, "forbidden"),
    NotFoundError: (404, "not_found"),
    ConflictError: (409, "conflict"),
    InvalidTransitionError: (409, "invalid_transition"),
    InvalidInputError: (422, "invalid_input"),
}

HTTP_CODES = {400: "bad_request", 401: "unauthorized", 403: "forbidden", 404: "not_found",
              405: "method_not_allowed", 409: "conflict", 413: "too_large", 422: "invalid_input"}


def error_body(code: str, message: str, details=None) -> dict:
    """every error looks the same: {"error": {"code": ..., "message": ...}}"""
    body = {"error": {"code": code, "message": message}}
    if details is not None:
        body["error"]["details"] = details
    return body


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def domain_error(_: Request, exc: DomainError):
        status, code = ERROR_MAP.get(type(exc), (400, "bad_request"))
        return JSONResponse(error_body(code, str(exc)), status_code=status)

    @app.exception_handler(StarletteHTTPException)
    async def http_error(_: Request, exc: StarletteHTTPException):
        code = HTTP_CODES.get(exc.status_code, "error")
        return JSONResponse(error_body(code, str(exc.detail)), status_code=exc.status_code,
                            headers=getattr(exc, "headers", None))

    @app.exception_handler(RequestValidationError)
    async def validation_error(_: Request, exc: RequestValidationError):
        errors = exc.errors()
        first = errors[0] if errors else {}
        field = ".".join(str(p) for p in first.get("loc", [])[1:]) or "request"
        message = f"{field}: {first.get('msg', 'invalid value')}"
        return JSONResponse(error_body("validation_error", message, jsonable_encoder(errors)),
                            status_code=422)
