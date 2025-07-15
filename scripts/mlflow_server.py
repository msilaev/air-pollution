import os
import signal
import subprocess
import sys

from dotenv import load_dotenv


class MLflowServerManager:
    def __init__(self):
        load_dotenv()
        self.process = None

    def start_server(self):
        """Start MLflow server"""
        aws_access_key = os.getenv("AWS_ACCESS_KEY_ID")
        aws_secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
        aws_region = os.getenv("AWS_REGION", "us-east-1")

        if not aws_access_key or not aws_secret_key:
            print("❌ AWS credentials not found in environment variables.")
            return False

        env = os.environ.copy()
        env.update(
            {
                "AWS_ACCESS_KEY_ID": aws_access_key,
                "AWS_SECRET_ACCESS_KEY": aws_secret_key,
                "AWS_REGION": aws_region,
            }
        )

        cmd = [
            "mlflow",
            "server",
            "--backend-store-uri",
            "sqlite:///mlflow.db",
            "--default-artifact-root",
            "s3://mlflow-artifacts-remote-2025/air_pollution_prediction",
            "--host",
            "0.0.0.0",
            "--port",
            "5000",
        ]

        try:
            print("🚀 Starting MLflow server...")
            print(f"Command: {' '.join(cmd)}")
            print("MLflow UI will be available at: http://localhost:5000")
            print("Press Ctrl+C to stop")

            self.process = subprocess.Popen(cmd, env=env)
            return True
        except Exception as e:
            print(f"❌ Failed to start MLflow server: {e}")
            return False

    def stop_server(self):
        """Stop MLflow server"""
        if self.process:
            self.process.terminate()
            print("MLflow server stopped")


def signal_handler(sig, frame):
    print("\nShutting down MLflow server...")
    if hasattr(signal_handler, "server_manager"):
        signal_handler.server_manager.stop_server()
    sys.exit(0)


if __name__ == "__main__":
    server_manager = MLflowServerManager()
    signal_handler.server_manager = server_manager

    # Handle Ctrl+C gracefully
    signal.signal(signal.SIGINT, signal_handler)

    if server_manager.start_server():
        try:
            # Keep the script running
            server_manager.process.wait()
        except KeyboardInterrupt:
            pass
    else:
        sys.exit(1)
