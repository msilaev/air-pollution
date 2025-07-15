"""
Prefect deployment configurations and schedules
"""

from prefect.deployments import Deployment
from prefect.server.schemas.schedules import CronSchedule

from flows.main_flows import (
    full_mlops_pipeline_flow,
    monitoring_pipeline_flow,
    prediction_pipeline_flow,
    training_pipeline_flow,
)

# Training pipeline deployment - runs weekly on Sundays at 2 AM
training_deployment = Deployment.build_from_flow(
    flow=training_pipeline_flow,
    name="weekly-training-pipeline",
    schedule=CronSchedule(cron="0 2 * * 0"),  # Every Sunday at 2 AM
    parameters={
        "chunk_size_hours": 168,  # 1 week
        "week_number": 2,
        "force_refresh": True,
    },
    tags=["training", "ml", "weekly"],
    description="Weekly training pipeline for air pollution prediction model",
)

# Prediction data refresh deployment - runs daily at 6 AM
prediction_deployment = Deployment.build_from_flow(
    flow=prediction_pipeline_flow,
    name="daily-prediction-data-refresh",
    schedule=CronSchedule(cron="0 6 * * *"),  # Every day at 6 AM
    parameters={"chunk_size_hours": 48, "week_number": 1},
    tags=["prediction", "data-refresh", "daily"],
    description="Daily refresh of prediction data",
)

# Monitoring deployment - runs every 6 hours
monitoring_deployment = Deployment.build_from_flow(
    flow=monitoring_pipeline_flow,
    name="model-monitoring",
    schedule=CronSchedule(cron="0 */6 * * *"),  # Every 6 hours
    tags=["monitoring", "drift-detection", "automated"],
    description="Continuous model monitoring and drift detection",
)

# Full pipeline deployment - runs weekly on Saturdays at midnight
full_pipeline_deployment = Deployment.build_from_flow(
    flow=full_mlops_pipeline_flow,
    name="weekly-full-mlops-pipeline",
    schedule=CronSchedule(cron="0 0 * * 6"),  # Every Saturday at midnight
    parameters={
        "training_chunk_hours": 168,
        "training_week_number": 2,
        "prediction_chunk_hours": 48,
        "prediction_week_number": 1,
        "force_retrain": False,
    },
    tags=["mlops", "full-pipeline", "weekly"],
    description="Complete MLOps pipeline with monitoring and retraining",
)

if __name__ == "__main__":
    # Apply all deployments
    training_deployment.apply()
    prediction_deployment.apply()
    monitoring_deployment.apply()
    full_pipeline_deployment.apply()

    print("✅ All Prefect deployments have been applied!")
    print("\nDeployments created:")
    print("- weekly-training-pipeline (Sundays at 2 AM)")
    print("- daily-prediction-data-refresh (Daily at 6 AM)")
    print("- model-monitoring (Every 6 hours)")
    print("- weekly-full-mlops-pipeline (Saturdays at midnight)")
