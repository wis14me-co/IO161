from typing import Any, Dict, Optional
from fastapi import HTTPException, status


class AppException(Exception):
    """Base application exception."""
    
    def __init__(
        self,
        message: str,
        code: str = "internal_error",
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)


class ValidationException(AppException):
    """Validation error exception."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="validation_error",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details=details
        )


class NotFoundException(AppException):
    """Resource not found exception."""
    
    def __init__(self, message: str, resource: str = "resource", resource_id: Any = None):
        details = {"resource": resource}
        if resource_id:
            details["resource_id"] = str(resource_id)
        super().__init__(
            message=message,
            code="not_found",
            status_code=status.HTTP_404_NOT_FOUND,
            details=details
        )


class UnauthorizedException(AppException):
    """Unauthorized access exception."""
    
    def __init__(self, message: str = "Unauthorized"):
        super().__init__(
            message=message,
            code="unauthorized",
            status_code=status.HTTP_401_UNAUTHORIZED
        )


class ForbiddenException(AppException):
    """Forbidden access exception."""
    
    def __init__(self, message: str = "Forbidden"):
        super().__init__(
            message=message,
            code="forbidden",
            status_code=status.HTTP_403_FORBIDDEN
        )


class ConflictException(AppException):
    """Resource conflict exception."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="conflict",
            status_code=status.HTTP_409_CONFLICT,
            details=details
        )


class RateLimitException(AppException):
    """Rate limit exceeded exception."""
    
    def __init__(self, message: str = "Rate limit exceeded", retry_after: int = 60):
        super().__init__(
            message=message,
            code="rate_limit_exceeded",
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            details={"retry_after": retry_after}
        )


class ServiceUnavailableException(AppException):
    """Service unavailable exception."""
    
    def __init__(self, message: str = "Service temporarily unavailable"):
        super().__init__(
            message=message,
            code="service_unavailable",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE
        )


class InternalServerException(AppException):
    """Internal server error exception."""
    
    def __init__(self, message: str = "Internal server error", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="internal_error",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=details
        )


class BadRequestException(AppException):
    """Bad request exception."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="bad_request",
            status_code=status.HTTP_400_BAD_REQUEST,
            details=details
        )


class PayloadTooLargeException(AppException):
    """Request payload too large exception."""
    
    def __init__(self, message: str = "Request payload too large", max_size: int = 0):
        details = {}
        if max_size:
            details["max_size"] = max_size
        super().__init__(
            message=message,
            code="payload_too_large",
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            details=details
        )


class UnprocessableEntityException(AppException):
    """Unprocessable entity exception (semantic errors)."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="unprocessable_entity",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details=details
        )


class DependencyException(AppException):
    """External dependency failure exception."""
    
    def __init__(self, message: str = "External service unavailable", service: str = "unknown"):
        super().__init__(
            message=message,
            code="dependency_error",
            status_code=status.HTTP_502_BAD_GATEWAY,
            details={"service": service}
        )


def app_exception_to_http(app_exc: AppException) -> HTTPException:
    """Convert AppException to HTTPException."""
    return HTTPException(
        status_code=app_exc.status_code,
        detail={
            "code": app_exc.code,
            "message": app_exc.message,
            "details": app_exc.details
        }
    )


def create_error_response(
    code: str,
    message: str,
    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
    details: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Create a standardized error response dictionary."""
    return {
        "code": code,
        "message": message,
        "details": details or {}
    }


# Exception handler functions for FastAPI
def handle_app_exception(request, exc: AppException):
    """FastAPI exception handler for AppException."""
    from starlette.responses import JSONResponse
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message
            }
        }
    )


def handle_http_exception(request, exc: HTTPException):
    """FastAPI exception handler for HTTPException - format to match spec."""
    from starlette.responses import JSONResponse
    # If detail is already in the right format, use it
    if isinstance(exc.detail, dict) and "error" in exc.detail:
        return JSONResponse(status_code=exc.status_code, content=exc.detail)
    # Otherwise wrap in error format
    code = exc.detail.get("code", "unknown") if isinstance(exc.detail, dict) else "unknown"
    message = exc.detail.get("message", str(exc.detail)) if isinstance(exc.detail, dict) else str(exc.detail)
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": code,
                "message": message
            }
        }
    )


def handle_validation_exception(request, exc):
    """FastAPI exception handler for validation errors."""
    from starlette.responses import JSONResponse
    from fastapi.exceptions import RequestValidationError
    if isinstance(exc, RequestValidationError):
        # Extract first error for simple message
        first_error = exc.errors()[0] if exc.errors() else {}
        field = ".".join(str(x) for x in first_error.get("loc", []))
        msg = first_error.get("msg", "Validation failed")
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": {
                    "code": "validation_failed",
                    "message": f"{field}: {msg}" if field else msg
                }
            }
        )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "internal_error",
                "message": "Internal server error"
            }
        }
    )