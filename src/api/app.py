# from pydantic import BaseModel
# import pandas as pd
import uvicorn
from fastapi import FastAPI

# from src.models.predict import predict
from src.api.routes import (
    data_ingestion_endpoint,
    health_check_endpoint,
    predictions_endpoint,
)

# Create FastAPI app
app = FastAPI(
    title="Air Pollution Prediction API",
    description="API for predicting air pollution levels",
    version="1.0.0",
)

# Include routers
app.include_router(health_check_endpoint.router, prefix="/api/v1", tags=["health"])
app.include_router(predictions_endpoint.router, prefix="/api/v1", tags=["predictions"])
app.include_router(
    data_ingestion_endpoint.router, prefix="/api/v1", tags=["data_ingestion"]
)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
    # app.run( debug=True,  host='0.0.0.0', port=9696)
