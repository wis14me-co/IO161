from app.config import get_settings, Settings
from app.database import get_db, init_db, Base
from app.core.service_registry import (
    ServiceRegistry,
    DependencyContainer,
    get_service_registry,
    get_dependency_container,
    service_registry,
    dependency_container
)
from app.core.dependencies import (
    get_settings_dependency,
    get_database,
    get_current_user,
    get_current_active_user,
    get_current_superuser,
    get_service_registry_dependency,
    get_dependency_container_dependency,
    get_service_accessor,
    get_cross_service_client,
    ServiceAccessor,
    CrossServiceClient,
)
from app.core.exceptions import (
    AppException,
    ValidationException,
    NotFoundException,
    UnauthorizedException,
    ForbiddenException,
    ConflictException,
    RateLimitException,
    ServiceUnavailableException,
    InternalServerException,
    BadRequestException,
    app_exception_to_http,
)
from app.core.middleware import (
    RequestLoggingMiddleware,
    RateLimitMiddleware,
    SecurityHeadersMiddleware,
    ErrorHandlingMiddleware,
    setup_middleware,
)

__all__ = [
    # Config
    "get_settings",
    "Settings",
    # Database
    "get_db",
    "init_db",
    "Base",
    # Service Registry
    "ServiceRegistry",
    "DependencyContainer",
    "get_service_registry",
    "get_dependency_container",
    "service_registry",
    "dependency_container",
    # Dependencies
    "get_settings_dependency",
    "get_database",
    "get_current_user",
    "get_current_active_user",
    "get_current_superuser",
    "get_service_registry_dependency",
    "get_dependency_container_dependency",
    "get_service_accessor",
    "get_cross_service_client",
    "ServiceAccessor",
    "CrossServiceClient",
    # Exceptions
    "AppException",
    "ValidationException",
    "NotFoundException",
    "UnauthorizedException",
    "ForbiddenException",
    "ConflictException",
    "RateLimitException",
    "ServiceUnavailableException",
    "InternalServerException",
    "BadRequestException",
    "app_exception_to_http",
    # Middleware
    "RequestLoggingMiddleware",
    "RateLimitMiddleware",
    "SecurityHeadersMiddleware",
    "ErrorHandlingMiddleware",
    "setup_middleware",
]