import json
import os
import subprocess
import tempfile
from datetime import datetime, timedelta

import boto3
import joblib
import mlflow
import mlflow.sklearn
import numpy as np
import pandas as pd
from dotenv import load_dotenv
from mlflow.tracking import MlflowClient
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import Lasso, LinearRegression, Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.model_selection import TimeSeriesSplit
from sklearn.multioutput import MultiOutputRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from src.config import USE_S3


class PollutionPredictor:
    def __init__(self, training_hours=24, n_steps=6):
        self.training_hours = training_hours
        self.n_steps = n_steps
        self.model = None
        self.scaler = None
        self.features_pollution = None
        self.features_additional = ["hour_sin", "hour_cos", "day_sin", "day_cos"]

        # Initialize MLflow
        self.setup_mlflow()
        print("MLflow tracking URI set to:", mlflow.get_tracking_uri())

        # AWS clients
        self.s3_client = boto3.client("s3")
        self.s3_bucket = os.environ.get("AWS_S3_BUCKET_NAME", "air-pollution-models")

    def setup_mlflow(self):
        """Setup MLflow tracking URI and S3 endpoint if available"""
        import mlflow
        import os
        if USE_S3:
            tracking_uri = os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")
        else:
            tracking_uri = os.getenv("MLFLOW_TRACKING_URI", "sqlite:///mlflow.db")
        mlflow.set_tracking_uri(tracking_uri)

        try:
            experiment = mlflow.get_experiment_by_name("Pollution Prediction")

            # Get S3 bucket name and construct proper S3 URI
            s3_bucket = os.environ.get("AWS_S3_BUCKET_NAME")
            if USE_S3 and s3_bucket:
                artifact_location = f"s3://{s3_bucket}/air_pollution_prediction"
            else:
                artifact_location = None  # Use default local artifact store

            if experiment is None:
                if artifact_location:
                    experiment_id = mlflow.create_experiment(
                        "Pollution Prediction", artifact_location=artifact_location
                    )
                else:
                    experiment_id = mlflow.create_experiment("Pollution Prediction")
            else:
                experiment_id = experiment.experiment_id
            mlflow.set_experiment(experiment_id)

        except Exception as e:
            print(f"Failed to setup MLflow: {e}")

    def create_features(self, df):
        """Create temporal features as in your notebook"""
        df = df.copy()
        df["Timestamp"] = pd.to_datetime(df["Timestamp"])

        print(df.columns)

        # Extract pollution features (PM10, PM2.5)
        self.features_pollution = [
            col for col in df.columns if ("matter" in col or "Nitrogen" in col)
        ]

        df = df[self.features_pollution + ["Timestamp"]].copy()

        # Create temporal features
        hours = df["Timestamp"].dt.hour
        days_of_week = df["Timestamp"].dt.dayofweek

        df["hour_sin"] = np.sin(2 * np.pi * hours / 24)
        df["hour_cos"] = np.cos(2 * np.pi * hours / 24)
        df["day_sin"] = np.sin(2 * np.pi * days_of_week / 7)
        df["day_cos"] = np.cos(2 * np.pi * days_of_week / 7)

        for feature in self.features_pollution:
            print(df[feature].head())

        df.fillna(method="ffill", inplace=True)
        df.fillna(method="bfill", inplace=True)

        # print(f"nan values in df: {df.isna().sum().sum()}")

        return df

    def prepare_sequences(self, df):
        """Prepare training sequences exactly as in your notebook"""
        df_features = self.create_features(df)

        # print(f"nan values in df_features: {df_features.isna().sum().sum()}")

        set_pollution_additional = np.array(
            df_features[self.features_additional].values
        )
        set_pollution_target = np.array(df_features[self.features_pollution].values)

        # Prepare training data (your exact logic)
        X = []
        X_additional = []
        y = []

        for i in range(
            self.training_hours, len(set_pollution_additional) - self.n_steps + 1
        ):
            X.append(set_pollution_target[i - self.training_hours : i])
            X_additional.append(set_pollution_additional[i])
            y.append(set_pollution_target[i : i + self.n_steps])

        X, X_additional, y = np.array(X), np.array(X_additional), np.array(y)

        # Reshape as in your notebook
        X = X.reshape(X.shape[0], X.shape[1] * X.shape[2])
        y = y.reshape(y.shape[0], y.shape[1] * y.shape[2])
        X = np.concatenate((X, X_additional), axis=1)

        return X, y

    def train(self, df):
        """Train model using your exact approach"""
        print(f"Training model with data shape: {df.shape}")

        # Prepare sequences
        with mlflow.start_run() as run:
            mlflow.set_tag("model_type", "Lasso Regression with MultiOutput")
            mlflow.log_param("training_hours", self.training_hours)
            mlflow.log_param("n_steps", self.n_steps)
            mlflow.log_param("alpha", 1.0)

            X, y = self.prepare_sequences(df)

            # Time series split (your exact logic)
            tscv = TimeSeriesSplit(n_splits=3)
            for train_index, val_index in tscv.split(X):
                pass  # Get the last split

            X_train, X_val = X[train_index], X[val_index]
            y_train, y_val = y[train_index], y[val_index]

            # Scale features
            self.scaler = StandardScaler()
            X_train = self.scaler.fit_transform(X_train)
            X_val = self.scaler.transform(X_val)

            # Lasso Regression
            self.model = MultiOutputRegressor(Lasso(alpha=1.0))  # Adjust alpha
            self.model.fit(X_train, y_train)

            # Evaluate
            y_pred = self.model.predict(X_val)
            mae = mean_absolute_error(y_val, y_pred)
            mse = mean_squared_error(y_val, y_pred)
            rmse = np.sqrt(mse)
            accuracy_score = self.model.score(X_val, y_val)

            # Log metrics
            mlflow.log_metric("mae", mae)
            mlflow.log_metric("mse", mse)
            mlflow.log_metric("rmse", rmse)
            mlflow.log_metric("r2_score", accuracy_score)
            mlflow.log_metric("training_samples", len(X_train))
            mlflow.log_metric("validation_samples", len(X_val))

            # Log model and artifacts to S3
            mlflow.sklearn.log_model(
                self.model, "model", registered_model_name="pollution_predictor"
            )

            # Create temporary files for artifacts
            with tempfile.TemporaryDirectory() as temp_dir:
                # Save scaler
                scaler_path = os.path.join(temp_dir, "scaler.pkl")
                joblib.dump(self.scaler, scaler_path)
                mlflow.log_artifact(scaler_path, "artifacts")

                # Save features
                features_path = os.path.join(temp_dir, "features.pkl")
                joblib.dump(self.features_pollution, features_path)
                mlflow.log_artifact(features_path, "artifacts")

                # Save model metadata
                metadata = {
                    "training_hours": self.training_hours,
                    "n_steps": self.n_steps,
                    "features_pollution": self.features_pollution,
                    "features_additional": self.features_additional,
                    "model_type": "Lasso Regression with MultiOutput",
                    "created_at": datetime.now().isoformat(),
                }

                metadata_path = os.path.join(temp_dir, "model_metadata.json")

                with open(metadata_path, "w") as f:
                    json.dump(metadata, f, indent=2)
                mlflow.log_artifact(metadata_path, "artifacts")

            self.run_id = run.info.run_id

            metrics = {
                "mae": mae,
                "mse": mse,
                "rmse": rmse,
                "r2_score": accuracy_score,
                "training_samples": len(X_train),
                "validation_samples": len(X_val),
                "mlflow_run_id": self.run_id,
                "mlflow_experiment_id": run.info.experiment_id,
            }

        print(
            f"Model trained - MAE: {mae:.3f}, RMSE: {rmse:.3f}, R2: {accuracy_score:.3f}"
        )
        print(f"MLflow run ID: {self.run_id}")
        print(f"Artifacts stored in S3")
        return metrics

    def load_model_from_mlflow(self, run_id=None, model_version=None):
        """Load model from MLflow S3 artifact store"""
        try:
            if model_version:
                model_uri = f"models:/pollution_predictor/{model_version}"
                self.model = mlflow.sklearn.load_model(model_uri)

                client = MlflowClient()
                model_version_info = client.get_model_version(
                    "pollution_predictor", model_version
                )
                run_id = model_version_info.run_id

            elif run_id:
                model_uri = f"runs:/{run_id}/model"
                self.model = mlflow.sklearn.load_model(model_uri)
            else:
                client = MlflowClient()
                latest_version = client.get_latest_versions(
                    "pollution_predictor", stages=["Production"]
                )

                if not latest_version:
                    latest_version = client.get_latest_versions(
                        "pollution_predictor", stages=["None"]
                    )
                if not latest_version:
                    raise ValueError("No model version found in MLflow")

                model_version = latest_version[0].version
                run_id = latest_version[0].run_id
                model_uri = f"models:/pollution_predictor/{model_version}"
                self.model = mlflow.sklearn.load_model(model_uri)

            # Download artifacts from S3
            with tempfile.TemporaryDirectory() as temp_dir:
                # Download scaler - CORRECTED SYNTAX
                scaler_artifact_path = mlflow.artifacts.download_artifacts(
                    artifact_uri=f"runs:/{run_id}/artifacts/scaler.pkl",
                    dst_path=temp_dir,
                )
                self.scaler = joblib.load(scaler_artifact_path)

                # Download features - CORRECTED SYNTAX
                features_artifact_path = mlflow.artifacts.download_artifacts(
                    artifact_uri=f"runs:/{run_id}/artifacts/features.pkl",
                    dst_path=temp_dir,
                )
                self.features_pollution = joblib.load(features_artifact_path)

                # Download metadata - CORRECTED SYNTAX
                try:
                    metadata_artifact_path = mlflow.artifacts.download_artifacts(
                        artifact_uri=f"runs:/{run_id}/artifacts/model_metadata.json",
                        dst_path=temp_dir,
                    )
                    with open(metadata_artifact_path, "r") as f:
                        metadata = json.load(f)
                    self.training_hours = metadata.get("training_hours", 24)
                    self.n_steps = metadata.get("n_steps", 6)
                    self.features_additional = metadata.get(
                        "features_additional",
                        ["hour_sin", "hour_cos", "day_sin", "day_cos"],
                    )
                    print("✓ Model metadata loaded successfully")
                except Exception as metadata_error:
                    print(f"Warning: Could not load model metadata: {metadata_error}")

            print(f"✓ Model loaded from MLflow S3 artifacts: {model_uri}")
            print(f"✓ Run ID: {run_id}")
            return True

        except Exception as e:
            print(f"❌ Failed to load model from MLflow: {e}")
            return False

    def predict(self, df, target_timestamp=None):
        """Make predictions for the next 6 hours"""

        if self.model is None:
            raise ValueError(
                "Model is not loaded. Please load the model first using load_model_from_mlflow()"
            )

        if target_timestamp is None:
            target_timestamp = datetime.now()

        df_features = self.create_features(df)

        # Get the latest available data for prediction
        latest_data = df_features.tail(self.training_hours + self.n_steps)

        set_pollution_additional = np.array(
            latest_data[self.features_additional].values
        )
        set_pollution_target = np.array(latest_data[self.features_pollution].values)

        # Prepare input (last sequence)
        X_input = set_pollution_target[-self.training_hours :].flatten()
        X_additional_input = set_pollution_additional[-1]
        X_combined = np.concatenate([X_input, X_additional_input]).reshape(1, -1)

        # Scale and predict
        X_scaled = self.scaler.transform(X_combined)
        prediction = self.model.predict(X_scaled)

        # Reshape prediction
        prediction = prediction.reshape(self.n_steps, len(self.features_pollution))
        historical_data = set_pollution_target[-self.training_hours :]
        historical_timestamps = latest_data["Timestamp"].values[-self.training_hours :]

        # Default station name (this should match your actual station data)
        # You may want to pass this as a parameter or detect it from the data
        # Note: Station names are already included in feature names, so we don't need to add them again

        # Format results
        results = {
            "prediction_timestamp": target_timestamp.isoformat(),
            "predictions": {},
            "historical_data": {},
        }

        for i, feature in enumerate(self.features_pollution):
            # Extract pollutant and station from feature name (e.g., "Nitrogen dioxide_Helsinki Kallio 2")
            if "_" in feature:
                parts = feature.split("_", 1)  # Split only on first underscore
                pollutant = (
                    parts[0].replace("Particulate matter < ", "PM").replace(" µm", "")
                )
                station = parts[1]
                pollutant_station_key = f"{pollutant}_{station}"
            else:
                # Fallback if no underscore found
                pollutant_station_key = feature.replace(
                    "Particulate matter < ", "PM"
                ).replace(" µm", "")

            results["predictions"][pollutant_station_key] = {
                f"hour_{j+1}": {
                    "value": float(prediction[j, i]),
                    "timestamp": (
                        target_timestamp + timedelta(hours=j + 1)
                    ).isoformat(),
                }
                for j in range(self.n_steps)
            }

        for i, feature in enumerate(self.features_pollution):
            # Extract pollutant and station from feature name (e.g., "Nitrogen dioxide_Helsinki Kallio 2")
            if "_" in feature:
                parts = feature.split("_", 1)  # Split only on first underscore
                pollutant = (
                    parts[0].replace("Particulate matter < ", "PM").replace(" µm", "")
                )
                station = parts[1]
                pollutant_station_key = f"{pollutant}_{station}"
            else:
                # Fallback if no underscore found
                pollutant_station_key = feature.replace(
                    "Particulate matter < ", "PM"
                ).replace(" µm", "")

            results["historical_data"][pollutant_station_key] = []

            try:
                for j in range(self.training_hours):
                    ts = historical_timestamps[j]
                    value = historical_data[j, i]
                    results["historical_data"][pollutant_station_key].append(
                        {
                            "timestamp": pd.to_datetime(ts).isoformat(),
                            "value": float(value),
                        }
                    )
            except Exception as e:
                # If there's an error with historical data for this feature, skip it
                results["historical_data"][pollutant_station_key] = []

        return results
