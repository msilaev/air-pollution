# Test configuration for pytest
import os
import sys

# from datetime import datetime, timedelta
from unittest.mock import Mock, patch

import pandas as pd
import pytest

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


@pytest.fixture
def sample_pollution_data():
    """Sample pollution data for testing"""
    dates = pd.date_range(start="2024-01-01", periods=100, freq="H")
    data = {
        "Timestamp": dates,
        "Nitrogen dioxide_Helsinki Kallio 2": [20.5 + i * 0.1 for i in range(100)],
        "Particulate matter < 10 µm_Helsinki Kallio 2": [
            25.0 + i * 0.2 for i in range(100)
        ],
        "Particulate matter < 2.5 µm_Helsinki Kallio 2": [
            12.1 + i * 0.1 for i in range(100)
        ],
    }
    df = pd.DataFrame(data)
    return df


@pytest.fixture
def mock_s3_client():
    """Mock S3 client for testing"""
    with patch("boto3.client") as mock_client:
        yield mock_client


@pytest.fixture
def mock_mlflow():
    """Mock MLflow for testing"""
    with patch("mlflow.sklearn.log_model"), patch("mlflow.log_metrics"), patch(
        "mlflow.log_params"
    ), patch("mlflow.start_run") as mock_start, patch("mlflow.end_run"), patch(
        "mlflow.set_tracking_uri"
    ), patch(
        "mlflow.get_experiment_by_name"
    ) as mock_exp, patch(
        "mlflow.create_experiment"
    ) as mock_create, patch(
        "mlflow.set_experiment"
    ):
        # Setup mock returns
        mock_exp.return_value = None
        mock_create.return_value = "test_experiment_id"

        # Mock active run context
        mock_run = Mock()
        mock_run.__enter__ = Mock(return_value=mock_run)
        mock_run.__exit__ = Mock(return_value=None)
        mock_start.return_value = mock_run

        yield


@pytest.fixture(autouse=False)  # Disabled due to PyArrow compatibility issues
def clean_mlflow():
    """Clean up MLflow state before and after each test"""
    # Disabled to avoid PyArrow crashes on Windows
    yield
