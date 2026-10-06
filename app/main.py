from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.config import get_settings
from app.database import init_db
from app.auth.routes import router as auth_router
from app.payments.routes import router as payments_router
from app.settlement.routes import router as settlement_router
from app.authorization.routes import router as authorization_router
from app.websocket.routes import router as websocket_router
from app.core import setup_middleware
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

# Setup WebSocket manager in storage for notifications
storage.set_websocket_manager(manager)

# Setup all middleware (order matters!)
setup_middleware(app, settings)

app.include_router(auth_router, prefix=settings.API_V1_PREFIX + "/auth", tags=["auth"])
app.include_router(payments_router, prefix=settings.API_V1_PREFIX + "/payments", tags=["payments"])
app.include_router(settlement_router, prefix=settings.API_V1_PREFIX + "/settlements", tags=["settlements"])
app.include_router(authorization_router, prefix=settings.API_V1_PREFIX + "/authorizations", tags=["authorizations"])
app.include_router(websocket_router)


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/")
def root():
    return {"message": "Welcome to Pocketful API"}