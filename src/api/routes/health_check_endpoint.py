from datetime import datetime

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "air-pollution-prediction-api",
    }


@router.get("/ready")
async def readiness_check():
    """Get API version"""
    return {"status": "ready", "timestamp": datetime.utcnow().isoformat()}
