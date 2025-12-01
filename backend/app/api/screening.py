"""Screening execution endpoints."""

from fastapi import APIRouter

router = APIRouter()


@router.post("/execute")
async def execute_screening():
    """Execute a screening formula."""
    return {"message": "Not implemented yet"}


@router.get("/results")
async def get_results():
    """Get screening results."""
    return {"results": []}


@router.post("/results")
async def save_results():
    """Save screening results."""
    return {"message": "Not implemented yet"}


@router.get("/history")
async def get_history():
    """Get screening history."""
    return {"history": []}


@router.post("/compare")
async def compare_results():
    """Compare two result sets."""
    return {"message": "Not implemented yet"}


@router.post("/export")
async def export_results():
    """Export results to CSV/Excel."""
    return {"message": "Not implemented yet"}
