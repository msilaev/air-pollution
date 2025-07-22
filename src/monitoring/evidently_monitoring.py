# import pandas as pd
from evidently import ColumnMapping
from evidently.metrics import DatasetDriftMetric
from evidently.report import Report


class ModelMonitor:
    def __init__(self):
        self.column_mapping = ColumnMapping()

    def generate_drift_report(self, reference_data, current_data):
        """Generate drift detection report"""
        report = Report(metrics=[DatasetDriftMetric()])
        report.run(reference_data=reference_data, current_data=current_data)
        return report

    def check_drift(self, reference_data, current_data):
        """Check for data drift"""
        report = self.generate_drift_report(reference_data, current_data)
        drift_detected = report.as_dict()["metrics"][0]["result"]["dataset_drift"]
        return drift_detected
