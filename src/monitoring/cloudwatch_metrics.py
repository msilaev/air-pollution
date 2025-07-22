# from datetime import datetime

import boto3

# from typing import Any, Dict


class CloudWatchMetrics:
    def __init__(self):
        self.cloudwatch = boto3.client("cloudwatch")
        self.namespace = "PollutionPrediction"

    def put_prediction_metrics(self, mae: float, rmse: float, model_version: str):
        """Send model performance metrics to CloudWatch"""

        metrics = [
            {
                "MetricName": "ModelMAE",
                "Value": mae,
                "Unit": "None",
                "Dimensions": [{"Name": "ModelVersion", "Value": model_version}],
            },
            {
                "MetricName": "ModelRMSE",
                "Value": rmse,
                "Unit": "None",
                "Dimensions": [{"Name": "ModelVersion", "Value": model_version}],
            },
        ]

        self.cloudwatch.put_metric_data(Namespace=self.namespace, MetricData=metrics)

    def put_prediction_count(self, count: int, model_version: str):
        """Log number of predictions made"""
        self.cloudwatch.put_metric_data(
            Namespace=self.namespace,
            MetricData=[
                {
                    "MetricName": "PredictionCount",
                    "Value": count,
                    "Unit": "Count",
                    "Dimensions": [{"Name": "ModelVersion", "Value": model_version}],
                }
            ],
        )

    def put_flow_execution_metrics(self, flow_name: str, status: str, duration: float):
        """Log flow execution metrics"""
        self.cloudwatch.put_metric_data(
            Namespace=self.namespace,
            MetricData=[
                {
                    "MetricName": "FlowExecution",
                    "Value": 1 if status == "success" else 0,
                    "Unit": "Count",
                    "Dimensions": [
                        {"Name": "FlowName", "Value": flow_name},
                        {"Name": "Status", "Value": status},
                    ],
                },
                {
                    "MetricName": "FlowDuration",
                    "Value": duration,
                    "Unit": "Seconds",
                    "Dimensions": [{"Name": "FlowName", "Value": flow_name}],
                },
            ],
        )

    def put_data_quality_metrics(self, data_shape: tuple, missing_values: int):
        """Log data quality metrics"""
        self.cloudwatch.put_metric_data(
            Namespace=self.namespace,
            MetricData=[
                {"MetricName": "DataRows", "Value": data_shape[0], "Unit": "Count"},
                {"MetricName": "DataColumns", "Value": data_shape[1], "Unit": "Count"},
                {
                    "MetricName": "MissingValues",
                    "Value": missing_values,
                    "Unit": "Count",
                },
            ],
        )
