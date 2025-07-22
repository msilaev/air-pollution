"""
Main Prefect flows for MLOps pipeline
"""

import logging
from datetime import datetime

from prefect import flow
from prefect.task_runners import SequentialTaskRunner

from flows.tasks import (
    check_data_quality_task,
    collect_prediction_data_task,
    collect_training_data_task,
    train_model_task,
    validate_model_task,
)

logger = logging.getLogger(__name__)

@flow(
    name="training_pipeline",
    description="Complete training pipeline: data collection → training → validation",
    task_runner=SequentialTaskRunner(),
    retries=1,
)

def training_pipeline_flow(
    chunk_size_hours: int = 168,  # 1 week
    week_number: int = 2,
    force_refresh: bool = True,
):
    """
    Complete training pipeline flow

    Args:
        chunk_size_hours: Size of data chunks in hours (default: 168 = 1 week)
        week_number: Which week of data to collect (1-8)
        force_refresh: Whether to force fresh data collection
    """
    logger.info("Starting training pipeline: week=%s, chunk_size=%sh", 
                week_number, chunk_size_hours)

    # Step 1: Collect training data
    data_collection_result = collect_training_data_task(
        chunk_size_hours=chunk_size_hours,
        week_number=week_number,
        force_refresh=force_refresh,
    )

    # Step 2: Check data quality
    quality_check = check_data_quality_task(data_type="training")

    # Step 3: Train model (only if data quality is good)
    if quality_check.get("passed", False):
        training_result = train_model_task()

        # Step 4: Validate the trained model
        validation_result = validate_model_task()

        return {
            "data_collection": data_collection_result,
            "quality_check": quality_check,
            "training": training_result,
            "validation": validation_result,
            "pipeline_status": "success",
            "timestamp": datetime.now().isoformat(),
        }
    else:
        logger.warning("Data quality check failed, skipping training")
        return {
            "data_collection": data_collection_result,
            "quality_check": quality_check,
            "pipeline_status": "failed_quality_check",
            "timestamp": datetime.now().isoformat(),
        }

@flow(
    name="prediction_pipeline",
    description="Prediction pipeline: collect fresh data → generate predictions",
    task_runner=SequentialTaskRunner(),
    retries=1,
)
def prediction_pipeline_flow(chunk_size_hours: int = 48, week_number: int = 1):
    """
    Prediction pipeline flow

    Args:
        chunk_size_hours: Size of data chunks in hours (default: 48)
        week_number: Which week of data to collect (default: 1 = most recent)
    """

    logger.info(
        f"Starting prediction pipeline: week={week_number}, chunk_size={chunk_size_hours}h"
    )

    # Step 1: Collect fresh prediction data
    data_collection_result = collect_prediction_data_task(
        chunk_size_hours=chunk_size_hours, week_number=week_number
    )

    # Step 2: Check data quality
    quality_check = check_data_quality_task(data_type="predicting")

    return {
        "data_collection": data_collection_result,
        "quality_check": quality_check,
        "pipeline_status": (
            "success" if quality_check.get("passed", False) else "failed_quality_check"
        ),
        "timestamp": datetime.now().isoformat(),
    }


@flow(
    name="monitoring_pipeline",
    description="Model monitoring and drift detection pipeline",
    task_runner=SequentialTaskRunner(),
)
def monitoring_pipeline_flow():
    """
    Monitoring pipeline for model performance and data drift
    """

    logger.info("Starting monitoring pipeline")

    # Check data quality for both datasets
    training_quality = check_data_quality_task(data_type="training")
    prediction_quality = check_data_quality_task(data_type="predicting")

    train_result = train_model_task()

    # Validate current model
    model_validation = validate_model_task()

    # Determine if retraining is needed
    retrain_needed = False
    reasons = []

    if not training_quality.get("passed", False):
        retrain_needed = True
        reasons.append("Training data quality issues")

    if not prediction_quality.get("passed", False):
        reasons.append("Prediction data quality issues")

    if not model_validation.get("model_loaded", False):
        retrain_needed = True
        reasons.append("No model available")

    monitoring_result = {
        "training_quality": training_quality,
        "prediction_quality": prediction_quality,
        "model_validation": model_validation,
        "retrain_needed": retrain_needed,
        "retrain_reasons": reasons,
        "timestamp": datetime.now().isoformat(),
    }

    logger.info(f"Monitoring completed. Model metrics: {train_result}. "
                f"Retrain needed: {retrain_needed}")

    # Trigger retraining if needed
    if retrain_needed:
        logger.info("Triggering automatic retraining")
        training_result = training_pipeline_flow()
        monitoring_result["automatic_retrain"] = training_result

    return monitoring_result


@flow(
    name="full_mlops_pipeline",
    description="Complete MLOps pipeline with monitoring and automatic retraining",
    task_runner=SequentialTaskRunner(),
)
def full_mlops_pipeline_flow(
    training_chunk_hours: int = 168,
    training_week_number: int = 2,
    prediction_chunk_hours: int = 48,
    prediction_week_number: int = 1,
    force_retrain: bool = False,
):
    """
    Complete MLOps pipeline that orchestrates all components

    Args:
        training_chunk_hours: Hours of training data per chunk
        training_week_number: Week number for training data
        prediction_chunk_hours: Hours of prediction data per chunk
        prediction_week_number: Week number for prediction data
        force_retrain: Force model retraining regardless of monitoring
    """

    logger.info("Starting full MLOps pipeline")

    results = {"pipeline_start": datetime.now().isoformat()}

    # Step 1: Run monitoring to check current state
    if not force_retrain:
        monitoring_result = monitoring_pipeline_flow()
        results["monitoring"] = monitoring_result

        # If monitoring triggered retraining, we're done
        if monitoring_result.get("automatic_retrain"):
            results["training"] = monitoring_result["automatic_retrain"]
            train_performed = True
        else:
            train_performed = False
    else:
        train_performed = False

    # Step 2: Run training pipeline if needed
    if force_retrain or not train_performed:
        training_result = training_pipeline_flow(
            chunk_size_hours=training_chunk_hours,
            week_number=training_week_number,
            force_refresh=True,
        )
        results["training"] = training_result

    # Step 3: Always refresh prediction data
    prediction_result = prediction_pipeline_flow(
        chunk_size_hours=prediction_chunk_hours, week_number=prediction_week_number
    )
    results["prediction_data"] = prediction_result

    results["pipeline_end"] = datetime.now().isoformat()
    results["status"] = "completed"

    logger.info("Full MLOps pipeline completed successfully")

    return results
