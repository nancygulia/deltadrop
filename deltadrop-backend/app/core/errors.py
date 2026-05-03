"""
DeltaDrop Standardized Error Handling.

All API errors use the same JSON envelope:
{
    "error": true,
    "message": "Human-readable description",
    "status_code": 400
}
"""
import logging
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

logger = logging.getLogger(__name__)


def make_error(status_code: int, message: str) -> dict:
    """Build a standardized error dict."""
    return {
        "error": True,
        "message": message,
        "status_code": status_code,
    }


def register_error_handlers(app: FastAPI) -> None:
    """
    Register global exception handlers on a FastAPI app instance.
    Call once in create_app().
    """

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        """Convert all HTTPExceptions to standardized format."""
        # If detail is already a dict (e.g. from rate limiter), use it
        if isinstance(exc.detail, dict):
            body = exc.detail
            # Ensure required keys
            body.setdefault("error", True)
            body.setdefault("status_code", exc.status_code)
            body.setdefault("message", f"Error {exc.status_code}")
        else:
            body = make_error(exc.status_code, str(exc.detail))

        # Log server errors
        if exc.status_code >= 500:
            logger.error(f"[HTTP {exc.status_code}] {request.method} {request.url.path}: {exc.detail}")

        return JSONResponse(
            status_code=exc.status_code,
            content=body,
            headers=getattr(exc, "headers", None),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """Convert Pydantic validation errors to standardized format."""
        errors = exc.errors()
        # Build a human-readable summary
        messages = []
        for err in errors[:5]:  # Cap at 5 to avoid huge payloads
            loc = " → ".join(str(l) for l in err.get("loc", []))
            messages.append(f"{loc}: {err.get('msg', 'invalid')}")

        message = "; ".join(messages) if messages else "Request validation failed"

        logger.warning(f"[VALIDATION] {request.method} {request.url.path}: {message}")

        return JSONResponse(
            status_code=422,
            content=make_error(422, message),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        """Catch-all for unhandled exceptions — never leak stack traces."""
        logger.error(
            f"[UNHANDLED] {request.method} {request.url.path}: {type(exc).__name__}: {exc}",
            exc_info=True,
        )
        return JSONResponse(
            status_code=500,
            content=make_error(500, "An internal error occurred. Please try again later."),
        )
