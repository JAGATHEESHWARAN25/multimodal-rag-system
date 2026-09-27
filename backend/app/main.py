import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.models.database import db_manager
from app.api.upload import router as upload_router
from app.api.ocr import router as ocr_router
from app.api.rag import router as rag_router
from app.api.auth import router as auth_router
from app.api.graph import router as graph_router
from app.api.summarize import router as summarize_router
from app.api.system import router as system_router
from app.config import LOG_LEVEL

# Configure logging parameters
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("app.main")

# Initialize FastAPI App
app = FastAPI(
    title="Multimodal Offline RAG Backend",
    description="FastAPI Backend for the Offline Multimodal RAG System (NTRO SIH25231)",
    version="1.0.0"
)

# Configure CORS Middleware to allow requests from the React Frontend development server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # During development, we allow all origins. Can be restricted to local ports if needed.
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Lifecycle startup event
@app.on_event("startup")
async def startup_event():
    """Initializes the database schema and storage directories on server startup."""
    logger.info("Initializing offline database registry...")
    try:
        db_manager._initialize_tables()
        logger.info("Database registry initialized successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize SQLite registry: {str(e)}")
        raise e
        
    from app.core.background_worker import worker
    await worker.start()

@app.on_event("shutdown")
async def shutdown_event():
    from app.core.background_worker import worker
    await worker.stop()

# Include routers
app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
app.include_router(upload_router)
app.include_router(ocr_router)
app.include_router(rag_router)
app.include_router(graph_router)
app.include_router(summarize_router)
app.include_router(system_router)

@app.get("/api/health")
def health_check():
    """Health check endpoint to verify backend operational status."""
    return {
        "status": "healthy",
        "service": "Multimodal Offline RAG System API Gateway"
    }

