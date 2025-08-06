from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from app.config import settings
from app.database import connect_to_mongo, close_mongo_connection
from app.routes import auth, workspaces, chats, documents, phones, webhooks, workflows, reports, monitoring
from app.routes import exports
from app.services.message_queue import message_queue
from app.services.scheduler_service import scheduler_service
from app.services.export_scheduler import export_scheduler
import logging
import uvicorn
from contextlib import asynccontextmanager
import asyncio

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Rate limiting
limiter = Limiter(key_func=get_remote_address)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("Starting WhatsApp Automation Backend...")
    await connect_to_mongo()
    
    # Initialize message queue
    await message_queue.initialize()
    
    # Start message processing in background
    asyncio.create_task(message_queue.process_messages())
    
    # Start scheduler
    await scheduler_service.start()
    
    # Start export scheduler
    await export_scheduler.start()
    
    logger.info("Application started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down application...")
    await export_scheduler.stop()
    await scheduler_service.stop()
    await message_queue.close()
    await close_mongo_connection()
    logger.info("Application shutdown complete")

# Create FastAPI app
app = FastAPI(
    title="WhatsApp Automation Backend",
    description="Backend API for WhatsApp automation system with AI chat capabilities",
    version="1.0.0",
    lifespan=lifespan
)

# Add rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173", "http://127.0.0.1:5173"],  # React dev servers
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Trusted host middleware
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["localhost", "127.0.0.1", "*.localhost"]
)

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )

# Health check endpoint
@app.get("/health")
async def health_check():
    # Check message queue health
    queue_stats = await message_queue.get_queue_stats()
    scheduler_status = scheduler_service.get_job_status()
    export_status = export_scheduler.get_scheduler_status()
    
    return {
        "status": "healthy",
        "service": "whatsapp-automation-backend",
        "version": "1.0.0",
        "message_queue": queue_stats,
        "scheduler": scheduler_status,
        "export_scheduler": export_status,
        "timestamp": datetime.utcnow().isoformat()
    }

# Include routers
app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
app.include_router(workspaces.router, prefix="/workspaces", tags=["Workspaces"])
app.include_router(chats.router, prefix="/chats", tags=["Chats"])
app.include_router(documents.router, prefix="/documents", tags=["Documents"])
app.include_router(phones.router, prefix="/phones", tags=["Phone Numbers"])
app.include_router(webhooks.router, prefix="/webhooks", tags=["Webhooks"])
app.include_router(workflows.router, prefix="/workflows", tags=["Workflows"])
app.include_router(reports.router, prefix="/reports", tags=["Reports"])
app.include_router(monitoring.router, prefix="/monitoring", tags=["Monitoring"])
app.include_router(exports.router, prefix="/exports", tags=["Excel Exports"])

# Root endpoint
@app.get("/")
async def root():
    return {
        "message": "WhatsApp Automation Backend API",
        "version": "1.0.0",
        "docs_url": "/docs",
        "redoc_url": "/redoc"
    }

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )