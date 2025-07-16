import logging
from datetime import datetime
import os

from fastapi import APIRouter, HTTPException
from mlflow import MlflowClient, set_tracking_uri

from src.api.schemas import PredictionResponse
from src.config import USE_S3
from src.data.data_ingestion import DataIngestion
from src.data.data_loader import DataLoader
from src.models.pollution_predictor import PollutionPredictor

# Set MLflow tracking URI based on USE_S3
if USE_S3:
    # Use S3/remote tracking URI from environment or config
    tracking_uri = os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")
else:
    # Use local SQLite DB for MLflow
    tracking_uri = os.getenv("MLFLOW_TRACKING_URI", "sqlite:///mlflow.db")
set_tracking_uri(tracking_uri)

router = APIRouter()
logger = logging.getLogger(__name__)

# Initialize components (could be moved to dependencies)
predictor = PollutionPredictor()
data_loader = DataLoader(use_s3=USE_S3)
data_ingestion = DataIngestion(use_s3=USE_S3)

# Try to load the latest model on startup
try:
    print("Attempting to load model on startup...")
    model_loaded = predictor.load_model_from_mlflow()
    if model_loaded:
        print("✅ Model loaded successfully on startup")
    else:
        print("⚠️ No model found on startup - will need to train first")
except Exception as e:
    print(f"⚠️ Failed to load model on startup: {e}")
    print("Model will need to be trained or loaded manually")


@router.get("/train")
async def train_model():
    """Train model with existing data"""
    try:
        # Load training dataset and check if it exists
        try:
            df = data_loader.load_train_dataset()
        except FileNotFoundError:
            raise HTTPException(
                status_code=404,
                detail="No training data available. Please ensure training data is properly loaded.",
            )

        # Check if dataframe is empty or has insufficient data
        if df is None or df.empty:
            raise HTTPException(
                status_code=400, detail="Training dataset is empty. Cannot train model."
            )

        # Check if we have enough data for training
        min_required_rows = (
            predictor.training_hours + predictor.n_steps + 10
        )  # Extra buffer for training
        if len(df) < min_required_rows:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient data for training. Need at least {min_required_rows} rows, got {len(df)}.",
            )

        print(f"Loaded data with shape: {df.shape}")

        # Train the model
        metrics = predictor.train(df)

        logger.info(f"Model trained successfully at {datetime.now()}")
        return metrics

    except Exception as e:
        logger.error(f"Training failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Training failed: {str(e)}")


@router.get("/predict", response_model=PredictionResponse)
async def predict_pollution(fetch_fresh_data: bool = False):
    """Generate pollution predictions for the next 6 hours"""
    try:
        # Only fetch fresh data if explicitly requested
        if fetch_fresh_data:
            data_ingestion = DataIngestion(use_s3=USE_S3)
            data_ingestion.fetch_pollution_data(
                data_type="predicting", chunk_size_hours=48, week_number=1
            )

        # Load prediction dataset and check if it exists
        try:
            df = data_loader.load_predicting_dataset()
        except FileNotFoundError:
            # If no prediction data exists, try to fetch it automatically
            try:
                data_ingestion = DataIngestion(use_s3=USE_S3)
                data_ingestion.fetch_pollution_data(
                    data_type="predicting", chunk_size_hours=48, week_number=1
                )
                df = data_loader.load_predicting_dataset()
            except Exception as fetch_error:
                raise HTTPException(
                    status_code=404,
                    detail=f"No prediction data available and failed to fetch fresh data: {str(fetch_error)}",
                )

        # Check if dataframe is empty or has insufficient data
        if df is None or df.empty:
            raise HTTPException(
                status_code=400,
                detail="Prediction dataset is empty. Please refresh the data first.",
            )

        # Check if we have enough data for predictions (need at least training_hours + n_steps)
        min_required_rows = predictor.training_hours + predictor.n_steps
        if len(df) < min_required_rows:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient data for predictions. Need at least {min_required_rows} rows, got {len(df)}. Please refresh the data.",
            )

        print(f"Loaded data with shape: {df.shape}")

        # Load model if not already loaded
        if not predictor.model:
            model_loaded = predictor.load_model_from_mlflow()
            if not model_loaded:
                raise HTTPException(
                    status_code=500,
                    detail="No trained model available. Please train a model first.",
                )

        # Make prediction
        prediction = predictor.predict(df)

        # logger.info(f"Generated prediction at {datetime.now()}")
        return prediction

    except Exception as e:
        # logger.error(f"Prediction failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")


@router.post("/data/refresh")
async def refresh_prediction_data():
    """Fetch fresh pollution data for predictions"""
    try:
        data_ingestion = DataIngestion(use_s3=USE_S3)
        data_ingestion.fetch_pollution_data(
            data_type="predicting", chunk_size_hours=48, week_number=1
        )

        # Load the refreshed data to verify
        df = data_loader.load_predicting_dataset()

        return {
            "status": "success",
            "message": "Prediction data refreshed successfully",
            "data_shape": df.shape,
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Data refresh failed: {str(e)}")


@router.get("/data/status")
async def get_data_status():
    """Check the availability and status of training and prediction data"""
    status = {
        "training_data": {"available": False, "shape": None, "error": None},
        "prediction_data": {"available": False, "shape": None, "error": None},
        "model_status": {"loaded": bool(predictor.model), "error": None},
    }

    # Check training data
    try:
        df_train = data_loader.load_train_dataset()
        if df_train is not None and not df_train.empty:
            status["training_data"]["available"] = True
            status["training_data"]["shape"] = df_train.shape
            min_required = predictor.training_hours + predictor.n_steps + 10
            status["training_data"]["sufficient"] = len(df_train) >= min_required
            status["training_data"]["min_required_rows"] = min_required
        else:
            status["training_data"]["error"] = "Dataset is empty"
    except Exception as e:
        status["training_data"]["error"] = str(e)

    # Check prediction data
    try:
        df_pred = data_loader.load_predicting_dataset()
        if df_pred is not None and not df_pred.empty:
            status["prediction_data"]["available"] = True
            status["prediction_data"]["shape"] = df_pred.shape
            min_required = predictor.training_hours + predictor.n_steps
            status["prediction_data"]["sufficient"] = len(df_pred) >= min_required
            status["prediction_data"]["min_required_rows"] = min_required
        else:
            status["prediction_data"]["error"] = "Dataset is empty"
    except Exception as e:
        status["prediction_data"]["error"] = str(e)

    # Check model status
    try:
        if not predictor.model:
            # Try to load model
            model_loaded = predictor.load_model_from_mlflow()
            status["model_status"]["loaded"] = model_loaded
            if not model_loaded:
                status["model_status"]["error"] = "No trained model available"
    except Exception as e:
        status["model_status"]["error"] = str(e)

    return status


@router.get("/model/info")
async def get_model_info():
    """Get information about the current model including performance metrics"""

    # Try to load model if not already loaded
    if not predictor.model:
        try:
            print("Model not loaded, attempting to load from MLflow...")
            model_loaded = predictor.load_model_from_mlflow()
            if model_loaded:
                print("✅ Model loaded successfully for info request")
            else:
                print("❌ No model available to load")
        except Exception as e:
            print(f"❌ Failed to load model: {e}")

    model_info = {
        "model_loaded": bool(predictor.model),
        "model_type": "Lasso Regression with MultiOutput",
        "historical_feature_hours": predictor.training_hours,
        "prediction_hours": predictor.n_steps,
        "target_features": (
            predictor.features_pollution if predictor.features_pollution else []
        ),
        "metrics": {"r2_score": None, "rmse": None, "mae": None, "mse": None},
        "model_metadata": {},
    }

    print(f"Model loaded: {predictor.model}")

    # Try to get latest model metrics from MLflow
    try:
        if predictor.model:
            client = MlflowClient()

            # Get the latest model version
            try:
                latest_versions = client.get_latest_versions(
                    "pollution_predictor", stages=["Production"]
                )
                if not latest_versions:
                    latest_versions = client.get_latest_versions(
                        "pollution_predictor", stages=["None"]
                    )

                if latest_versions:
                    latest_version = latest_versions[0]
                    run_id = latest_version.run_id

                    # Get metrics from the run
                    run = client.get_run(run_id)
                    metrics = run.data.metrics

                    model_info["metrics"]["r2_score"] = metrics.get("r2_score")
                    model_info["metrics"]["rmse"] = metrics.get("rmse")
                    model_info["metrics"]["mae"] = metrics.get("mae")
                    model_info["metrics"]["mse"] = metrics.get("mse")

                    # Add additional metadata
                    model_info["model_metadata"] = {
                        "run_id": run_id,
                        "model_version": latest_version.version,
                        "creation_time": latest_version.creation_timestamp,
                        "training_samples": metrics.get("training_samples"),
                        "validation_samples": metrics.get("validation_samples"),
                    }

            except Exception as mlflow_error:
                model_info["metrics"][
                    "error"
                ] = f"Could not retrieve metrics: {str(mlflow_error)}"
        else:
            model_info[
                "error"
            ] = "No model is currently loaded. Please train a model first or check MLflow for available models."

    except Exception as e:
        model_info["error"] = f"Error getting model info: {str(e)}"

    return model_info


@router.get("/models/mlflow/list")
async def list_mlflow_models():
    """List MLflow model versions"""
    try:
        client = MlflowClient()
        model_versions = client.search_model_versions("name='pollution_predictor'")

        versions = []
        for mv in model_versions:
            versions.append(
                {
                    "version": mv.version,
                    "run_id": mv.run_id,
                    "stage": mv.current_stage,
                    "creation_timestamp": mv.creation_timestamp,
                }
            )

        return {"model_versions": versions}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to list MLflow models: {str(e)}"
        )


@router.post("/load_model/mlflow/{model_version}")
async def load_mlflow_model(model_version: str):
    """Load a specific MLflow model version"""
    global model_trained
    try:
        success = predictor.load_model_from_mlflow(model_version=model_version)
        if success:
            model_trained = True
            return {
                "status": "success",
                "message": f"MLflow model version {model_version} loaded successfully",
                "model_version": model_version,
                "timestamp": datetime.now().isoformat(),
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to load model")
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to load MLflow model: {str(e)}"
        )
