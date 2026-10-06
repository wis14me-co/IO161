from typing import TypeVar, Generic, Dict, Any, Optional, Callable, Type, List
from abc import ABC, abstractmethod
import logging
from contextlib import contextmanager

logger = logging.getLogger(__name__)

T = TypeVar('T')


class ServiceNotFoundError(Exception):
    pass


class ServiceRegistry:
    """
    Centralized service registry for dependency injection and service discovery.
    """
    
    def __init__(self):
        self._services: Dict[str, Any] = {}
        self._factories: Dict[str, Callable[[], Any]] = {}
        self._singletons: Dict[str, Any] = {}
        self._initialized = False
    
    def register(self, name: str, service: Any) -> None:
        """Register a service instance."""
        if name in self._services:
            logger.warning(f"Service '{name}' already registered, overwriting")
        self._services[name] = service
        logger.debug(f"Registered service: {name}")
    
    def register_factory(self, name: str, factory: Callable[[], Any]) -> None:
        """Register a factory function for lazy initialization."""
        self._factories[name] = factory
        logger.debug(f"Registered factory: {name}")
    
    def register_singleton(self, name: str, factory: Callable[[], Any]) -> None:
        """Register a singleton factory - created once on first access."""
        self._factories[name] = factory
        logger.debug(f"Registered singleton factory: {name}")
    
    def get(self, name: str) -> Any:
        """Get a service by name, initializing singletons on first access."""
        if name in self._singletons:
            return self._singletons[name]
        
        if name in self._services:
            return self._services[name]
        
        if name in self._factories:
            service = self._factories[name]()
            if name in self._factories:  # Check if it was a singleton factory
                # If the factory was registered via register_singleton, we cache it
                pass
            self._services[name] = service
            return service
        
        raise ServiceNotFoundError(f"Service '{name}' not found")
    
    def get_singleton(self, name: str) -> Any:
        """Get a singleton service, creating it on first access."""
        if name in self._singletons:
            return self._singletons[name]
        
        if name in self._factories:
            service = self._factories[name]()
            self._singletons[name] = service
            return service
        
        raise ServiceNotFoundError(f"Singleton service '{name}' not found")
    
    def has(self, name: str) -> bool:
        """Check if a service is registered."""
        return name in self._services or name in self._factories
    
    def unregister(self, name: str) -> bool:
        """Unregister a service."""
        if name in self._services:
            del self._services[name]
            return True
        if name in self._factories:
            del self._factories[name]
            return True
        return False
    
    def clear(self) -> None:
        """Clear all services."""
        self._services.clear()
        self._factories.clear()
        self._singletons.clear()
    
    def initialize_all(self) -> None:
        """Initialize all registered factories."""
        for name, factory in self._factories.items():
            if name not in self._services and name not in self._singletons:
                try:
                    service = factory()
                    self._services[name] = service
                    logger.debug(f"Initialized service: {name}")
                except Exception as e:
                    logger.error(f"Failed to initialize service '{name}': {e}")
        self._initialized = True

    @contextmanager
    def temporary_service(self, name: str, service: Any):
        """Temporarily override a service for testing."""
        old_service = self._services.get(name)
        old_factory = self._factories.get(name)
        old_singleton = self._singletons.get(name)
        
        self._services[name] = service
        if name in self._factories:
            del self._factories[name]
        if name in self._singletons:
            del self._singletons[name]
        
        try:
            yield service
        finally:
            # Restore
            if old_service is not None:
                self._services[name] = old_service
            elif name in self._services:
                del self._services[name]
            
            if old_factory is not None:
                self._factories[name] = old_factory
            
            if old_singleton is not None:
                self._singletons[name] = old_singleton
            elif name in self._singletons:
                del self._singletons[name]

    def get_all(self) -> Dict[str, Any]:
        """Get all registered services."""
        return {**self._services, **{k: v for k, v in self._factories.items() if k not in self._services}}

    def list_services(self) -> List[str]:
        """List all registered service names."""
        return list(set(list(self._services.keys()) + list(self._factories.keys()) + list(self._singletons.keys())))


class DependencyContainer:
    """
    Dependency injection container with type-based resolution.
    """
    
    def __init__(self):
        self._bindings: Dict[Type, Any] = {}
        self._factories: Dict[Type, Callable[[], Any]] = {}
        self._singletons: Dict[Type, Any] = {}
    
    def bind(self, interface: Type[T], implementation: T) -> None:
        """Bind an interface to a concrete implementation."""
        self._bindings[interface] = implementation
    
    def bind_factory(self, interface: Type[T], factory: Callable[[], T]) -> None:
        """Bind an interface to a factory function."""
        self._factories[interface] = factory
    
    def bind_singleton(self, interface: Type[T], factory: Callable[[], T]) -> None:
        """Bind an interface to a singleton factory."""
        self._factories[interface] = factory
    
    def resolve(self, interface: Type[T]) -> T:
        """Resolve a dependency by type."""
        if interface in self._singletons:
            return self._singletons[interface]
        
        if interface in self._bindings:
            return self._bindings[interface]
        
        if interface in self._factories:
            instance = self._factories[interface]()
            # Check if this was a singleton binding
            # (We can't easily distinguish, so we don't auto-cache)
            return instance
        
        raise ServiceNotFoundError(f"No binding for type '{interface.__name__}'")
    
    def resolve_singleton(self, interface: Type[T]) -> T:
        """Resolve a singleton dependency."""
        if interface in self._singletons:
            return self._singletons[interface]
        
        if interface in self._factories:
            instance = self._factories[interface]()
            self._singletons[interface] = instance
            return instance
        
        if interface in self._bindings:
            return self._bindings[interface]
        
        raise ServiceNotFoundError(f"No binding for type '{interface.__name__}'")

    def resolve_all(self, interface: Type[T]) -> List[T]:
        """Resolve all implementations for an interface (if multiple registered)."""
        results = []
        if interface in self._bindings:
            results.append(self._bindings[interface])
        if interface in self._factories:
            results.append(self._factories[interface]())
        if interface in self._singletons:
            results.append(self._singletons[interface])
        return results

    def unbind(self, interface: Type[T]) -> bool:
        """Remove a binding."""
        removed = False
        if interface in self._bindings:
            del self._bindings[interface]
            removed = True
        if interface in self._factories:
            del self._factories[interface]
            removed = True
        if interface in self._singletons:
            del self._singletons[interface]
            removed = True
        return removed

    def clear(self) -> None:
        """Clear all bindings."""
        self._bindings.clear()
        self._factories.clear()
        self._singletons.clear()


# Global instances
service_registry = ServiceRegistry()
dependency_container = DependencyContainer()


def get_service_registry() -> ServiceRegistry:
    """Get the global service registry."""
    return service_registry


def get_dependency_container() -> DependencyContainer:
    """Get the global dependency container."""
    return dependency_container


def initialize_core_services() -> None:
    """Initialize and register all core application services."""
    from app.auth.service import auth_service as auth_service_instance
    from app.settlement.service import settlement_service as settlement_service_instance
    from app.authorization.service import authorization_service as authorization_service_instance
    from app.storage import storage
    
    # Register services
    service_registry.register("auth", auth_service_instance)
    service_registry.register("settlement", settlement_service_instance)
    service_registry.register("authorization", authorization_service_instance)
    service_registry.register("storage", storage)
    
    # Register singletons for database and config
    from app.config import get_settings
    from app.database import get_db as get_db_session
    
    service_registry.register_singleton("settings", get_settings)
    service_registry.register_factory("db_session", lambda: next(get_db_session()))
    
    # Initialize all factories
    service_registry.initialize_all()
    
    logger.info("Core services initialized and registered")