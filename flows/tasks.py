"""
Prefect flows for air pollution prediction MLOps pipeline
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict

import pandas as pd
from prefect import flow, task
from prefect.task_runners import SequentialTaskRunner

from src.config import USE_S3
from src.data.data_ingestion import DataIngestion
from src.data.data_loader import DataLoader
from src.models.pollution_predictor import PollutionPredictor

logger = logging.getLogger(__name__)


@task(name="collect_training_data", retries=2)
def collect_training_data_task(
    chunk_size_hours: int = 168,  # 1 week
    week_number: int = 2,
    force_refresh: bool = True,
) -> Dict[str, Any]:
    """Task to collect training data"""
    try:
        logger.info(
            f"Starting training data collection: week={week_number}, chunk_size={chunk_size_hours}h"
        )

        data_ingestion = DataIngestion(use_s3=USE_S3)
        result = data_ingestion.fetch_pollution_data(
            data_type="training",
            chunk_size_hours=chunk_size_hours,
            week_number=week_number,
        )

        # Load and validate the data
        data_loader = DataLoader(use_s3=USE_S3)
        df = data_loader.load_train_dataset()

        return {
            "status": "success",
            "records_collected": len(df) if df is not None else 0,
            "data_shape": df.shape if df is not None else None,
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"Training data collection failed: {e}")
        raise e


@task(name="collect_prediction_data", retries=2)
def collect_prediction_data_task(
    chunk_size_hours: int = 48, week_number: int = 1
) -> Dict[str, Any]:
    """Task to collect prediction data"""
    try:
        logger.info(
            f"Starting prediction data collection: week={week_number}, chunk_size={chunk_size_hours}h"
        )

        data_ingestion = DataIngestion(use_s3=USE_S3)
        result = data_ingestion.fetch_pollution_data(
            data_type="predicting",
            chunk_size_hours=chunk_size_hours,
            week_number=week_number,
        )

        # Load and validate the data
        data_loader = DataLoader(use_s3=USE_S3)
        df = data_loader.load_predicting_dataset()

        return {
            "status": "success",
            "records_collected": len(df) if df is not None else 0,
            "data_shape": df.shape if df is not None else None,
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"Prediction data collection failed: {e}")
        raise e


@task(name="train_model", retries=1)
def train_model_task() -> Dict[str, Any]:
    """Task to train the pollution prediction model"""
    try:
        logger.info("Starting model training")

        # Load training data
        data_loader = DataLoader(use_s3=USE_S3)
        df = data_loader.load_train_dataset()

        if df is None or df.empty:
            raise ValueError("No training data available")

        # Initialize predictor and train
        predictor = PollutionPredictor()
        metrics = predictor.train(df)

        logger.info(f"Model training completed with metrics: {metrics}")
        return metrics

    except Exception as e:
        logger.error(f"Model training failed: {e}")
        raise e


@task(name="validate_model", retries=1)
def validate_model_task() -> Dict[str, Any]:
    """Task to validate the trained model"""
    try:
        logger.info("Starting model validation")

        predictor = PollutionPredictor()

        # Try to load the model
        model_loaded = predictor.load_model_from_mlflow()
        if not model_loaded:
            raise ValueError("No model found to validate")

        # Load prediction data for validation
        data_loader = DataLoader(use_s3=USE_S3)
        df = data_loader.load_predicting_dataset()

        if df is None or df.empty:
            raise ValueError("No prediction data available for validation")

        # Make a test prediction
        prediction = predictor.predict(df)

        validation_result = {
            "model_loaded": True,
            "prediction_shape": (
                prediction.get("predictions", {}).get("shape") if prediction else None
            ),
            "timestamp": datetime.now().isoformat(),
            "status": "success",
        }

        logger.info(f"Model validation completed: {validation_result}")
        return validation_result

    except Exception as e:
        logger.error(f"Model validation failed: {e}")
        raise e


@task(name="check_data_quality")
def check_data_quality_task(data_type: str = "training") -> Dict[str, Any]:
    """Task to check data quality"""
    try:
        logger.info(f"Checking data quality for {data_type} data")

        data_loader = DataLoader(use_s3=USE_S3)

        if data_type == "training":
            df = data_loader.load_train_dataset()
        else:
            df = data_loader.load_predicting_dataset()

        if df is None or df.empty:
            return {"status": "failed", "error": "Dataset is empty"}

        # Basic data quality checks
        quality_checks = {
            "total_rows": len(df),
            "total_columns": len(df.columns),
            "missing_values": df.isnull().sum().sum(),
            "missing_percentage": (
                df.isnull().sum().sum() / (len(df) * len(df.columns))
            )
            * 100,
            "duplicate_rows": df.duplicated().sum(),
            "timestamp_range": {  "start": (
        df.index.min().isoformat() if hasattr(df.index.min(), "isoformat") else df.index.min()
    ),
    "end": (
        df.index.max().isoformat() if hasattr(df.index.max(), "isoformat") else df.index.max()
    ),
},
        }

        # Quality thresholds
        quality_score = 100
        if quality_checks["missing_percentage"] > 10:
            quality_score -= 30
        if quality_checks["duplicate_rows"] > len(df) * 0.05:
            quality_score -= 20

        quality_checks["quality_score"] = quality_score
        quality_checks["passed"] = quality_score >= 70
        quality_checks["status"] = "success"

        logger.info(f"Data quality check completed: score={quality_score}")
        return quality_checks

    except Exception as e:
        logger.error(f"Data quality check failed: {e}")
        return {"status": "failed", "error": str(e)}
