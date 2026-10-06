from typing import Generator, Optional, TypeVar, Callable, Any
from functools import lru_cache
from fastapi import Depends, HTTPException, Header, Request
from sqlalchemy.orm import Session
from jose import jwt, JWTError

from app.config import get_settings, Settings
from app.database import get_db as get_db_session
from app.auth.service import decode_access_token
from app.auth.models import User
from app.core.service_registry import (
    get_service_registry, 
    get_dependency_container, 
    ServiceRegistry, 
    DependencyContainer,
    initialize_core_services
)

T = TypeVar('T')

settings = get_settings()

# Initialize core services on module load
initialize_core_services()


def get_settings_dependency() -> Settings:
    """FastAPI dependency for application settings."""
    return settings


def get_database() -> Generator[Session, None, None]:
    """FastAPI dependency for database session."""
    db = next(get_db_session())
    try:
        yield db
    finally:
        db.close()


async def get_current_user(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_database)
) -> User:
    """FastAPI dependency for current authenticated user."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    token = authorization[7:]
    token_data = decode_access_token(token)
    if not token_data or not token_data.user_id:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    from app.auth.service import get_user_by_id
    user = get_user_by_id(db, token_data.user_id)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """FastAPI dependency for current active user."""
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


async def get_current_superuser(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """FastAPI dependency for current superuser."""
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return current_user


def get_service_registry_dependency() -> ServiceRegistry:
    """FastAPI dependency for service registry."""
    return get_service_registry()


def get_dependency_container_dependency() -> DependencyContainer:
    """FastAPI dependency for dependency container."""
    return get_dependency_container()


class ServiceAccessor:
    """Helper class to access services from the registry."""
    
    def __init__(self, registry: ServiceRegistry = Depends(get_service_registry_dependency)):
        self.registry = registry
    
    def get(self, name: str):
        return self.registry.get(name)
    
    def get_singleton(self, name: str):
        return self.registry.get_singleton(name)
    
    def has(self, name: str) -> bool:
        return self.registry.has(name)


def get_service_accessor() -> ServiceAccessor:
    """FastAPI dependency for service accessor."""
    return ServiceAccessor()


class CrossServiceClient:
    """
    Client for cross-service communication within the application.
    """
    
    def __init__(self, registry: ServiceRegistry = Depends(get_service_registry_dependency)):
        self.registry = registry
    
    def call_service(self, service_name: str, method: str, *args, **kwargs):
        """Call a method on a registered service."""
        service = self.registry.get(service_name)
        if not hasattr(service, method):
            raise AttributeError(f"Service '{service_name}' has no method '{method}'")
        return getattr(service, method)(*args, **kwargs)
    
    async def call_service_async(self, service_name: str, method: str, *args, **kwargs):
        """Call an async method on a registered service."""
        service = self.registry.get(service_name)
        if not hasattr(service, method):
            raise AttributeError(f"Service '{service_name}' has no method '{method}'")
        return await getattr(service, method)(*args, **kwargs)


def get_cross_service_client(registry: ServiceRegistry = None) -> CrossServiceClient:
    """FastAPI dependency for cross-service client."""
    if registry is None:
        registry = get_service_registry()
    return CrossServiceClient(registry)


@lru_cache()
def get_service_registry_instance() -> ServiceRegistry:
    """Cached service registry instance for startup."""
    return ServiceRegistry()


@lru_cache()
def get_dependency_container_instance() -> DependencyContainer:
    """Cached dependency container instance for startup."""
    return DependencyContainer()


class ServiceProvider:
    """
    Provider class for accessing services with type hints.
    """
    
    def __init__(self, registry: ServiceRegistry):
        self.registry = registry
    
    def auth(self):
        """Get auth service."""
        from app.auth.service import AuthService
        return self.registry.get("auth")
    
    def settlement(self):
        """Get settlement service."""
        from app.settlement.service import SettlementService
        return self.registry.get("settlement")
    
    def authorization(self):
        """Get authorization service."""
        from app.authorization.service import AuthorizationService
        return self.registry.get("authorization")
    
    def storage(self):
        """Get storage."""
        from app.storage import Storage
        return self.registry.get("storage")


def get_service_provider(registry: ServiceRegistry = Depends(get_service_registry_dependency)) -> ServiceProvider:
    """FastAPI dependency for service provider."""
    return ServiceProvider(registry)


# Type-specific dependencies for easier use in routes
def get_auth_service():
    """Get auth service directly."""
    registry = get_service_registry()
    return registry.get("auth")


def get_settlement_service():
    """Get settlement service directly."""
    registry = get_service_registry()
    return registry.get("settlement")


def get_authorization_service():
    """Get authorization service directly."""
    registry = get_service_registry()
    return registry.get("authorization")


def get_storage():
    """Get storage directly."""
    registry = get_service_registry()
    return registry.get("storage")