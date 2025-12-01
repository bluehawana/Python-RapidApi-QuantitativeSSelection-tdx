"""Data service endpoints."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/bonds")
async def get_bonds():
    """Get all convertible bonds."""
    return {"bonds": []}


@router.get("/bonds/{code}")
async def get_bond(code: str):
    """Get bond details by code."""
    return {"message": "Not implemented yet"}


@router.get("/refresh")
async def refresh_data():
    """Force data refresh from AkShare."""
    return {"message": "Data refresh triggered"}
