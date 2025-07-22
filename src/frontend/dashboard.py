from datetime import datetime, timedelta

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import streamlit as st

# Frontend app
st.set_page_config(page_title="Air Pollution Predictor", page_icon="🌍", layout="wide")


class AirPollutionDashboard:
    def __init__(self):
        import os

        self.api_base_url = os.getenv("API_BASE_URL", "http://localhost:8000/api/v1")

        # Station coordinates from your data collection
        self.station_coordinates = {
            "Helsinki Kallio 2": {"lat": 60.1878, "lon": 24.9508},
            "Espoo Leppävaara Läkkisepänkuja": {"lat": 60.2191, "lon": 24.8130},
            "Espoo Luukki": {"lat": 60.1625, "lon": 24.6683},
            "Helsinki Mannerheimintie": {"lat": 60.1699, "lon": 24.9384},
            "Vantaa Tikkurila Neilikkatie": {"lat": 60.2925, "lon": 25.0442},
            "Helsinki Vartiokylä Huivipolku": {"lat": 60.2243, "lon": 25.1040},
            "Vantaa Kehä III Viinikkala": {"lat": 60.2708, "lon": 24.8875},
            "Helsinki Kustaa Vaasan tie": {"lat": 60.1985, "lon": 24.9675},
        }

    def check_api_health(self):
        """Check if API is running"""
        try:
            response = requests.get(f"{self.api_base_url}/health", timeout=5)
            return response.status_code == 200
        except Exception as e:
            st.write(f"🔍 DEBUG: API connection error: {e}")
            return False

    def get_model_info(self):
        """Get current model information"""
        try:
            response = requests.get(f"{self.api_base_url}/model/info")
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            st.write(f"🔍 DEBUG: Model info error: {e}")
        return None

    def train_model(self):
        """Trigger model training"""
        try:
            response = requests.get(f"{self.api_base_url}/train")
            return response.json() if response.status_code == 200 else None
        except Exception as e:
            st.error(f"Training failed: {e}")
            return None

    def get_predictions(self, fetch_fresh=True):
        """Get pollution predictions"""
        try:
            url = f"{self.api_base_url}/predict"
            if fetch_fresh:
                url += "?fetch_fresh_data=true"

            response = requests.get(url)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            st.error(f"Prediction failed: {e}")
        return None

    def get_data_status(self):
        """Get data availability status"""
        try:
            response = requests.get(f"{self.api_base_url}/data/status")
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            st.error(f"Failed to get data status: {e}")
        return None

    def refresh_prediction_data(self):
        """Refresh prediction data"""
        try:
            response = requests.post(f"{self.api_base_url}/data/refresh")
            return response.json() if response.status_code == 200 else None
        except Exception as e:
            st.error(f"Data refresh failed: {e}")
        return None

    def collect_training_data(self, week_number=2):
        """Collect training data"""
        try:
            url = f"{self.api_base_url}/data/collect/training"
            chunk_size_hours = 24 * 7  # Fixed to 1 week chunks
            params = {
                "chunk_size_hours": chunk_size_hours,
                "week_number": week_number,
                "force_refresh": True,
            }
            response = requests.get(url, params=params)
            return response.json() if response.status_code == 200 else None
        except Exception as e:
            st.error(f"Training data collection failed: {e}")
        return None

    def collect_weather_data(self):
        """Weather data collection removed - not needed"""
        return None

    def get_latest_station_data(self):
        """Get latest data from all stations (simulated from your notebook logic)"""
        latest_data = {}
        for station, coords in self.station_coordinates.items():
            latest_data[station] = {
                "Latitude": coords["lat"],
                "Longitude": coords["lon"],
                "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "Nitrogen monoxide": f"{20 + hash(station) % 30:.1f}",
                "Nitrogen dioxide": f"{15 + hash(station) % 25:.1f}",
                "Particulate matter < 10 µm": f"{25 + hash(station) % 20:.1f}",
                "Particulate matter < 2.5 µm": f"{12 + hash(station) % 15:.1f}",
            }
        return latest_data

    def render_dashboard(self):
        """Render the main dashboard"""
        st.title("🌍 Air Pollution Prediction Dashboard")

        # Sidebar
        st.sidebar.title("Controls")

        # API Health Check
        if self.check_api_health():
            st.sidebar.success("✅ API is running")
        else:
            st.sidebar.error("❌ API is not accessible")
            st.error(
                "❌ Cannot connect to API. Please ensure the FastAPI server is running on http://localhost:8000"
            )
            return

        # Main content
        tab1, tab2, tab3, tab4, tab5 = st.tabs(
            [
                "📊 Predictions",
                "🗺️ Station Map",
                "📥 Data Collection",
                "🤖 Model Training",
                "ℹ️ Model Info",
            ]
        )

        with tab1:
            self.render_predictions_tab()

        with tab2:
            self.render_map_tab()

        with tab3:
            self.render_data_collection_tab()

        with tab4:
            self.render_training_tab()

        with tab5:
            self.render_model_info_tab()

    def render_predictions_tab(self):
        """Render predictions tab with enhanced plotting"""
        st.header("🔮 Air Pollution Predictions")

        col1, col2 = st.columns([3, 1])

        with col2:
            if st.button("🔄 Get New Predictions", type="primary", key="pred_button"):
                with st.spinner("Generating predictions..."):
                    predictions = self.get_predictions()
                    if predictions:
                        st.session_state["predictions"] = predictions
                        st.success("✅ Predictions updated!")
                    else:
                        st.error("❌ Failed to get predictions")

        # Display predictions if available
        if "predictions" in st.session_state:
            predictions = st.session_state["predictions"]

            st.subheader("📈 Prediction Visualization")
            self.plot_predictions(predictions)

            # Show raw data in expander
            with st.expander("🔍 Raw Prediction Data"):
                st.json(predictions)

        else:
            st.info("👆 Click 'Get New Predictions' to see pollution forecasts")

            # Show sample visualization
            st.subheader("📊 Sample Prediction Chart")
            sample_data = self.create_sample_prediction_data()
            self.plot_sample_predictions(sample_data)

    def create_sample_prediction_data(self):
        """Create sample prediction data matching the real API format"""
        base_time = datetime.now()

        # Create sample data matching the real API format (pollutant_station as key)
        sample_predictions = {}
        sample_historical = {}

        pollutants = ["Nitrogen dioxide", "PM10", "PM2.5"]
        stations = [
            "Helsinki Kallio 2",
            "Espoo Leppävaara Läkkisepänkuja",
            "Helsinki Mannerheimintie",
        ]

        for pollutant in pollutants:
            for station in stations:
                # Create the key in the format "pollutant_station"
                key = f"{pollutant}_{station}"

                # Predictions for each pollutant-station combination
                sample_predictions[key] = {}
                for hour in range(1, 7):  # 6 hours
                    timestamp = base_time + timedelta(hours=hour)
                    # Vary values by station and pollutant
                    base_value = (
                        15 + hour * 2 + (hash(pollutant) % 10) + (hash(station) % 8)
                    )

                    sample_predictions[key][f"hour_{hour}"] = {
                        "value": base_value,
                        "timestamp": timestamp.isoformat(),
                    }

                # Historical data for each pollutant-station combination
                sample_historical[key] = []
                for hour in range(-24, 0):  # Last 24 hours
                    timestamp = base_time + timedelta(hours=hour)
                    base_value = (
                        20
                        + abs(hour) * 0.5
                        + (hash(pollutant) % 8)
                        + (hash(station) % 6)
                    )

                    sample_historical[key].append(
                        {"value": base_value, "timestamp": timestamp.isoformat()}
                    )

        return {
            "prediction_timestamp": base_time.isoformat(),
            "predictions": sample_predictions,
            "historical_data": sample_historical,
        }

    def plot_sample_predictions(self, sample_data):
        """Plot sample predictions"""
        st.info("This is sample data. Click 'Get New Predictions' for real forecasts.")
        self.plot_predictions(sample_data)

    def render_training_tab(self):
        """Render model training tab"""
        st.header("🤖 Model Training")

        col1, col2 = st.columns([2, 1])

        with col1:
            st.write("Train a new model with the latest available data.")

            if st.button("🚀 Train Model", type="primary"):
                with st.spinner("Training model... This may take a few minutes"):
                    result = self.train_model()
                    if result:
                        st.success("✅ Model trained successfully!")
                        st.json(result)
                    else:
                        st.error("❌ Training failed")

        with col2:
            st.info(
                """
            **Training Process:**
            1. Loads training data
            2. Trains Lasso regression model
            3. Saves model to MLflow
            4. Updates model in memory
            """
            )

    def render_model_info_tab(self):  # noqa: C901
        """Render model information tab"""
        st.header("Model Information")

        model_info = self.get_model_info()

        if model_info:
            # Model Status Section
            col1, col2 = st.columns(2)

            with col1:
                st.subheader("🤖 Model Status")
                model_loaded = model_info.get("model_loaded", False)
                if model_loaded:
                    st.success("✅ Model is loaded and ready")
                else:
                    st.warning("⚠️ No model loaded")

                st.write(f"**Model Type:** {model_info.get('model_type', 'Unknown')}")
                st.write(
                    f"**Training Hours:** {model_info.get('historical_feature_hours', 'Unknown')}"
                )
                st.write(
                    f"**Prediction Hours:** {model_info.get('prediction_hours', 'Unknown')}"
                )

                # Target features
                target_features = model_info.get("target_features", [])
                if target_features:
                    st.write(f"**Target Features:** {len(target_features)}")
                    with st.expander("View Features"):
                        for feature in target_features:
                            st.write(f"• {feature}")

            with col2:
                st.subheader("📊 Model Performance Metrics")

                metrics = model_info.get("metrics", {})

                # Display metrics in a nice format
                if metrics.get("error"):
                    st.error(f"❌ {metrics['error']}")
                else:
                    col_r2, col_rmse = st.columns(2)

                    with col_r2:
                        r2_score = metrics.get("r2_score")
                        if r2_score is not None:
                            # Color code R2 score
                            color = "normal"
                            if r2_score > 0.8:
                                color = "normal"
                            elif r2_score > 0.6:
                                color = "normal"
                            else:
                                color = "inverse"
                            st.metric("R² Score", f"{r2_score:.4f}", delta_color=color)
                        else:
                            st.metric("R² Score", "N/A")

                    with col_rmse:
                        rmse = metrics.get("rmse")
                        if rmse is not None:
                            st.metric("RMSE", f"{rmse:.3f} μg/m³")
                        else:
                            st.metric("RMSE", "N/A")

                    col_mae, col_mse = st.columns(2)

                    with col_mae:
                        mae = metrics.get("mae")
                        if mae is not None:
                            st.metric("MAE", f"{mae:.3f} μg/m³")
                        else:
                            st.metric("MAE", "N/A")

                    with col_mse:
                        mse = metrics.get("mse")
                        if mse is not None:
                            st.metric("MSE", f"{mse:.3f}")
                        else:
                            st.metric("MSE", "N/A")

            # Model Metadata Section
            model_metadata = model_info.get("model_metadata", {})
            if model_metadata:
                st.subheader("🔍 Model Metadata")

                col1, col2, col3 = st.columns(3)

                with col1:
                    run_id = model_metadata.get("run_id", "N/A")
                    st.write(
                        f"**Run ID:** `{run_id[:8]}...`"
                        if len(run_id) > 8
                        else f"**Run ID:** `{run_id}`"
                    )

                    model_version = model_metadata.get("model_version", "N/A")
                    st.write(f"**Model Version:** {model_version}")

                with col2:
                    training_samples = model_metadata.get("training_samples")
                    if training_samples:
                        st.write(f"**Training Samples:** {int(training_samples)}")

                    validation_samples = model_metadata.get("validation_samples")
                    if validation_samples:
                        st.write(f"**Validation Samples:** {int(validation_samples)}")

                with col3:
                    creation_time = model_metadata.get("creation_time")
                    if creation_time:
                        # Convert timestamp to readable date
                        try:
                            import datetime

                            dt = datetime.datetime.fromtimestamp(creation_time / 1000)
                            st.write(f"**Created:** {dt.strftime('%Y-%m-%d %H:%M')}")
                        except Exception as e:
                            st.write(f"**Created:** {creation_time}")
                            print(f"Error parsing creation time: {e}")
            # Performance Interpretation
            if metrics and not metrics.get("error"):
                st.subheader("📈 Performance Interpretation")

                r2_score = metrics.get("r2_score")
                rmse = metrics.get("rmse")

                if r2_score is not None:
                    if r2_score > 0.8:
                        st.success(
                            f"🟢 **Excellent Model Performance** (R² = {r2_score:.3f})"
                        )
                        st.write(
                            "The model explains more than 80% of the variance in pollution levels."
                        )
                    elif r2_score > 0.6:
                        st.warning(
                            f"🟡 **Good Model Performance** (R² = {r2_score:.3f})"
                        )
                        st.write(
                            "The model explains 60-80% of the variance. Consider feature engineering."
                        )
                    elif r2_score > 0.4:
                        st.warning(
                            f"🟠 **Fair Model Performance** (R² = {r2_score:.3f})"
                        )
                        st.write(
                            "The model explains 40-60% of the variance. Significant improvement needed."
                        )
                    else:
                        st.error(f"🔴 **Poor Model Performance** (R² = {r2_score:.3f})")
                        st.write(
                            "The model explains less than 40% of the variance. Model retraining recommended."
                        )

                if rmse is not None:
                    st.info(
                        f"**RMSE:** {rmse:.3f} μg/m³ - Average prediction error magnitude"
                    )

            # Raw model info in expander
            with st.expander("🔍 Raw Model Information"):
                st.json(model_info)

        else:
            st.warning("⚠️ No model information available.")
            st.info("💡 **Next Steps:**")
            st.write("1. Train a model using the '🤖 Model Training' tab")
            st.write("2. Ensure the API is running and accessible")
            st.write("3. Check if MLflow is properly configured")

    # MAP FUNCTIONS
    def create_plotly_map(self, station_data=None):
        """Create a Plotly map with station locations"""

        if station_data is None:
            station_data = self.get_latest_station_data()

        # Prepare data for plotting
        map_data = []
        for station_name, info in station_data.items():
            pm10_value = float(info.get("Particulate matter < 10 µm", 25))
            pm25_value = float(info.get("Particulate matter < 2.5 µm", 15))

            map_data.append(
                {
                    "Station": station_name,
                    "Latitude": info["Latitude"],
                    "Longitude": info["Longitude"],
                    "PM10": pm10_value,
                    "PM2.5": pm25_value,
                    "NO2": float(info.get("Nitrogen dioxide", 20)),
                    "Timestamp": info["Timestamp"],
                    "Color": self.get_pollution_color(pm10_value),
                    "Size": max(
                        10, min(30, pm10_value)
                    ),  # Size based on pollution level
                }
            )

        df_map = pd.DataFrame(map_data)

        # Create scatter mapbox
        fig = px.scatter_mapbox(
            df_map,
            lat="Latitude",
            lon="Longitude",
            hover_name="Station",
            hover_data={
                "PM10": ":.1f",
                "PM2.5": ":.1f",
                "NO2": ":.1f",
                "Timestamp": True,
                "Latitude": False,
                "Longitude": False,
            },
            color="PM10",
            size="Size",
            color_continuous_scale="RdYlGn_r",  # Red-Yellow-Green reversed
            size_max=25,
            zoom=9,
            height=600,
            title="Air Quality Monitoring Stations",
        )

        # Update layout
        fig.update_layout(
            mapbox_style="open-street-map",
            margin={"r": 0, "t": 50, "l": 0, "b": 0},
            coloraxis_colorbar=dict(
                title="PM10 (μg/m³)"
            ),  # <-- FIXED: removed titleside
        )

        return fig

    def get_pollution_color(self, pm10_value):
        """Get color based on PM10 pollution level"""
        if pm10_value > 50:
            return "red"
        elif pm10_value > 30:
            return "orange"
        elif pm10_value > 20:
            return "yellow"
        else:
            return "green"

    def render_map_tab(self):
        """Render map tab with Plotly map"""
        st.header("🗺️ Monitoring Stations Map")

        col1, col2 = st.columns([3, 1])

        with col2:
            if st.button("🔄 Refresh Station Data", type="secondary"):
                st.session_state["station_data_refreshed"] = datetime.now()

        # Get latest station data
        station_data = self.get_latest_station_data()

        # Create and display Plotly map
        st.subheader("📍 Air Quality Monitoring Stations")
        plotly_map = self.create_plotly_map(station_data)
        st.plotly_chart(plotly_map, use_container_width=True)

        # Station summary
        st.subheader("📊 Station Summary")
        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("Total Stations", len(station_data))
        with col2:
            st.metric("Active Stations", len(station_data))
        with col3:
            avg_pm10 = sum(
                float(data.get("Particulate matter < 10 µm", 0))
                for data in station_data.values()
            ) / len(station_data)
            st.metric("Avg PM10", f"{avg_pm10:.1f} μg/m³")

    # PREDICTION PLOTTING FUNCTIONS
    def plot_predictions(self, predictions_data):  # noqa: C901
        """Create prediction plots with historical context"""

        if not predictions_data or "predictions" not in predictions_data:
            st.error("No prediction data available")
            return

        predictions = predictions_data["predictions"]
        historical_data = predictions_data.get("historical_data", {})
        prediction_timestamp = predictions_data.get(
            "prediction_timestamp", datetime.now().isoformat()
        )

        st.info(
            f"🕐 Predictions generated at: {pd.to_datetime(prediction_timestamp).strftime('%Y-%m-%d %H:%M:%S')}"
        )

        try:
            # Parse predictions into DataFrame
            predicted_data = []
            for pollutant_station_key, hourly_data in predictions.items():
                # Parse pollutant and station from the key (format: "Pollutant_Station")
                if "_" in pollutant_station_key:
                    parts = pollutant_station_key.split(
                        "_", 1
                    )  # Split only on first underscore
                    pollutant = parts[0]
                    station = parts[1]
                else:
                    # Fallback if format is different
                    pollutant = pollutant_station_key
                    station = "Unknown Station"

                for hour_key, prediction_info in hourly_data.items():
                    predicted_data.append(
                        {
                            "timestamp": prediction_info["timestamp"],
                            "pollutant": pollutant,
                            "value": prediction_info["value"],
                            "hour": hour_key,
                            "station": station,
                        }
                    )

            df_predictions = pd.DataFrame(predicted_data)

            # Parse historical data into DataFrame
            df_historical = None
            if historical_data:
                historical_parsed = []
                for pollutant_station_key, data_points in historical_data.items():
                    # Parse pollutant and station from the key
                    if "_" in pollutant_station_key:
                        parts = pollutant_station_key.split("_", 1)
                        pollutant = parts[0]
                        station = parts[1]
                    else:
                        # If no station in key, this might be historical data without station names
                        pollutant = pollutant_station_key
                        # Try to infer station from prediction data structure
                        station = "Helsinki Kallio 2"  # Default to first station

                    for data_point in data_points:
                        historical_parsed.append(
                            {
                                "timestamp": data_point["timestamp"],
                                "pollutant": pollutant,
                                "value": data_point["value"],
                                "station": station,
                            }
                        )

                if historical_parsed:
                    df_historical = pd.DataFrame(historical_parsed)
                    # Fix timestamp conversion with error handling
                    try:
                        df_historical["timestamp"] = pd.to_datetime(
                            df_historical["timestamp"], errors="coerce"
                        )
                        # Remove any rows with invalid timestamps
                        df_historical = df_historical.dropna(subset=["timestamp"])
                    except Exception as e:
                        st.warning(f"Issue with historical timestamp conversion: {e}")
                        df_historical = None

            if df_predictions.empty:
                st.error("No prediction data to plot")
                return

            # Convert timestamp to datetime with error handling
            try:
                df_predictions["timestamp"] = pd.to_datetime(
                    df_predictions["timestamp"], errors="coerce"
                )
                # Remove any rows with invalid timestamps
                df_predictions = df_predictions.dropna(subset=["timestamp"])
                df_predictions = df_predictions.sort_values("timestamp")
            except Exception as e:
                st.error(f"Error converting prediction timestamps: {e}")
                return

            if df_predictions.empty:
                st.error("No valid prediction data after timestamp conversion")
                return

            # Show overview
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                historical_count = (
                    len(df_historical) if df_historical is not None else 0
                )
                st.metric("📈 Historical Points", historical_count)
            with col2:
                predicted_count = len(df_predictions)
                st.metric("🔮 Predicted Points", predicted_count)
            with col3:
                pollutant_count = df_predictions["pollutant"].nunique()
                st.metric("🌫️ Pollutants", pollutant_count)
            with col4:
                station_count = (
                    df_predictions["station"].nunique()
                    if "station" in df_predictions.columns
                    else 1
                )
                st.metric("🏢 Stations", station_count)

            # Debug information for historical data
            if df_historical is None:
                st.info("ℹ️ No historical data available in API response")
            elif df_historical.empty:
                st.info("ℹ️ Historical data DataFrame is empty after processing")
            else:
                # Show historical data summary
                hist_pollutants = df_historical["pollutant"].unique()
                hist_stations = (
                    df_historical["station"].unique()
                    if "station" in df_historical.columns
                    else []
                )
                st.success(
                    f"✅ Historical data loaded: {len(hist_pollutants)} pollutants, {len(hist_stations)} stations"
                )

            # Visualization options
            viz_option = st.selectbox(
                "Choose visualization:",
                ["Combined View", "By Pollutant", "Comparison View"],
                index=1,  # Default to "By Pollutant"
            )

            if viz_option == "Combined View":
                self.plot_combined_with_history_separate(df_predictions, df_historical)
            elif viz_option == "By Pollutant":
                self.plot_by_pollutant_with_history(df_predictions, df_historical)
            else:
                self.plot_comparison_view_separate(df_predictions, df_historical)

            # Summary statistics
            self.show_enhanced_summary_separate(
                df_predictions, df_historical, pd.to_datetime(prediction_timestamp)
            )

            # Data table
            with st.expander("📋 Detailed Data Table"):
                col1, col2 = st.columns(2)

                with col1:
                    st.write("**Predictions:**")
                    display_pred = df_predictions.copy()
                    display_pred["timestamp"] = display_pred["timestamp"].dt.strftime(
                        "%Y-%m-%d %H:%M"
                    )
                    display_pred["value"] = display_pred["value"].round(2)
                    # Show relevant columns
                    columns_to_show = ["timestamp", "pollutant", "station", "value"]
                    display_columns = [
                        col for col in columns_to_show if col in display_pred.columns
                    ]
                    st.dataframe(
                        display_pred[display_columns],
                        use_container_width=True,
                        # hide_index=True,
                    )

                with col2:
                    if df_historical is not None and not df_historical.empty:
                        st.write("**Historical:**")
                        display_hist = df_historical.copy()
                        display_hist["timestamp"] = display_hist[
                            "timestamp"
                        ].dt.strftime("%Y-%m-%d %H:%M")
                        display_hist["value"] = display_hist["value"].round(2)
                        # Show relevant columns
                        columns_to_show = ["timestamp", "pollutant", "station", "value"]
                        # display_columns = [
                        #    col
                        #    for col in columns_to_show
                        #    if col in display_hist.columns
                        # ]
                        # st.dataframe(
                        #     display_hist[display_columns],
                        #     use_container_width=True
                        #     #hide_index=True,
                        # )
                    else:
                        st.write("**No historical data available**")

        except Exception as e:
            st.error(f"Error plotting predictions: {e}")
            with st.expander("🔍 Debug Information"):
                st.write("Exception details:", str(e))
                st.json(predictions_data)

    def plot_combined_with_history_separate(self, df_predictions, df_historical=None):
        """Plot combined view with multiple stations for all pollutants"""
        st.subheader("🔮 All Pollutants & Stations - Combined View")

        fig = go.Figure()

        pollutants = df_predictions["pollutant"].unique()
        stations = (
            df_predictions["station"].unique()
            if "station" in df_predictions.columns
            else ["Unknown Station"]
        )

        # Create a color mapping for pollutant-station combinations
        color_palette = (
            px.colors.qualitative.Set1
            + px.colors.qualitative.Set2
            + px.colors.qualitative.Set3
        )
        color_index = 0

        for pollutant in pollutants:
            for station in stations:
                color = color_palette[color_index % len(color_palette)]
                color_index += 1

                # Historical data (if available)
                if (
                    df_historical is not None
                    and not df_historical.empty
                    and "station" in df_historical.columns
                ):
                    hist_data = df_historical[
                        (df_historical["pollutant"] == pollutant)
                        & (df_historical["station"] == station)
                    ].sort_values("timestamp")

                    if not hist_data.empty:
                        fig.add_trace(
                            go.Scatter(
                                x=hist_data["timestamp"],
                                y=hist_data["value"],
                                mode="lines+markers",
                                name=f"{pollutant} - {station} (Hist)",
                                line=dict(color=color, dash="dash", width=1.5),
                                marker=dict(size=3, symbol="circle"),
                                hovertemplate=f"<b>{pollutant} - {station} (Historical)</b><br>"
                                + "Time: %{x}<br>"
                                + "Value: %{y:.2f} μg/m³<extra></extra>",
                                opacity=0.7,
                            )
                        )

                # Predicted data
                pred_data = df_predictions[
                    (df_predictions["pollutant"] == pollutant)
                    & (df_predictions["station"] == station)
                ].sort_values("timestamp")

                if not pred_data.empty:
                    fig.add_trace(
                        go.Scatter(
                            x=pred_data["timestamp"],
                            y=pred_data["value"],
                            mode="lines+markers",
                            name=f"{pollutant} - {station} (Pred)",
                            line=dict(color=color, width=2.5),
                            marker=dict(size=6, symbol="diamond"),
                            hovertemplate=f"<b>{pollutant} - {station} (Predicted)</b><br>"
                            + "Time: %{x}<br>"
                            + "Value: %{y:.2f} μg/m³<extra></extra>",
                        )
                    )

        # Add vertical line at prediction start with error handling
        if not df_predictions.empty:
            try:
                # Ensure we get a proper Timestamp object
                prediction_start = pd.Timestamp(df_predictions["timestamp"].iloc[0])
                if pd.notna(prediction_start):
                    fig.add_vline(
                        x=prediction_start,
                        line_dash="dot",
                        line_color="red",
                        annotation_text="Prediction Start",
                        annotation_position="top",
                    )
            except Exception as e:
                st.write(f"Warning: Could not add prediction start line: {e}")

        fig.update_layout(
            title="🌍 Air Pollution: All Pollutants & Stations",
            xaxis_title="Time",
            yaxis_title="Concentration (μg/m³)",
            hovermode="x unified",
            height=700,
            showlegend=True,
            legend=dict(
                orientation="v",
                yanchor="top",
                y=1,
                xanchor="left",
                x=1.01,
                font=dict(size=10),
            ),
        )

        st.plotly_chart(fig, use_container_width=True)

        # Show summary of stations and pollutants
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("🌫️ Pollutants", len(pollutants))
        with col2:
            st.metric("🏢 Stations", len(stations))
        with col3:
            total_series = len(pollutants) * len(stations)
            st.metric("📊 Total Series", total_series)

    def plot_by_pollutant_with_history(
        self, df_predictions, df_historical=None
    ):  # noqa: C901
        """Plot each pollutant separately with multiple stations combined on the same panel"""

        # Get all pollutants from both datasets
        pollutants = set(df_predictions["pollutant"].unique())
        if df_historical is not None and not df_historical.empty:
            pollutants.update(df_historical["pollutant"].unique())

        # Color palette for stations
        station_colors = px.colors.qualitative.Set1

        # print(pollutants)

        for pollutant in sorted(pollutants, reverse=True):
            # print("Plotting pollutant:", pollutant)
            st.subheader(f"🌫️ {pollutant} - All Stations")

            fig = go.Figure()

            # Get all stations for this pollutant
            pred_stations = set()
            hist_stations = set()

            if not df_predictions.empty:
                pred_data_pollutant = df_predictions[
                    df_predictions["pollutant"] == pollutant
                ]
                pred_stations = set(pred_data_pollutant["station"].unique())

            if df_historical is not None and not df_historical.empty:
                hist_data_pollutant = df_historical[
                    df_historical["pollutant"] == pollutant
                ]
                hist_stations = set(hist_data_pollutant["station"].unique())

            all_stations = sorted(pred_stations.union(hist_stations))

            if not all_stations:
                st.warning(f"No station data available for {pollutant}")
                continue

            # Plot data for each station
            for i, station in enumerate(all_stations):
                color = station_colors[i % len(station_colors)]

                # Historical data for this station
                if df_historical is not None and not df_historical.empty:
                    hist_data = df_historical[
                        (df_historical["pollutant"] == pollutant)
                        & (df_historical["station"] == station)
                    ].sort_values("timestamp")

                    if not hist_data.empty:
                        fig.add_trace(
                            go.Scatter(
                                x=hist_data["timestamp"],
                                y=hist_data["value"],
                                mode="lines+markers",
                                name=f"{station} (Historical)",
                                line=dict(color=color, dash="dash", width=2),
                                marker=dict(size=4, color=color, symbol="circle"),
                                hovertemplate=f"<b>{station} - Historical</b><br>"
                                + "Time: %{x}<br>"
                                + "Value: %{y:.2f} μg/m³<extra></extra>",
                                showlegend=True,
                            )
                        )

                # Predicted data for this station
                if not df_predictions.empty:
                    pred_data = df_predictions[
                        (df_predictions["pollutant"] == pollutant)
                        & (df_predictions["station"] == station)
                    ].sort_values("timestamp")

                    if not pred_data.empty:
                        fig.add_trace(
                            go.Scatter(
                                x=pred_data["timestamp"],
                                y=pred_data["value"],
                                mode="lines+markers",
                                name=f"{station} (Predicted)",
                                line=dict(color=color, width=3),
                                marker=dict(size=8, color=color, symbol="diamond"),
                                hovertemplate=f"<b>{station} - Predicted</b><br>"
                                + "Time: %{x}<br>"
                                + "Value: %{y:.2f} μg/m³<extra></extra>",
                                showlegend=True,
                            )
                        )

            # Add prediction start line with error handling
            if not df_predictions.empty:
                try:
                    # Use iloc[0] instead of min() to avoid timestamp arithmetic issues
                    pollutant_data = df_predictions[
                        df_predictions["pollutant"] == pollutant
                    ]
                    if not pollutant_data.empty:
                        prediction_start = pd.Timestamp(
                            pollutant_data["timestamp"].iloc[0]
                        )
                        if pd.notna(prediction_start):
                            fig.add_vline(
                                x=prediction_start,
                                line_dash="dot",
                                line_color="gray",
                                annotation_text="Prediction Start",
                                annotation_position="top",
                            )
                except Exception as e:
                    st.write(
                        f"Warning: Could not add prediction start line for {pollutant}: {e}"
                    )

            # print(f"Plotting {pollutant} for {len(all_stations)} stations")

            fig.update_layout(
                title=f"{pollutant} - All Monitoring Stations",
                xaxis_title="Time",
                yaxis_title="Concentration (μg/m³)",
                hovermode="x unified",
                height=500,
                legend=dict(
                    orientation="v", yanchor="top", y=1, xanchor="left", x=1.01
                ),
            )

            # print(f"Plotting {pollutant} for {len(all_stations)} stations end")

            st.plotly_chart(fig, use_container_width=True)

            # print(f"Plotting {pollutant} for {len(all_stations)} stations end")

            # Show station summary for this pollutant
            if not df_predictions.empty:
                st.write(f"**Stations with data for {pollutant}:** {len(all_stations)}")

                # Create summary table for this pollutant
                summary_data = []

                for station in all_stations:
                    # print(f"Processing station: {station} for pollutant: {pollutant}")
                    pred_station_data = df_predictions[
                        (df_predictions["pollutant"] == pollutant)
                        & (df_predictions["station"] == station)
                    ]

                    # print(f"Processing station: {station} for pollutant: {pollutant}")

                    if not pred_station_data.empty:
                        avg_pred = pred_station_data["value"].mean()
                        max_pred = pred_station_data["value"].max()
                        min_pred = pred_station_data["value"].min()

                        summary_data.append(
                            {
                                "Station": station,
                                "Avg Predicted": f"{avg_pred:.1f}",
                                "Max Predicted": f"{max_pred:.1f}",
                                "Min Predicted": f"{min_pred:.1f}",
                            }
                        )

                    # print(f"Processing station: {station} for pollutant: {pollutant} end")

                if summary_data:
                    pass
                    # print(f"Adding summary for pollutant: {pollutant} start")
                    # df_summary = pd.DataFrame(summary_data)
                    # st.dataframe(df_summary, use_container_width=True, hide_index=True)
                    # st.dataframe(df_summary, use_container_width=True)
                    # print(f"Adding summary for pollutant: {pollutant} end")

    def plot_comparison_view_separate(self, df_predictions, df_historical):
        """Plot comparison between historical trends and predictions"""
        st.subheader("📊 Historical vs Predicted Comparison")

        if df_historical is None or df_historical.empty:
            st.warning("No historical data available for comparison")
            return

        pollutants = df_predictions["pollutant"].unique()

        # Create subplots
        cols = st.columns(min(len(pollutants), 2))

        for idx, pollutant in enumerate(pollutants):
            with cols[idx % 2]:
                pred_data = df_predictions[df_predictions["pollutant"] == pollutant]
                hist_data = df_historical[df_historical["pollutant"] == pollutant]

                if not hist_data.empty and not pred_data.empty:
                    hist_avg = hist_data["value"].mean()
                    pred_avg = pred_data["value"].mean()

                    # Create comparison chart
                    fig = go.Figure()

                    categories = ["Historical Avg", "Predicted Avg"]
                    values = [hist_avg, pred_avg]
                    colors = ["lightblue", "lightcoral"]

                    fig.add_trace(
                        go.Bar(
                            x=categories,
                            y=values,
                            marker_color=colors,
                            text=[f"{v:.1f}" for v in values],
                            textposition="auto",
                        )
                    )

                    # Calculate trend
                    change = pred_avg - hist_avg
                    change_pct = (change / hist_avg * 100) if hist_avg != 0 else 0

                    fig.update_layout(
                        title=f"{pollutant}<br><span style='font-size:12px'>Change: {change:+.1f} μg/m³ ({change_pct:+.1f}%)</span>",
                        yaxis_title="Concentration (μg/m³)",
                        height=300,
                        showlegend=False,
                    )

                    st.plotly_chart(fig, use_container_width=True)

    def show_enhanced_summary_separate(
        self, df_predictions, df_historical, prediction_timestamp
    ):
        """Show enhanced summary with separate DataFrames"""
        st.subheader("📊 Enhanced Summary Statistics")

        col1, col2, col3, col4 = st.columns(4)

        # Pollutant-specific comparison table
        if df_historical is not None and not df_historical.empty:
            st.subheader("🌫️ Pollutant Comparison")

            comparison_data = []
            for pollutant in df_predictions["pollutant"].unique():
                pred_stats = df_predictions[df_predictions["pollutant"] == pollutant][
                    "value"
                ]
                hist_stats = df_historical[df_historical["pollutant"] == pollutant][
                    "value"
                ]

                if not hist_stats.empty and not pred_stats.empty:
                    comparison_data.append(
                        {
                            "Pollutant": pollutant,
                            "Historical Avg": f"{hist_stats.mean():.1f}",
                            "Predicted Avg": f"{pred_stats.mean():.1f}",
                            "Change": f"{pred_stats.mean() - hist_stats.mean():+.1f}",
                            "Change %": (
                                f"{((pred_stats.mean() - hist_stats.mean()) / hist_stats.mean() * 100):+.1f}%"
                                if hist_stats.mean() != 0
                                else "N/A"
                            ),
                        }
                    )

            if comparison_data:
                pass
                # df_comparison = pd.DataFrame(comparison_data)
                # st.dataframe(df_comparison, use_container_width=True) #, hide_index=True)

    def render_data_collection_tab(self):  # noqa: C901
        """Render data collection tab for training dataset creation"""
        st.header("📥 Data Collection & Training Dataset Creation")

        # Data Status Section
        st.subheader("📊 Current Data Status")
        col1, col2 = st.columns(2)

        with col1:
            if st.button("🔍 Check Data Status", key="check_status"):
                with st.spinner("Checking data status..."):
                    status = self.get_data_status()
                    if status:
                        st.success("✅ Data status retrieved")
                        st.json(status)
                    else:
                        st.error("❌ Failed to get data status")

        with col2:
            if st.button("🔄 Refresh Prediction Data", key="refresh_data"):
                with st.spinner("Refreshing prediction data..."):
                    result = self.refresh_prediction_data()
                    if result:
                        st.success("✅ Prediction data refreshed")
                        st.json(result)
                    else:
                        st.error("❌ Failed to refresh data")

        st.divider()

        # Training Data Collection Section
        st.subheader("🏗️ Training Dataset Creation")

        col1, col2 = st.columns([2, 1])

        with col1:
            st.write("**Configure training data collection parameters:**")

            # Parameters for training data collection
            # chunk_size_hours = st.slider("Chunk Size (Hours)",
            #                            min_value=24, max_value=168,
            #                            value=72, step=24,
            #                            help="Size of data chunks to collect (24-168 hours)")

            chunk_size_hours = 7 * 24
            week_number = st.selectbox(
                "Week Number",
                options=[1, 2, 3, 4, 5, 6, 7, 8],
                index=1,
                help="Which week of data to collect",
            )

            st.info(
                f"""
            **Current Settings:**
            - Chunk Size: {chunk_size_hours} hours ({chunk_size_hours/24:.1f} days)
            - Week Number: {week_number}
            - This will collect pollution data for training
            """
            )

            # Collect Training Data Button
            if st.button(
                "🚀 Collect Training Data", type="primary", key="collect_training"
            ):
                with st.spinner(
                    f"Collecting training data (Week {week_number}, {chunk_size_hours}h chunks)..."
                ):
                    result = self.collect_training_data(week_number)
                    if result:
                        st.success("✅ Training data collection completed!")
                        st.json(result)

                        # Show success metrics if available
                        if isinstance(result, dict):
                            if "records_collected" in result:
                                st.metric(
                                    "Records Collected", result["records_collected"]
                                )
                            if "time_range" in result:
                                st.write(f"**Time Range:** {result['time_range']}")
                    else:
                        st.error("❌ Training data collection failed")

        with col2:
            st.info(
                """
            **Training Data Collection:

            1. **Chunk Size**: Controls how much data is processed at once
            2. **Week Number**: Selects which week of historical data to collect
            3. **Collection Process**:
               - Fetches pollution data from APIs
               - Processes and cleans the data
               - Saves to training dataset files
               - Updates data status

            **Recommended Settings:**
            - Chunk Size: 72 hours (3 days)
            - Week Number: 2 (for recent data)
            """
            )

        st.divider()

        # Weather Data Collection Section
        st.subheader("🌤️ Weather Data Collection")

        col1, col2 = st.columns([2, 1])

        with col1:
            st.write("Collect weather data to complement pollution measurements.")

            if st.button("🌡️ Collect Weather Data", key="collect_weather"):
                with st.spinner("Checking weather data collection..."):
                    self.collect_weather_data()
                    result = None
                    if result:
                        if result.get("status") == "info":
                            st.info(f"ℹ️ {result.get('message')}")
                            st.write(f"**Note:** {result.get('note')}")
                        else:
                            st.success("✅ Weather data collection completed!")
                            st.json(result)
                    else:
                        st.error("❌ Weather data collection failed")

        with col2:
            st.warning(
                """
            **Weather Data Collection:**

            🚧 **Currently Under Development**

            Future weather features:
            - Temperature
            - Humidity
            - Wind speed/direction
            - Atmospheric pressure
            - Precipitation

            Will be used as features for pollution prediction models.
            """
            )

        # Data Management Tips
        st.divider()
        st.subheader("💡 Data Management Tips")

        st.markdown(
            """
        **Best Practices:

        1. **Regular Collection**: Collect training data weekly to keep models updated
        2. **Data Quality**: Check data status before training to ensure sufficient data
        3. **Chunk Sizing**: Use 72-hour chunks for balanced processing and completeness
        4. **Weather Integration**: Collect weather data alongside pollution data for better predictions
        5. **Monitoring**: Regularly refresh prediction data to maintain current forecasts

        **Workflow:
        1. Check current data status
        2. Collect training data with appropriate parameters
        3. Collect complementary weather data
        4. Train new model with collected data
        5. Evaluate model performance
        """
        )


def main():
    dashboard = AirPollutionDashboard()
    dashboard.render_dashboard()


if __name__ == "__main__":
    main()
