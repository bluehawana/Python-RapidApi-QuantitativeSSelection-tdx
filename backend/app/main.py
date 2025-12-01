"""FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.error_handlers import register_exception_handlers
from app.api import health, formulas, screening, data

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    description="Quantitative screening system for convertible bonds",
    version="1.0.0",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, tags=["Health"])
app.include_router(formulas.router, prefix="/api/formulas", tags=["Formulas"])
app.include_router(
    screening.router, prefix="/api/screening", tags=["Screening"])
app.include_router(data.router, prefix="/api/data", tags=["Data"])


# Register exception handlers
register_exception_handlers(app)


@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "Convertible Bond Selector API", "version": "1.0.0"}
