from datetime import datetime
from typing import Any, Dict

from pydantic import BaseModel


class PredictionResponse(BaseModel):
    prediction_timestamp: str
    predictions: Dict[str, Dict[str, Dict[str, Any]]]
    historical_data: Dict[
        str, list
    ] = {}  # Add historical_data field with default empty dict

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class HealthResponse(BaseModel):
    status: str
    timestamp: str
    service: str


class ModelInfoResponse(BaseModel):
    model_type: str
    training_hours: int
    prediction_steps: int
    features: list
