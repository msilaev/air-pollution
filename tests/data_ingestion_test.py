"""
Tests for DataIngestion - only tests that use existing methods
"""

from unittest.mock import patch

from src.data.data_ingestion import DataIngestion

# Removed unused import


class TestDataIngestion:
    """Test cases for DataIngestion class"""

    def test_init_local(self):
        """Test initialization with local mode"""
        ingestion = DataIngestion(use_s3=False)
        assert ingestion.use_s3 is False
        assert ingestion.address == "Helsinki"
        assert not hasattr(ingestion, "s3_client") or ingestion.s3_client is None

    def test_init_s3(self, mock_s3_client):
        """Test initialization with S3 mode"""
        with patch.dict("os.environ", {"AWS_S3_DATA_BUCKET": "test-bucket"}):
            with patch("boto3.client", return_value=mock_s3_client):
                ingestion = DataIngestion(use_s3=True)
                assert ingestion.use_s3 is True
                assert ingestion.bucket == "test-bucket"
                assert ingestion.s3_client is not None

    def test_init_custom_address(self):
        """Test initialization with custom address"""
        ingestion = DataIngestion(address="Espoo")
        assert ingestion.address == "Espoo"

    def test_upload_to_s3_method_exists(self):
        """Test that upload_to_s3 method exists"""
        ingestion = DataIngestion()
        assert hasattr(ingestion, "upload_to_s3"), "upload_to_s3 method should exist"

    def test_merge_and_save_data_local_method_exists(self):
        """Test that merge_and_save_data_local method exists"""
        ingestion = DataIngestion()
        assert hasattr(
            ingestion, "merge_and_save_data_local"
        ), "merge_and_save_data_local method should exist"

    def test_fetch_pollution_data_method_exists(self):
        """Test that fetch_pollution_data method exists"""
        ingestion = DataIngestion()
        assert hasattr(
            ingestion, "fetch_pollution_data"
        ), "fetch_pollution_data method should exist"
