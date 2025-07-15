import logging
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, HTTPException

from src.config import USE_S3
from src.data.data_ingestion import DataIngestion

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/data/collect/training")
async def collect_training_data(
    background_tasks: BackgroundTasks,
    week_number: int = 8,
    chunk_size_hours: int = 24 * 7,  # Default to 1 week
    force_refresh: bool = False,
):
    """Collect and prepare training data"""
    try:

        def run_training_data_collection():
            ingestion = DataIngestion(use_s3=USE_S3)

            ingestion.fetch_pollution_data(
                data_type="training",
                chunk_size_hours=chunk_size_hours,
                week_number=week_number,
            )

            # logger.info(f"Training data collection completed: {len(df)} records")

        # Run in background
        background_tasks.add_task(run_training_data_collection)

        return {
            "status": "started",
            "message": f"Training data collection started for { week_number*chunk_size_hours} hours",
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"Training data collection failed: {e}")
        raise HTTPException(
            status_code=500, detail=f"Training data collection failed: {str(e)}"
        )


@router.get("/data/collect/predicting")
async def collect_testing_data(
    background_tasks: BackgroundTasks,
    week_number: int = 1,
    chunk_size_hours: int = 48,  # Default to 1 week
    force_refresh: bool = False,
):
    """Collect and prepare training data"""
    try:

        def run_training_data_collection():
            ingestion = DataIngestion(use_s3=USE_S3)

            ingestion.fetch_pollution_data(
                data_type="training",
                chunk_size_hours=chunk_size_hours,
                week_number=week_number,
            )

            # logger.info(f"Training data collection completed: {len(df)} records")

        # Run in background
        background_tasks.add_task(run_training_data_collection)

        return {
            "status": "started",
            "message": f"Testing data collection started for { week_number*chunk_size_hours} hours",
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"Training data collection failed: {e}")
        raise HTTPException(
            status_code=500, detail=f"Training data collection failed: {str(e)}"
        )


@router.get("/data/status")
async def get_data_status():
    """Check data availability and freshness"""
    try:
        import os

        from src.config import INTERIM_DATA_DIR

        training_file = os.path.join(
            INTERIM_DATA_DIR, "air_pollution_data_total.parquet"
        )
        latest_file = os.path.join(INTERIM_DATA_DIR, "latest_pollution_data.parquet")

        status = {
            "training_data": {
                "exists": os.path.exists(training_file),
                "last_modified": None,
                "age_hours": None,
            },
            "latest_data": {
                "exists": os.path.exists(latest_file),
                "last_modified": None,
                "age_hours": None,
            },
        }

        if status["training_data"]["exists"]:
            mtime = datetime.fromtimestamp(os.path.getmtime(training_file))
            status["training_data"]["last_modified"] = mtime.isoformat()
            status["training_data"]["age_hours"] = (
                datetime.now() - mtime
            ).total_seconds() / 3600

        if status["latest_data"]["exists"]:
            mtime = datetime.fromtimestamp(os.path.getmtime(latest_file))
            status["latest_data"]["last_modified"] = mtime.isoformat()
            status["latest_data"]["age_hours"] = (
                datetime.now() - mtime
            ).total_seconds() / 3600

        return status

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get data status: {str(e)}"
        )
