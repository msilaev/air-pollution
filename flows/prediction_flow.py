import json
import os
import time
from datetime import datetime, timedelta

import boto3
from prefect import flow, task

from src.data.data_loader import DataLoader
from src.models.pollution_predictor import PollutionPredictor
from src.monitoring.cloudwatch_metrics import CloudWatchMetrics


@task
def log_data_quality_metrics(df):
    """Log data quality metrics"""
    cw_metrics = CloudWatchMetrics()

    missing_values = df.isnull().sum().sum()
    cw_metrics.put_data_quality_metrics(df.shape, missing_values)

    print(f"Logged data quality metrics: shape={df.shape}, missing={missing_values}")


@task
def log_prediction_metrics(predictions, model_version):
    """Log prediction metrics to CloudWatch"""
    cw_metrics = CloudWatchMetrics()

    # Count predictions
    prediction_count = len(predictions.get("predictions", {}))
    cw_metrics.put_prediction_count(prediction_count, model_version)

    print(f"Logged prediction metrics to CloudWatch for model version: {model_version}")


@task
def get_latest_model_version():
    """Get the latest model version from Parameter Store"""
    ssm_client = boto3.client("ssm")

    try:
        response = ssm_client.get_parameter(Name="/pollution-model/latest-version")
        model_version = response["Parameter"]["Value"]
        print(f"Using model version: {model_version}")
        return model_version
    except ssm_client.exceptions.ParameterNotFound:
        print("No model version found, using default")
        return None


@task
def load_recent_data():
    """Load recent data for prediction"""
    data_loader = DataLoader()

    # Load last 48 hours of data
    end_time = datetime.now()
    start_time = end_time - timedelta(hours=48)

    df = data_loader.load_time_range(start_time, end_time)
    print(f"Loaded recent data with shape: {df.shape}")
    return df


@task
def make_predictions(df, model_version):
    """Generate 6-hour predictions"""
    predictor = PollutionPredictor()

    if model_version:
        predictor.load_model_from_s3(model_version)
    else:
        raise ValueError("No model version available")

    predictions = predictor.predict(df)
    print(f"Generated predictions for {len(predictions['predictions'])} features")
    return predictions


@task
def save_predictions_to_s3(predictions):
    """Save predictions to S3 for later analysis"""
    s3_client = boto3.client("s3")
    bucket = os.environ.get("S3_BUCKET", "air-pollution-models")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    key = f"predictions/predictions_{timestamp}.json"

    s3_client.put_object(
        Bucket=bucket,
        Key=key,
        Body=json.dumps(predictions, indent=2),
        ContentType="application/json",
    )

    print(f"Saved predictions to s3://{bucket}/{key}")
    return f"s3://{bucket}/{key}"


@task
def send_predictions_to_api(predictions):
    """Send predictions to external API or dashboard"""
    # This could be your Grafana webhook or other monitoring system
    import requests

    api_endpoint = os.environ.get("PREDICTIONS_API_ENDPOINT")
    if api_endpoint:
        try:
            response = requests.post(api_endpoint, json=predictions)
            response.raise_for_status()
            print("Predictions sent to API successfully")
        except Exception as e:
            print(f"Failed to send predictions to API: {e}")


@flow(name="pollution-prediction")
def prediction_flow():
    """Main prediction flow"""
    start_time = time.time()

    try:
        print("Starting pollution prediction flow")

        # Get latest model
        model_version = get_latest_model_version()

        # Load recent data
        df = load_recent_data()

        # Log data quality metrics
        log_data_quality_metrics(df)

        # Make predictions
        predictions = make_predictions(df, model_version)

        # Save and distribute predictions
        s3_path = save_predictions_to_s3(predictions)
        send_predictions_to_api(predictions)

        # Log metrics to CloudWatch
        log_prediction_metrics(predictions, model_version)

        # Log successful flow execution
        duration = time.time() - start_time
        cw_metrics = CloudWatchMetrics()
        cw_metrics.put_flow_execution_metrics(
            "pollution-prediction", "success", duration
        )

        return {
            "predictions": predictions,
            "s3_path": s3_path,
            "model_version": model_version,
        }

    except Exception as e:
        # Log failed flow execution
        duration = time.time() - start_time
        cw_metrics = CloudWatchMetrics()
        cw_metrics.put_flow_execution_metrics(
            "pollution-prediction", "failure", duration
        )
        raise e


if __name__ == "__main__":
    prediction_flow()
