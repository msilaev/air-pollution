import logging
import os
import tempfile

import boto3
import pandas as pd
from botocore.exceptions import ClientError

from src.config import INTERIM_DATA_DIR


class DataLoader:
    def __init__(self, use_s3=False):
        self.use_s3 = use_s3
        if use_s3:
            self.s3_client = boto3.client("s3")
            self.bucket = os.environ.get("AWS_S3_BUCKET_NAME", "air-pollution-data")
            self.bucket = self.bucket.replace("s3://", "").strip()
        self.logger = logging.getLogger(__name__)

    def load_from_local(self, filename):
        """Load data from local INTERIM_DATA_DIR"""
        try:
            file_path = os.path.join(INTERIM_DATA_DIR, filename)

            if not os.path.exists(file_path):
                raise FileNotFoundError(f"File not found: {file_path}")

            if filename.endswith(".parquet"):
                return pd.read_parquet(file_path)
            elif filename.endswith(".csv"):
                return pd.read_csv(file_path)
            else:
                raise ValueError(f"Unsupported file format: {filename}")
        except Exception as e:
            self.logger.error(f"Failed to load data from local: {e}")
            raise

    def load_from_s3(self, key):
        """Load data from S3"""
        try:
            self.logger.info(f"Loading data from S3: s3://{self.bucket}/{key}")

            # Use Windows-compatible temporary directory
            with tempfile.NamedTemporaryFile(
                delete=False, suffix=".parquet"
            ) as temp_file:
                temp_path = temp_file.name

            try:
                # Download file from S3
                self.s3_client.download_file(self.bucket, key, temp_path)
                self.logger.info(f"Downloaded {key} to {temp_path}")

                # Load the file
                if key.endswith(".parquet"):
                    df = pd.read_parquet(temp_path)
                elif key.endswith(".csv"):
                    df = pd.read_csv(temp_path)
                else:
                    raise ValueError(f"Unsupported file format: {key}")

                self.logger.info(f"✅ Loaded {len(df)} records from S3: {key}")
                return df

            finally:
                # Clean up temporary file
                if os.path.exists(temp_path):
                    os.unlink(temp_path)

        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            if error_code == "NoSuchKey":
                self.logger.error(f"❌ File not found in S3: s3://{self.bucket}/{key}")
                # List available files for debugging
                self._list_s3_files()
            elif error_code == "NoSuchBucket":
                self.logger.error(f"❌ Bucket not found: {self.bucket}")
            else:
                self.logger.error(f"❌ S3 Error ({error_code}): {e}")
            raise
        except Exception as e:
            self.logger.error(f"❌ Failed to load data from S3: {e}")
            raise

    def load_time_range(self, start_time, end_time):
        """Load data for specific time range"""
        try:
            # Load from local file (based on your notebook)
            if self.use_s3:
                df = self.load_from_s3("training-data/air_pollution_data_total.parquet")
            else:
                df = self.load_from_local("air_pollution_data_total.parquet")

            df["Timestamp"] = pd.to_datetime(df["Timestamp"])

            mask = (df["Timestamp"] >= start_time) & (df["Timestamp"] <= end_time)
            filtered_df = df.loc[mask].copy()

            self.logger.info(
                f"Loaded {len(filtered_df)} records for time range {start_time} to {end_time}"
            )
            return filtered_df
        except Exception as e:
            self.logger.error(f"Failed to load time range data: {e}")
            raise

    def load_train_dataset(self):
        """Load the training dataset"""
        try:
            if self.use_s3:
                df = self.load_from_s3(
                    "training_data/air_pollution_data_training_total.parquet"
                )
            else:
                df = self.load_from_local("air_pollution_data_training_total.parquet")

            df["Timestamp"] = pd.to_datetime(df["Timestamp"])
            self.logger.info(f"Loaded full dataset with {len(df)} records")
            return df
        except Exception as e:
            self.logger.error(f"Failed to load full dataset: {e}")
            raise

    def load_predicting_dataset(self):
        """Load the predicting dataset"""
        try:
            if self.use_s3:
                df = self.load_from_s3(
                    "predicting_data/air_pollution_data_predicting_total.parquet"
                )
            else:
                df = self.load_from_local("air_pollution_data_predicting_total.parquet")

            df["Timestamp"] = pd.to_datetime(df["Timestamp"])
            self.logger.info(f"Loaded predicting dataset with {len(df)} records")
            return df
        except Exception as e:
            self.logger.error(f"Failed to load predicting dataset: {e}")
            raise

    # def validate_data(self, df):
    #     """Validate data quality"""
    #     required_columns = ['Timestamp', 'Particulate matter < 10 µm', 'Particulate matter < 2.5 µm']
    #     missing_cols = [col for col in required_columns if col not in df.columns]

    #     if missing_cols:
    #         raise ValueError(f"Missing required columns: {missing_cols}")

    #     # Check for missing values
    #     null_counts = df[required_columns].isnull().sum()
    #     if null_counts.any():
    #         self.logger.warning(f"Found null values: {null_counts.to_dict()}")

    #     return True

    # def get_latest_data(self, hours=48):
    #     """Get latest available data for predictions"""
    #     # For local data, load the full dataset and get the latest portion
    #     df = self.load_full_dataset()

    #     # Get the latest timestamp and work backwards
    #     latest_time = df['Timestamp'].max()
    #     start_time = latest_time - timedelta(hours=hours)

    #     mask = df['Timestamp'] >= start_time
    #     filtered_df = df.loc[mask].copy()

    #     self.logger.info(f"Got latest {hours} hours of data: {len(filtered_df)} records")
    #     return filtered_df
