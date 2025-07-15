import datetime as dt
import io
import json
import logging
import os
import sys
from datetime import datetime, timedelta

import boto3
import matplotlib
import pandas as pd
import requests
from geopy.geocoders import Nominatim

from src.config import INTERIM_DATA_DIR, PROJ_ROOT, RAW_DATA_DIR

sys.path.append(PROJ_ROOT)

from scripts.data_from_stations import get_air_pollution_data_timeInterval


class DataIngestion:
    def __init__(self, use_s3=False, address="Helsinki"):
        self.logger = logging.getLogger(__name__)
        self.address = address
        self.use_s3 = use_s3
        if use_s3:
            self.s3_client = boto3.client("s3")
            self.bucket = os.environ.get("AWS_S3_DATA_BUCKET", "air-pollution-data")
        self.logger = logging.getLogger(__name__)

        self.square_side = 20  # km

        self.air_pollution_stations = [
            "Helsinki Kallio 2",
            "Espoo Leppävaara Läkkisepänkuja",
            "Espoo Luukki",
            "Helsinki Mannerheimintie",
            "Vantaa Tikkurila Neilikkatie",
            "Helsinki Vartiokylä Huivipolku",
            "Vantaa Kehä III Viinikkala",
            "Helsinki Kustaa Vaasan tie",
        ]

        self.air_pollution_indicators = [
            "Nitrogen dioxide",
            "Particulate matter < 10 µm",
            "Particulate matter < 2.5 µm",
        ]

    def fetch_pollution_data(
        self, data_type="training", chunk_size_hours=24 * 7, week_number=8
    ):
        """Fetch latest pollution data from APIs (from your notebook logic)"""
        try:
            geolocator = Nominatim(user_agent="ny_explorer")
            location = geolocator.geocode(self.address)
            latitude_city = location.latitude
            longitude_city = location.longitude

            air_pollution_total = {}

            for n in range(week_number):
                start = dt.datetime.now() - (n + 1) * dt.timedelta(
                    hours=chunk_size_hours
                )
                end = dt.datetime.now() - n * dt.timedelta(hours=chunk_size_hours)

                air_pollution_week = get_air_pollution_data_timeInterval(
                    latitude_city,
                    longitude_city,
                    square_side=self.square_side,
                    start=start,
                    end=end,
                )

                air_pollution_week = list(air_pollution_week)[0]

                for key in air_pollution_week.keys():
                    if key not in air_pollution_total.keys():
                        air_pollution_total[key] = air_pollution_week[key]
                    else:
                        air_pollution_total[key] = (
                            air_pollution_total[key] + air_pollution_week[key]
                        )

            df_air_pollution_total = pd.DataFrame()
            # Loop through all air pollution stations
            for station in self.air_pollution_stations:
                merged_df_list = []
                timestamp = []

                # Process data for the current station
                for x in air_pollution_total[station]:
                    df = pd.DataFrame(x.values())

                    # Convert nested values to floats
                    for col in df.columns:
                        if col != "Timestamp":
                            df[col] = df[col].apply(lambda x: x["value"])
                            df[col] = df[col].astype(float)

                    merged_df_list.append(df)
                    timestamp.append(list(x.keys())[0])

                # Combine all data for the current station
                merged_df = pd.concat(merged_df_list, ignore_index=True)
                merged_df["Timestamp"] = timestamp
                merged_df["Timestamp"] = pd.to_datetime(merged_df["Timestamp"])
                # merged_df["Station"] = station

                # Select relevant columns
                merged_df = merged_df[["Timestamp"] + self.air_pollution_indicators]
                merged_df = merged_df.drop_duplicates(subset=["Timestamp"])
                merged_df.sort_values(by="Timestamp", inplace=True)

                ###############
                df_air_pollution = merged_df.copy()

                df_air_pollution = df_air_pollution.rename(
                    columns={
                        "Particulate matter < 10 µm": f"Particulate matter < 10 µm_{station}",
                        "Particulate matter < 2.5 µm": f"Particulate matter < 2.5 µm_{station}",
                        "Nitrogen dioxide": f"Nitrogen dioxide_{station}",
                    }
                )
                if df_air_pollution_total.empty:
                    df_air_pollution_total = df_air_pollution.copy()
                else:
                    df_air_pollution_total = df_air_pollution_total.merge(
                        df_air_pollution, how="outer", on="Timestamp"
                    )  # , suffixes=('', f'_{station}'))

                ## Save to parquet file with station name in the filename
                if self.use_s3:
                    filename = f"training_data/{station.replace(' ', '_')}_air_pollution_data_{data_type}.parquet"
                    self.upload_to_s3(merged_df, filename)

                    print(
                        f"Saved data for station: {station} to {filename}, length: {len(merged_df)} in s3"
                    )
                else:
                    filename = f"{station.replace(' ', '_')}_air_pollution_data_{data_type}.parquet"
                    full_path = os.path.join(RAW_DATA_DIR, filename)

                    merged_df.to_parquet(full_path, index=False)
                    print(
                        f"Saved data for station: {station} to {filename}, length: {len(merged_df)} in {full_path}"
                    )

        except Exception as e:
            self.logger.error(f"Failed to fetch data: {e}")
            raise

        ## Save to parquet file with station name in the filename
        if self.use_s3:
            filename = f"{data_type}_data/air_pollution_data_{data_type}_total.parquet"
            self.upload_to_s3(df_air_pollution_total, filename)
            print(f"Saved total data: to {filename}, length: {len(merged_df)} in s3")

        else:
            filename = f"air_pollution_data_{data_type}_total.parquet"
            full_path = os.path.join(INTERIM_DATA_DIR, filename)

            df_air_pollution_total.to_parquet(full_path, index=False)
            print(
                f"Saved total data: to {filename}, length: {len(merged_df)} in {full_path}"
            )

    def upload_to_s3(self, df, key):
        """Upload DataFrame to S3 as parquet file"""
        try:
            s3_client = boto3.client("s3")
            session = boto3.Session()
            credentials = session.get_credentials()

            bucket = os.environ.get("AWS_S3_BUCKET_NAME", "air-pollution-models")
            bucket = bucket.replace("s3://", "").strip()

            # print(credentials.access_key, credentials.secret_key, credentials.token)
            # print(f"Uploading data to s3://{bucket}/{key}")
            # Convert DataFrame to parquet in memory
            buffer = io.BytesIO()
            df.to_parquet(buffer, index=False)
            buffer.seek(0)

            s3_client.put_object(
                Bucket=bucket,
                Key=key,
                Body=buffer.getvalue(),
                ContentType="application/octet-stream",
            )

            self.logger.info(f"Uploaded data to s3://{bucket}/{key}")
        except Exception as e:
            self.logger.error(f"Failed to upload data to S3: {e}")
            raise

    def merge_and_save_data_local(self):
        # Loop through all air pollution stations
        df_air_pollution_total = pd.DataFrame()

        for station in self.air_pollution_stations:
            # Generate the filename for the station
            filename = f"{station.replace(' ', '_')}_air_pollution_data.parquet"
            full_path = os.path.join(RAW_DATA_DIR, filename)

            # Load the air pollution dataset for the station
            if os.path.exists(full_path):
                df_air_pollution = pd.read_parquet(full_path)
                df_air_pollution["Timestamp"] = pd.to_datetime(
                    df_air_pollution["Timestamp"]
                )

                # df_air_pollution.ffill(inplace=True)
                # df_air_pollution.bfill(inplace=True)

                print(f"Loaded data for station: {station}")

                df_air_pollution = df_air_pollution[
                    [
                        "Timestamp",
                        "Particulate matter < 10 µm",
                        "Particulate matter < 2.5 µm",
                        "Nitrogen dioxide",
                    ]
                ]

                df_air_pollution = df_air_pollution.rename(
                    columns={
                        "Particulate matter < 10 µm": f"Particulate matter < 10 µm_{station}",
                        "Particulate matter < 2.5 µm": f"Particulate matter < 2.5 µm_{station}",
                        "Nitrogen dioxide": f"Nitrogen dioxide_{station}",
                    }
                )

                if df_air_pollution_total.empty:
                    df_air_pollution_total = df_air_pollution.copy()
                else:
                    df_air_pollution_total = df_air_pollution_total.merge(
                        df_air_pollution, how="outer", on="Timestamp"
                    )  # , suffixes=('', f'_{station}'))

            else:
                print(f"File not found for station: {station}")
                continue

        df_air_pollution_total.to_parquet(
            os.path.join(INTERIM_DATA_DIR, "air_pollution_data_total.parquet"),
            index=False,
        )

    def _clean_and_standardize(self, df):
        """Clean and standardize the collected data"""
        # Remove duplicates
        df = df.drop_duplicates(subset=["Timestamp", "Station"])

        # Sort by timestamp
        df = df.sort_values("Timestamp")

        # Handle missing values
        numeric_columns = df.select_dtypes(include=["float64", "int64"]).columns
        for col in numeric_columns:
            # Forward fill missing values (or use your preferred method)
            df[col] = df[col].fillna(method="ffill")

        # Ensure timestamp is timezone aware
        if df["Timestamp"].dt.tz is None:
            df["Timestamp"] = df["Timestamp"].dt.tz_localize("Europe/Helsinki")

        return df

    def _save_latest_data(self, df):
        """Save latest data to file"""
        os.makedirs(INTERIM_DATA_DIR, exist_ok=True)

        # Save with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"latest_pollution_data_{timestamp}.parquet"
        filepath = os.path.join(INTERIM_DATA_DIR, filename)

        df.to_parquet(filepath, index=False)

        # Also save as 'latest.parquet' for easy access
        latest_filepath = os.path.join(
            INTERIM_DATA_DIR, "latest_pollution_data.parquet"
        )
        df.to_parquet(latest_filepath, index=False)

        self.logger.info(f"Saved latest data to {filepath}")
