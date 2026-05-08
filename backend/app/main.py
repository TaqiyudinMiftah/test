import time
import uuid
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.database import init_db
from app.logger import get_logger
from app.api.health import router as health_router
from app.api.users import router as users_router
from app.api.jobs import router as jobs_router
from app.api.clips import router as clips_router

# Setup logger
logger = get_logger("main")
api_logger = get_logger("api.access")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing database...")
    try:
        await init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}", exc_info=True)
        raise
    yield
    logger.info("Application shutting down...")

app = FastAPI(
    title="AutoClip AI API",
    description="API untuk sistem AutoClip AI - AI-powered video clipping pipeline",
    version="1.0.0",
    lifespan=lifespan
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Logging Middleware untuk setiap request
@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    request_id = str(uuid.uuid4())[:8]
    start_time = time.time()
    
    # Log request
    client_host = request.client.host if request.client else "unknown"
    api_logger.info(
        f"[{request_id}] REQUEST: {request.method} {request.url.path} "
        f"- Client: {client_host} - User-Agent: {request.headers.get('user-agent', 'unknown')}"
    )
    
    try:
        response = await call_next(request)
        process_time = time.time() - start_time
        
        # Log response
        api_logger.info(
            f"[{request_id}] RESPONSE: {request.method} {request.url.path} "
            f"- Status: {response.status_code} - Time: {process_time:.3f}s"
        )
        
        # Add custom headers
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time"] = str(process_time)
        
        return response
        
    except Exception as e:
        process_time = time.time() - start_time
        api_logger.error(
            f"[{request_id}] ERROR: {request.method} {request.url.path} "
            f"- Time: {process_time:.3f}s - Exception: {str(e)}",
            exc_info=True
        )
        raise

# Include routers
app.include_router(health_router)
app.include_router(users_router)
app.include_router(jobs_router)
app.include_router(clips_router)

@app.get("/")
async def root():
    logger.info("Root endpoint accessed")
    return {
        "message": "Selamat datang di AutoClip AI API",
        "version": "1.0.0",
        "docs": "/docs"
    }

# Exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(
        f"Unhandled exception in {request.method} {request.url.path}: {str(exc)}",
        exc_info=True
    )
    from fastapi.responses import JSONResponse
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "error": str(exc)}
    )
