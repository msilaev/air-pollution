"""
Tests for Prefect flows
"""

from datetime import datetime
from unittest.mock import Mock, patch

import pandas as pd
import pytest

# Mock Prefect imports to avoid dependency issues in testing
try:
    from flows.main_flows import (
        monitoring_pipeline_flow,
        prediction_pipeline_flow,
        training_pipeline_flow,
    )
    from flows.tasks import (
        check_data_quality_task,
        collect_prediction_data_task,
        collect_training_data_task,
        train_model_task,
        validate_model_task,
    )

    PREFECT_AVAILABLE = True
except ImportError:
    PREFECT_AVAILABLE = False


@pytest.mark.skipif(not PREFECT_AVAILABLE, reason="Prefect not available")
class TestPrefectTasks:
    @patch("flows.tasks.DataIngestion")
    @patch("flows.tasks.DataLoader")
    def test_collect_training_data_task_success(
        self, mock_data_loader, mock_data_ingestion
    ):
        """Test successful training data collection task"""
        # Mock data ingestion
        mock_ingestion_instance = Mock()
        mock_data_ingestion.return_value = mock_ingestion_instance

        # Mock data loader
        mock_loader_instance = Mock()
        sample_df = pd.DataFrame({"test": [1, 2, 3]})
        mock_loader_instance.load_train_dataset.return_value = sample_df
        mock_data_loader.return_value = mock_loader_instance

        result = collect_training_data_task.fn(chunk_size_hours=168, week_number=2)

        assert result["status"] == "success"
        assert result["records_collected"] == 3
        assert "timestamp" in result
        mock_ingestion_instance.fetch_pollution_data.assert_called_once()

    @patch("flows.tasks.DataIngestion")
    @patch("flows.tasks.DataLoader")
    def test_collect_training_data_task_failure(
        self, mock_data_loader, mock_data_ingestion
    ):
        """Test training data collection task failure"""
        # Mock data ingestion to raise exception
        mock_ingestion_instance = Mock()
        mock_ingestion_instance.fetch_pollution_data.side_effect = Exception(
            "API Error"
        )
        mock_data_ingestion.return_value = mock_ingestion_instance

        with pytest.raises(Exception, match="API Error"):
            collect_training_data_task.fn(chunk_size_hours=168, week_number=2)

    @patch("flows.tasks.DataIngestion")
    @patch("flows.tasks.DataLoader")
    def test_collect_prediction_data_task_success(
        self, mock_data_loader, mock_data_ingestion
    ):
        """Test successful prediction data collection task"""
        # Mock data ingestion
        mock_ingestion_instance = Mock()
        mock_data_ingestion.return_value = mock_ingestion_instance

        # Mock data loader
        mock_loader_instance = Mock()
        sample_df = pd.DataFrame({"test": [1, 2, 3, 4, 5]})
        mock_loader_instance.load_predicting_dataset.return_value = sample_df
        mock_data_loader.return_value = mock_loader_instance

        result = collect_prediction_data_task.fn(chunk_size_hours=48, week_number=1)

        assert result["status"] == "success"
        assert result["records_collected"] == 5
        assert "timestamp" in result
        mock_ingestion_instance.fetch_pollution_data.assert_called_once()

    @patch("flows.tasks.PollutionPredictor")
    @patch("flows.tasks.DataLoader")
    def test_train_model_task_success(self, mock_data_loader, mock_predictor):
        """Test successful model training task"""
        # Mock data loader
        mock_loader_instance = Mock()
        sample_df = pd.DataFrame({"test": [1, 2, 3]})
        mock_loader_instance.load_train_dataset.return_value = sample_df
        mock_data_loader.return_value = mock_loader_instance

        # Mock predictor
        mock_predictor_instance = Mock()
        mock_metrics = {"r2_score": 0.85, "rmse": 2.34}
        mock_predictor_instance.train.return_value = mock_metrics
        mock_predictor.return_value = mock_predictor_instance

        result = train_model_task.fn()

        assert result == mock_metrics
        mock_predictor_instance.train.assert_called_once_with(sample_df)

    @patch("flows.tasks.DataLoader")
    def test_train_model_task_no_data(self, mock_data_loader):
        """Test model training task with no data"""
        # Mock data loader to return None
        mock_loader_instance = Mock()
        mock_loader_instance.load_train_dataset.return_value = None
        mock_data_loader.return_value = mock_loader_instance

        with pytest.raises(ValueError, match="No training data available"):
            train_model_task.fn()

    @patch("flows.tasks.PollutionPredictor")
    @patch("flows.tasks.DataLoader")
    def test_validate_model_task_success(self, mock_data_loader, mock_predictor):
        """Test successful model validation task"""
        # Mock predictor
        mock_predictor_instance = Mock()
        mock_predictor_instance.load_model_from_mlflow.return_value = True
        mock_prediction = {"predictions": {"test": [1, 2, 3]}}
        mock_predictor_instance.predict.return_value = mock_prediction
        mock_predictor.return_value = mock_predictor_instance

        # Mock data loader
        mock_loader_instance = Mock()
        sample_df = pd.DataFrame({"test": [1, 2, 3]})
        mock_loader_instance.load_predicting_dataset.return_value = sample_df
        mock_data_loader.return_value = mock_loader_instance

        result = validate_model_task.fn()

        assert result["model_loaded"] is True
        assert result["status"] == "success"
        assert "timestamp" in result

    @patch("flows.tasks.DataLoader")
    def test_check_data_quality_task_training(self, mock_data_loader):
        """Test data quality check for training data"""
        # Mock data loader
        mock_loader_instance = Mock()
        sample_df = pd.DataFrame(
            {
                "NO": [1, 2, 3, 4, 5],
                "NO2": [1, 2, 3, 4, 5],
                "PM10": [1, 2, 3, 4, 5],
                "PM25": [1, 2, 3, 4, 5],
            }
        )
        sample_df.index = pd.date_range("2024-01-01", periods=5, freq="H")
        mock_loader_instance.load_train_dataset.return_value = sample_df
        mock_data_loader.return_value = mock_loader_instance

        result = check_data_quality_task.fn(data_type="training")

        assert result["status"] == "success"
        assert result["total_rows"] == 5
        assert result["total_columns"] == 4
        assert result["missing_values"] == 0
        assert result["duplicate_rows"] == 0
        assert result["passed"] is True
        assert result["quality_score"] == 100

    @patch("flows.tasks.DataLoader")
    def test_check_data_quality_task_poor_quality(self, mock_data_loader):
        """Test data quality check with poor quality data"""
        # Mock data loader with poor quality data
        mock_loader_instance = Mock()
        sample_df = pd.DataFrame(
            {
                "NO": [1, None, 3, None, 5],  # 40% missing
                "NO2": [1, 2, 3, 4, 5],
                "PM10": [1, 2, 3, 4, 5],
                "PM25": [1, 2, 3, 4, 5],
            }
        )
        sample_df.index = pd.date_range("2024-01-01", periods=5, freq="H")
        mock_loader_instance.load_train_dataset.return_value = sample_df
        mock_data_loader.return_value = mock_loader_instance

        result = check_data_quality_task.fn(data_type="training")

        assert result["status"] == "success"
        assert result["missing_percentage"] == 10.0  # 2 missing out of 20 total values
        assert result["passed"] is True  # Still passes with 10% missing
        assert result["quality_score"] == 100  # Threshold is 10%, so still 100


@pytest.mark.skipif(not PREFECT_AVAILABLE, reason="Prefect not available")
class TestPrefectFlows:
    @patch("flows.main_flows.collect_training_data_task")
    @patch("flows.main_flows.check_data_quality_task")
    @patch("flows.main_flows.train_model_task")
    @patch("flows.main_flows.validate_model_task")
    def test_training_pipeline_flow_success(
        self, mock_validate, mock_train, mock_quality, mock_collect
    ):
        """Test successful training pipeline flow"""
        # Mock task results
        mock_collect.return_value = {"status": "success", "records": 100}
        mock_quality.return_value = {"passed": True, "quality_score": 95}
        mock_train.return_value = {"r2_score": 0.85}
        mock_validate.return_value = {"model_loaded": True}

        result = training_pipeline_flow(chunk_size_hours=168, week_number=2)

        assert result["pipeline_status"] == "success"
        assert "data_collection" in result
        assert "quality_check" in result
        assert "training" in result
        assert "validation" in result

        # Verify task calls
        mock_collect.assert_called_once_with(
            chunk_size_hours=168, week_number=2, force_refresh=True
        )
        mock_quality.assert_called_once_with(data_type="training")
        mock_train.assert_called_once()
        mock_validate.assert_called_once()

    @patch("flows.main_flows.collect_training_data_task")
    @patch("flows.main_flows.check_data_quality_task")
    def test_training_pipeline_flow_quality_failure(self, mock_quality, mock_collect):
        """Test training pipeline flow with quality check failure"""
        # Mock task results
        mock_collect.return_value = {"status": "success", "records": 100}
        mock_quality.return_value = {"passed": False, "quality_score": 50}

        result = training_pipeline_flow(chunk_size_hours=168, week_number=2)

        assert result["pipeline_status"] == "failed_quality_check"
        assert "data_collection" in result
        assert "quality_check" in result
        assert "training" not in result  # Should skip training
        assert "validation" not in result  # Should skip validation

    @patch("flows.main_flows.collect_prediction_data_task")
    @patch("flows.main_flows.check_data_quality_task")
    def test_prediction_pipeline_flow_success(self, mock_quality, mock_collect):
        """Test successful prediction pipeline flow"""
        # Mock task results
        mock_collect.return_value = {"status": "success", "records": 48}
        mock_quality.return_value = {"passed": True, "quality_score": 90}

        result = prediction_pipeline_flow(chunk_size_hours=48, week_number=1)

        assert result["pipeline_status"] == "success"
        assert "data_collection" in result
        assert "quality_check" in result

        # Verify task calls
        mock_collect.assert_called_once_with(chunk_size_hours=48, week_number=1)
        mock_quality.assert_called_once_with(data_type="predicting")
