## Air pollution prediction app

This is an end-to-end project following MLOPS practices on automation of data collection, model training and deployment. The goal is to predict air pullution indicators in Helsinki, Finland using the open-sourse real-time data from the air quality measuring stations.

## Note for mlops zoomcamp evaluators: Please use the latest commit, some bugs noticed at the last moment has been corrected

## Table of Contents
- [Resources](#resources)
- [Project Structure](#project-structure)
- [Installation](#installation)
- [Testing](#testing)
- [Orchestration with Prefect](#orchestration-with-prefect)
- [API Documentation](#api-documentation)
- [Deployment](#deployment)

## Resources
[FMI open data](https://en.ilmatieteenlaitos.fi/open-data)

[FMI WFS guide](https://en.ilmatieteenlaitos.fi/open-data-manual-wfs-examples-and-guidelines)

[fmiopen interface] (https://github.com/pnuu/fmiopendata)

Classes for parcing xml file with weather data are taken from fmiopen


## Project Structure

```plaintext
air_pollution/
├── notebooks/                  # Jupyter notebooks for experimentation
├── src/                        # Source code
│   ├── data/                   # Data processing scripts
│   │   ├── data_loader.py      # Data loading utilities
│   │   ├── data_ingestion.py   # API data collection
│   │   └── preprocess.py       # Data preprocessing
│   ├── models/                 # Model-related scripts
│   │   ├── pollution_predictor.py  # Main ML model
│   │   ├── train.py            # Training scripts
│   │   └── evaluate.py         # Model evaluation
│   ├── api/                    # REST API implementation
│   │   ├── app.py              # Main FastAPI app
│   │   ├── routes/             # API route modules
│   │   └── schemas.py          # Request/response schemas
│   ├── frontend/               # Streamlit dashboard
│   ├── monitoring/             # Data quality & model monitoring
│   └── config.py               # Configuration settings
├── flows/                      # Prefect orchestration workflows
│   ├── tasks.py                # Individual Prefect tasks
│   ├── main_flows.py           # Main pipeline flows
│   ├── training_flow.py        # Model training pipeline
│   ├── prediction_flow.py      # Prediction pipeline
│   ├── monitoring_flow.py      # Monitoring pipeline
│   └── deployments.py          # Flow deployment configurations
├── tests/                      # Comprehensive test suite
│   ├── test_predictor.py       # ML model tests
│   ├── test_api.py             # API tests
│   ├── test_data_ingestion.py  # Data pipeline tests
│   ├── test_flows.py           # Prefect orchestration tests
│   └── conftest.py             # Test configuration
├── data/                       # Raw and processed data
├── scripts/                    # Utility scripts
├── infrastructure/             # Docker & Terraform configs
├── .env                        # Environment variables
├── Dockerfile                  # Containerization
├── docker-compose.yml          # Multi-service orchestration
├── requirements.txt            # Python dependencies
└── README.md                   # Documentation
```

## Installation

### Prerequisites
- Python 3.8+ (tested with Python 3.11)
- Git
- (Optional) AWS CLI configured for S3 access
- (Optional) MLflow server for model tracking

### Setup Instructions

#### 1. Clone the Repository
```bash
git clone <repository-url>
cd air_pollution
```

#### 2. Create Virtual Environment
```bash
# Using venv
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
```

#### 3. Install Dependencies
```bash
# Install core dependencies
pip install -r requirements.txt

# For development (includes testing and linting tools)
pip install -r requirements-dev.txt  # if available
```

#### 4. Environment Configuration
Create a `.env` file in the project root:
```bash
# MLflow Configuration
MLFLOW_TRACKING_URI=sqlite:///mlflow.db
MLFLOW_S3_ENDPOINT_URL=your-s3-endpoint  # Optional

# AWS Configuration (Optional)
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
AWS_S3_DATA_BUCKET=your-bucket-name

# Application Configuration
PYTHONPATH=.
```

##### S3 Data and Artifact Storage

The use of AWS S3 for storing data and model artifacts is controlled by the `USE_S3` flag in `src/config.py`:

```python
USE_S3 = False  # Set to True to enable S3 storage for data and artifacts
```

- When `USE_S3 = True`, the application will read from and write to S3 buckets as configured in your environment variables.
- When `USE_S3 = False`, all data and artifacts will be stored locally in the `data/` and `models/` directories.

Update this flag according to your deployment or development needs.

#### 5. Verify Installation
```bash
# Run tests to verify everything is working
python -m pytest tests/ -v

# Check if core modules can be imported
python -c "from src.models.pollution_predictor import PollutionPredictor; print('✅ Installation successful!')"
```

### Quick Start
```bash
# Start the API server
python -m src.api.app

# Start the Streamlit dashboard
streamlit run src/frontend/dashboard.py

# Start Prefect orchestration server
prefect server start

# Run data collection (if configured)
python -m src.data.data_ingestion

# Run orchestrated training pipeline
python -c "from flows.main_flows import training_pipeline_flow; training_pipeline_flow()"
```

### Docker Installation (Alternative)
```bash
# Build the Docker image
docker build -t air-pollution-app .

# Run the container
docker run -p 8000:8000 air-pollution-app
```

### Troubleshooting

#### Common Issues:
- **PyArrow warnings on Windows**: These are compatibility warnings and don't affect functionality
- **MLflow connection errors**: Ensure `MLFLOW_TRACKING_URI` is set correctly
- **Import errors**: Make sure `PYTHONPATH=.` is set in your environment
- **AWS access issues**: Verify your AWS credentials and bucket permissions

## Testing

The project includes a comprehensive test suite with unit tests for the core components. All tests are designed to run independently and use mocking to avoid external dependencies.

### Test Structure

The test suite covers the following components:

#### 🧪 **Unit Tests**
- **`test_predictor.py`** - Core ML model logic tests (12 tests)
  - Model initialization and configuration
  - Data preprocessing and sequence preparation
  - Training pipeline validation
  - Prediction functionality
  - MLflow model loading and versioning

- **`test_data_ingestion.py`** - Data ingestion component tests (6 tests)
  - Local and S3 mode initialization
  - Configuration validation
  - Method existence verification
  - AWS integration setup (mocked)

- **`test_api.py`** - API structure and endpoints tests (6 tests)
  - FastAPI app creation and configuration
  - Health check endpoints functionality
  - Route registration verification
  - Module import validation

- **`test_flows.py`** - Prefect orchestration tests (11 tests - skipped when Prefect unavailable)
  - Data collection pipeline tasks
  - Model training workflows
  - Data quality validation
  - Pipeline integration flows

### Running Tests

#### Prerequisites
Ensure you have installed the project dependencies:
```bash
pip install -r requirements.txt
```

#### Run All Tests
```bash
# Run the complete test suite
python -m pytest tests/ -v

# Run with coverage report
python -m pytest tests/ -v --cov=src
```

#### Run Specific Test Categories
```bash
# Run only ML model tests
python -m pytest tests/test_predictor.py -v

# Run only API tests
python -m pytest tests/test_api.py -v

# Run only data ingestion tests
python -m pytest tests/test_data_ingestion.py -v

# Run orchestration tests (requires Prefect)
python -m pytest tests/test_flows.py -v
```

#### Test Output Interpretation
- ✅ **PASSED** - Test executed successfully
- ⏭️ **SKIPPED** - Test skipped (usually due to missing optional dependencies like Prefect)
- ❌ **FAILED** - Test failed (indicates a bug or configuration issue)

#### Expected Results
When running the full test suite, you should see:
- **35 tests PASSED** - All functionality working correctly including Prefect orchestration
- **0 tests FAILED** - Complete test coverage with no failures
- **~100 warnings** - Deprecation warnings (non-critical, do not affect functionality)

### Test Coverage
The tests focus on:
- **Unit testing** of individual components in isolation
- **Mocking** of external dependencies (AWS S3, MLflow, file systems)
- **Fast execution** without requiring external services
- **Regression prevention** for core ML and API functionality

### Notes
- Tests use mocking to avoid requiring actual AWS credentials or MLflow servers
- Some PyArrow compatibility warnings may appear on Windows but don't affect test results
- The test suite is designed to run in CI/CD environments without external dependencies

## Frontend: Streamlit Dashboard

The project includes an interactive dashboard for visualizing air pollution predictions and data. You can run the dashboard locally using Streamlit.

### Start the Dashboard (Frontend)

From the project root, run:

```bash
streamlit run src/frontend/dashboard.py
```

- The dashboard will be available at: http://localhost:8501
- Make sure your API server is running if the dashboard depends on live predictions.



## Orchestration with Prefect

The project uses [Prefect](https://www.prefect.io/) for workflow orchestration, providing automated data collection, model training, and prediction pipelines with monitoring and error handling.

### 🔧 **Prefect Setup**

#### 1. Start Prefect Server
```bash
# Start the local Prefect server
prefect server start

# The server will be available at: http://127.0.0.1:4200
# Dashboard: http://127.0.0.1:4200
# API docs: http://127.0.0.1:4200/docs
```

#### 2. Configure Prefect Client
```bash
# In a new terminal, set the API URL
prefect config set PREFECT_API_URL=http://127.0.0.1:4200/api

# Verify configuration
prefect config view
```

#### 3. Create a Work Pool (Optional)
```bash
# Create a local work pool for running flows
prefect work-pool create --type process local-pool

# Start a worker
prefect worker start --pool local-pool
```

### 🔄 **Available Workflows**

#### **Training Pipeline Flow**
Orchestrates the complete model training process:
- Data collection from multiple pollution monitoring stations
- Data quality validation
- Model training with MLflow tracking
- Model validation and registration

```python
# Run training pipeline programmatically
from flows.main_flows import training_pipeline_flow

result = training_pipeline_flow()
```

#### **Prediction Pipeline Flow**
Handles real-time predictions:
- Collects latest pollution data
- Loads trained model from MLflow
- Generates predictions
- Stores results for API consumption

```python
# Run prediction pipeline
from flows.main_flows import prediction_pipeline_flow

predictions = prediction_pipeline_flow()
```

#### **Monitoring Pipeline Flow**
Monitors data quality and model performance:
- Data drift detection
- Model performance tracking
- Alert generation for anomalies

```python
# Run monitoring pipeline
from flows.main_flows import monitoring_pipeline_flow

monitoring_results = monitoring_pipeline_flow()
```

### 🏃 **Running Flows**

#### **Method 1: Python Scripts**
```bash
# Training pipeline
python -c "from flows.main_flows import training_pipeline_flow; training_pipeline_flow()"


# Prediction pipeline
python -c "from flows.main_flows import prediction_pipeline_flow; prediction_pipeline_flow()"


# Monitoring pipeline
python -c "from flows.main_flows import monitoring_pipeline_flow; monitoring_pipeline_flow()"
```

#### **Method 2: Prefect CLI**
```bash
# Deploy flows to Prefect server
python flows/deployments.py

# Run deployed flows
prefect deployment run "training-pipeline/default"
prefect deployment run "prediction-pipeline/default"
```

#### **Method 3: Scheduled Runs**
```python
# flows/deployments.py contains scheduled deployments
# Training: Daily at 2 AM
# Predictions: Every 4 hours
# Monitoring: Every 2 hours
```

### 📊 **Monitoring & Observability**

#### **Prefect Dashboard**
- **Flow Runs**: View execution history and status
- **Task Runs**: Detailed task-level monitoring
- **Logs**: Real-time and historical logs
- **Metrics**: Performance and success rates

#### **MLflow Integration**
- **Experiment Tracking**: All training runs logged
- **Model Registry**: Versioned model artifacts
- **Metrics Comparison**: Training vs validation performance

#### **Data Quality Monitoring**
```python
# Built-in data quality checks
from flows.tasks import check_data_quality_task

quality_report = check_data_quality_task(data_type="training")
print(f"Quality Score: {quality_report['quality_score']}")
```

### 🔧 **Individual Tasks**

You can also run individual Prefect tasks for development and testing:

```python
# Data collection
from flows.tasks import collect_training_data_task
data = collect_training_data_task.fn(chunk_size_hours=168, week_number=2)

# Model training
from flows.tasks import train_model_task
metrics = train_model_task.fn()

# Model validation
from flows.tasks import validate_model_task
validation = validate_model_task.fn()

# Data quality check
from flows.tasks import check_data_quality_task
quality = check_data_quality_task.fn(data_type="training")
```

### 🚨 **Error Handling & Retries**

Prefect flows include robust error handling:
- **Automatic Retries**: Failed tasks retry with exponential backoff
- **Failure Notifications**: Configurable alerts for failed flows
- **Graceful Degradation**: Partial failures don't stop entire pipeline
- **State Management**: Track and resume from failed states

### 📈 **Production Configuration**

#### **Environment Variables**
```bash
# .env file configuration
PREFECT_API_URL=http://127.0.0.1:4200/api
PREFECT_WORK_POOL=local-pool
PREFECT_LOG_LEVEL=INFO

# For production deployments
PREFECT_CLOUD_API_KEY=your-cloud-api-key  # If using Prefect Cloud
```

#### **Scaling Considerations**
- **Work Pools**: Configure multiple pools for different task types
- **Concurrency**: Set limits for parallel task execution
- **Resource Allocation**: Configure CPU/memory limits per task
- **Storage**: Use remote storage for large datasets

### 🧪 **Testing Orchestration**

The project includes comprehensive tests for Prefect components:

```bash
# Test all Prefect tasks and flows
python -m pytest tests/test_flows.py -v

# Test individual task functions
python -m pytest tests/test_flows.py::TestPrefectTasks::test_collect_training_data_task_success -v

# Test flow orchestration
python -m pytest tests/test_flows.py::TestPrefectFlows -v
```

### 🔍 **Troubleshooting**

#### **Common Issues**
1. **Server Connection**: Ensure `PREFECT_API_URL` is set correctly
2. **Task Failures**: Check logs in Prefect dashboard
3. **Import Errors**: Verify all dependencies are installed
4. **Database Issues**: Reset Prefect database if corrupted

#### **Debug Commands**
```bash
# Check Prefect configuration
prefect config view

# View server status
prefect server database reset  # If database issues

# Check flow state
prefect flow-run ls --limit 10
```

### 📚 **Additional Resources**

- [Prefect Documentation](https://docs.prefect.io/)
- [Prefect Cloud](https://app.prefect.cloud/) for managed orchestration
- [Flow Run Concepts](https://docs.prefect.io/concepts/flows/)
- [Task Run Monitoring](https://docs.prefect.io/concepts/tasks/)

## Deployment

This project supports multiple deployment options, with a comprehensive AWS cloud deployment using Terraform for infrastructure as code.

### 🚀 **AWS Cloud Deployment**

The project includes a complete AWS deployment setup using Terraform that provisions a production-ready infrastructure with high availability, security, and scalability.

#### **🏗️ Architecture Overview**

The AWS deployment creates the following infrastructure:

```
┌─────────────────────────────────────────────────────────────┐
│                     AWS Cloud Infrastructure                │
├─────────────────────────────────────────────────────────────┤
│  Internet Gateway                                           │
│       │                                                     │
│  ┌────▼─────┐                                               │
│  │    ALB   │ (Application Load Balancer)                   │
│  │  Ports:  │ :80, :4200, :5000, :8501                     │
│  └────┬─────┘                                               │
│       │                                                     │
│  ┌────▼──────────────────────────────────────────────────┐  │
│  │                 ECS Cluster                           │  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────┐│  │
│  │  │    API   │  │Dashboard │  │  MLflow  │  │Prefect ││  │
│  │  │   :8000  │  │  :8501   │  │  :5000   │  │ :4200  ││  │
│  │  └──────────┘  └──────────┘  └──────────┘  └────────┘│  │
│  └─────────────────────────────────────────────────────────┘  │
│                              │                                │
│  ┌───────────────────────────▼──────────────────────────────┐ │
│  │              RDS PostgreSQL Database                     │ │
│  │                    (MLflow Backend)                      │ │
│  └───────────────────────────────────────────────────────────┘ │
│                              │                                │
│  ┌───────────────────────────▼──────────────────────────────┐ │
│  │                    S3 Buckets                            │ │
│  │           • MLflow Artifacts Storage                     │ │
│  │           • Data Lake Storage                            │ │
│  └───────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

#### **📋 Prerequisites**

Before deploying to AWS, ensure you have:

1. **AWS CLI configured** with appropriate credentials
2. **Terraform installed** (version >= 1.0)
3. **Docker installed** for building images
4. **Required IAM permissions** for your AWS user

#### **🔐 Required IAM Permissions**

Your AWS IAM user needs the following managed policies:

- `AmazonEC2FullAccess` - For VPC, security groups, and networking
- `AmazonECS_FullAccess` - For ECS cluster and service management
- `AmazonRDSFullAccess` - For RDS database management
- `AmazonS3FullAccess` - For S3 bucket creation and management
- `AmazonEC2ContainerRegistryFullAccess` - For ECR repositories
- `IAMFullAccess` - For creating service roles
- `CloudWatchLogsFullAccess` - For logging infrastructure

#### **🚀 Deployment Steps**

##### **Step 1: Build and Push Docker Images**

```bash
# Login to AWS ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 909251725488.dkr.ecr.us-east-1.amazonaws.com

# Build Docker images
docker build -f Dockerfile.api -t air-pollution/api:latest .
docker build -f Dockerfile.dashboard -t air-pollution/dashboard:latest .
docker build -f Dockerfile.prefect -t air-pollution/prefect:latest .

# Tag and push images to ECR
docker tag air-pollution/api:latest 909251725488.dkr.ecr.us-east-1.amazonaws.com/air-pollution/api:latest
docker push 909251725488.dkr.ecr.us-east-1.amazonaws.com/air-pollution/api:latest

docker tag air-pollution/dashboard:latest 909251725488.dkr.ecr.us-east-1.amazonaws.com/air-pollution/dashboard:latest
docker push 909251725488.dkr.ecr.us-east-1.amazonaws.com/air-pollution/dashboard:latest

docker tag air-pollution/prefect:latest 909251725488.dkr.ecr.us-east-1.amazonaws.com/air-pollution/prefect:latest
docker push 909251725488.dkr.ecr.us-east-1.amazonaws.com/air-pollution/prefect:latest
```

##### **Step 2: Create Terraform State Bucket**

```bash
# Create S3 bucket for Terraform state
aws s3 mb s3://air-pollution-terraform-state --region us-east-1
```

##### **Step 3: Deploy Infrastructure with Terraform**

```bash
# Navigate to terraform directory
cd infrastructure/terraform

# Initialize Terraform
terraform init

# Review deployment plan
terraform plan -var="db_password=your-secure-password"

# Deploy infrastructure
terraform apply -var="db_password=your-secure-password" -auto-approve
```

##### **Step 4: Verify Deployment**

```bash
# Check ECS cluster status
aws ecs list-services --cluster air-pollution-cluster

# Check service health
aws ecs describe-services --cluster air-pollution-cluster --services api-service dashboard-service mlflow-service prefect-service
```

#### **🌐 Service URLs**

After successful deployment, your services will be available at:

- **🔗 API**: `http://your-alb-dns-name.elb.amazonaws.com`
- **🔗 Dashboard**: `http://your-alb-dns-name.elb.amazonaws.com:8501`
- **🔗 MLflow**: `http://your-alb-dns-name.elb.amazonaws.com:5000`
- **🔗 Prefect**: `http://your-alb-dns-name.elb.amazonaws.com:4200`
- **📖 API Docs**: `http://your-alb-dns-name.elb.amazonaws.com/docs`

You can get the actual load balancer DNS name from Terraform output:
```bash
terraform output load_balancer_dns_name
```

#### **📊 Deployed Components**

| Component | Description | Port | Purpose |
|-----------|-------------|------|---------|
| **API Service** | FastAPI REST API | 8000 | Model predictions and data access |
| **Dashboard** | Streamlit web interface | 8501 | Interactive data visualization |
| **MLflow** | Model registry & tracking | 5000 | ML model lifecycle management |
| **Prefect** | Workflow orchestration | 4200 | Pipeline automation and scheduling |
| **PostgreSQL** | Database backend | 5432 | MLflow metadata storage |
| **S3 Buckets** | Object storage | - | Model artifacts and data lake |

#### **🔄 Infrastructure Management**

##### **Scaling Services**
```bash
# Scale API service to 3 instances
aws ecs update-service --cluster air-pollution-cluster --service api-service --desired-count 3

# Scale dashboard service
aws ecs update-service --cluster air-pollution-cluster --service dashboard-service --desired-count 2
```

##### **Updating Application**
```bash
# Rebuild and push new image
docker build -f Dockerfile.api -t air-pollution/api:latest .
docker tag air-pollution/api:latest 909251725488.dkr.ecr.us-east-1.amazonaws.com/air-pollution/api:latest
docker push 909251725488.dkr.ecr.us-east-1.amazonaws.com/air-pollution/api:latest

# Force new deployment
aws ecs update-service --cluster air-pollution-cluster --service api-service --force-new-deployment
```

##### **Monitoring and Logs**
```bash
# View service logs
aws logs tail /ecs/air-pollution-api --follow

# Check service health
aws ecs describe-services --cluster air-pollution-cluster --services api-service
```

#### **💰 Cost Optimization**

The deployment is designed for cost efficiency:

- **ECS Fargate**: Pay only for running containers
- **RDS t3.micro**: Free tier eligible for 12 months
- **S3**: Pay for storage used
- **ALB**: Minimal cost for traffic routing

**Estimated Monthly Cost**: $20-50 USD (depending on usage)

#### **🔒 Security Features**

- **VPC with private subnets** for database isolation
- **Security groups** with minimal required access
- **ALB** for SSL termination (when configured)
- **IAM roles** with least privilege access
- **RDS encryption** at rest

#### **🚨 Troubleshooting**

##### **Common Issues:**

1. **ECS Services Not Starting**
   ```bash
   # Check service events
   aws ecs describe-services --cluster air-pollution-cluster --services api-service

   # Check task definition
   aws ecs describe-task-definition --task-definition air-pollution-api:latest
   ```

2. **Database Connection Issues**
   ```bash
   # Check RDS status
   aws rds describe-db-instances --db-instance-identifier air-pollution-postgres

   # Verify security groups
   aws ec2 describe-security-groups --group-ids sg-xxxxxx
   ```

3. **Load Balancer Health Checks Failing**
   ```bash
   # Check target group health
   aws elbv2 describe-target-health --target-group-arn arn:aws:elasticloadbalancing:...
   ```

##### **Log Analysis:**
```bash
# API service logs
aws logs tail /ecs/air-pollution-api --follow

# Database logs (if enabled)
aws logs tail /aws/rds/instance/air-pollution-postgres/error --follow
```

#### **🧹 Cleanup**

To destroy the infrastructure and avoid ongoing costs:

```bash
cd infrastructure/terraform
terraform destroy -var="db_password=your-secure-password" -auto-approve

# Remove ECR images
aws ecr delete-repository --repository-name air-pollution/api --force
aws ecr delete-repository --repository-name air-pollution/dashboard --force
aws ecr delete-repository --repository-name air-pollution/prefect --force

# Remove S3 state bucket (optional)
aws s3 rb s3://air-pollution-terraform-state --force
```

### 🐳 **Local Docker Deployment**

For development and testing, you can run the entire stack locally using Docker Compose:

```bash
# Build and start all services
docker-compose up --build

# Start in detached mode
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

**Local Service URLs:**
- API: http://localhost:8000
- Dashboard: http://localhost:8501
- MLflow: http://localhost:5000
- Prefect: http://localhost:4200

### 🔧 **Environment Configuration**

#### **Production Environment Variables**
```bash
# AWS Configuration
AWS_REGION=us-east-1
AWS_S3_DATA_BUCKET=air-pollution-data-storage-xxxxx
AWS_S3_MLFLOW_BUCKET=air-pollution-mlflow-artifacts-xxxxx

# Database Configuration
DATABASE_URL=postgresql://mlflow:password@your-rds-endpoint:5432/mlflow

# MLflow Configuration
MLFLOW_TRACKING_URI=http://your-alb-dns:5000
MLFLOW_S3_ENDPOINT_URL=https://s3.us-east-1.amazonaws.com

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
```

#### **Development Environment Variables**
```bash
# Local Development
MLFLOW_TRACKING_URI=sqlite:///mlflow.db
DATABASE_URL=sqlite:///local.db
PYTHONPATH=.
```

### 📈 **Production Best Practices**

1. **SSL/TLS**: Configure ACM certificate for HTTPS
2. **Domain**: Use Route53 for custom domain names
3. **Monitoring**: Enable CloudWatch detailed monitoring
4. **Backup**: Configure RDS automated backups
5. **Scaling**: Set up auto-scaling policies
6. **CI/CD**: Integrate with GitHub Actions or CodePipeline
7. **Secrets**: Use AWS Secrets Manager for sensitive data

### 🎯 **Next Steps**

After deployment, consider:

1. **Setting up monitoring dashboards** in CloudWatch
2. **Configuring alerts** for service health
3. **Implementing CI/CD pipelines** for automated deployments
4. **Adding SSL certificates** for HTTPS
5. **Setting up custom domains** with Route53
6. **Implementing backup strategies** for data persistence
