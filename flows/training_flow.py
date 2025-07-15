import os

import boto3
import pandas as pd
from prefect import flow, task
from prefect.blocks.system import Secret

from src.data.data_loader import DataLoader
from src.models.pollution_predictor import PollutionPredictor
from src.monitoring.evidently_monitor import ModelMonitor


@task
def load_training_data():
    """Load data for training"""
    data_loader = DataLoader()
    df = data_loader.load_from_s3("training-data/air_pollution_data_total.parquet")
    print(f"Loaded training data with shape: {df.shape}")
    return df


@task
def check_data_drift(df):
    """Check for data drift before training"""
    monitor = ModelMonitor()
    drift_results = monitor.detect_drift(df)
    print(f"Data drift detected: {drift_results['dataset_drift_detected']}")
    return drift_results


@task
def train_pollution_model(df):
    """Train the pollution prediction model"""
    predictor = PollutionPredictor(training_hours=24, n_steps=6)
    metrics = predictor.train(df)

    # Save model to S3
    model_info = predictor.save_model_to_s3()

    return {"metrics": metrics, "model_info": model_info}


@task
def update_model_registry(model_info, metrics):
    """Update model registry with new model version"""
    # Update DynamoDB or Parameter Store with latest model version
    ssm_client = boto3.client("ssm")

    ssm_client.put_parameter(
        Name="/pollution-model/latest-version",
        Value=model_info["model_version"],
        Type="String",
        Overwrite=True,
    )

    ssm_client.put_parameter(
        Name=f'/pollution-model/{model_info["model_version"]}/metrics',
        Value=str(metrics),
        Type="String",
        Overwrite=True,
    )

    print(f"Updated model registry with version: {model_info['model_version']}")


@flow(name="pollution-model-training")
def training_flow():
    """Main training flow"""
    print("Starting pollution model training flow")

    # Load data
    df = load_training_data()

    # Check data drift
    drift_results = check_data_drift(df)

    # Train model
    training_results = train_pollution_model(df)

    # Update registry
    update_model_registry(training_results["model_info"], training_results["metrics"])

    return training_results


if __name__ == "__main__":
    training_flow()
