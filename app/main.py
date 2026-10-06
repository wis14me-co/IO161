from fastapi import FastAPI
from contextlib import asynccontextmanager
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError
from fastapi import HTTPException
from app.config import get_settings
from app.database import init_db
from app.auth.routes import router as auth_router
from app.payments.routes import router as payments_router
from app.settlement.routes import router as settlement_router
from app.authorization.routes import router as authorization_router
from app.requests.routes import router as requests_router
from app.split.routes import router as split_router
from app.test.routes import router as test_router
from app.websocket.routes import router as websocket_router
from app.frontend.routes import router as frontend_router
from app.core import setup_middleware
from app.core.exceptions import handle_app_exception, handle_validation_exception, handle_http_exception, AppException
from app.storage import storage
from app.websocket.manager import manager

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    init_db()
    yield
    # Shutdown (if needed)


app = FastAPI(
    title=settings.APP_NAME,
    debug=settings.DEBUG,
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
    lifespan=lifespan
)

# Exception handlers
app.add_exception_handler(AppException, handle_app_exception)
app.add_exception_handler(RequestValidationError, handle_validation_exception)
app.add_exception_handler(HTTPException, handle_http_exception)

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Setup WebSocket manager in storage for notifications
storage.set_websocket_manager(manager)

# Setup all middleware (order matters!)
setup_middleware(app, settings)

app.include_router(auth_router, prefix=settings.API_V1_PREFIX + "/auth", tags=["auth"])
app.include_router(payments_router, prefix=settings.API_V1_PREFIX + "/payments", tags=["payments"])
app.include_router(settlement_router, prefix=settings.API_V1_PREFIX + "/settlements", tags=["settlements"])
app.include_router(authorization_router, prefix=settings.API_V1_PREFIX + "/authorizations", tags=["authorizations"])
app.include_router(requests_router, prefix=settings.API_V1_PREFIX + "/requests", tags=["requests"])
app.include_router(split_router, prefix=settings.API_V1_PREFIX + "/splits", tags=["splits"])
app.include_router(test_router, tags=["test"])
app.include_router(websocket_router)
# Frontend routes - mount at root but avoid conflicting with API routes
# The frontend router handles HTML pages, not API endpoints
app.include_router(frontend_router)

# Add /me endpoint at root level as per spec
from app.auth.routes import read_users_me
app.get("/me", tags=["auth"])(read_users_me)


@app.get("/health")
def health_check():
    return {"status": "ok"}