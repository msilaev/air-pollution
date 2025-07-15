# MLOps Production Deployment Guide

## 🚀 Complete MLOps Pipeline with Prefect & AWS

This guide covers the complete deployment of our Air Pollution Prediction system with:
- **Prefect** for workflow orchestration
- **AWS ECS** for containerized deployment
- **Terraform** for infrastructure as code
- **GitHub Actions** for CI/CD
- **MLflow** for model management

## 📋 Prerequisites

### 1. Install Required Tools
```bash
# AWS CLI
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install

# Terraform
wget https://releases.hashicorp.com/terraform/1.5.0/terraform_1.5.0_linux_amd64.zip
unzip terraform_1.5.0_linux_amd64.zip
sudo mv terraform /usr/local/bin/

# Docker (if not installed)
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh
```

### 2. Configure AWS
```bash
aws configure
# Enter your Access Key ID, Secret Access Key, and region
```

### 3. Set Environment Variables
```bash
export AWS_REGION=us-east-1
export ENVIRONMENT=prod
export DB_PASSWORD=$(openssl rand -base64 32)
export PREFECT_API_URL=https://your-prefect-cloud-url
export PREFECT_API_KEY=your-prefect-api-key
```

## 🏗️ Infrastructure Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                          AWS Cloud                         │
├─────────────────────────────────────────────────────────────┤
│  Application Load Balancer (ALB)                           │
│         │                                                   │
│  ┌──────▼──────┐  ┌────────────┐  ┌─────────────────┐      │
│  │   API       │  │ Dashboard  │  │ Prefect Worker  │      │
│  │ (ECS Task)  │  │(ECS Task)  │  │   (ECS Task)    │      │
│  └─────────────┘  └────────────┘  └─────────────────┘      │
│         │                │                │                 │
│  ┌──────▼────────────────▼────────────────▼──────┐         │
│  │              MLflow Server                    │         │
│  │              (ECS Task)                       │         │
│  └───────────────────┬───────────────────────────┘         │
│                      │                                     │
│  ┌──────────────────▼──────────────────┐                   │
│  │         RDS PostgreSQL              │                   │
│  │    (Metadata & Experiments)         │                   │
│  └─────────────────────────────────────┘                   │
│                                                             │
│  ┌─────────────────────────────────────┐                   │
│  │            S3 Buckets               │                   │
│  │  • MLflow Artifacts                 │                   │
│  │  • Training Data                    │                   │
│  │  • Model Artifacts                  │                   │
│  └─────────────────────────────────────┘                   │
└─────────────────────────────────────────────────────────────┘
```

## 🔄 Prefect Workflow Orchestration

### Flow Architecture
```
Training Pipeline (Weekly)
├── Data Collection Task
├── Data Quality Check
├── Model Training Task
└── Model Validation Task

Prediction Pipeline (Daily)
├── Fresh Data Collection
├── Data Quality Check
└── Prediction Generation

Monitoring Pipeline (Every 6h)
├── Model Health Check
├── Data Drift Detection
└── Auto-retrain Trigger
```

### Scheduled Deployments
- **Training Pipeline**: Sundays at 2 AM
- **Prediction Data**: Daily at 6 AM
- **Monitoring**: Every 6 hours
- **Full Pipeline**: Saturdays at midnight

## 🚀 Deployment Steps

### Option 1: Automated Deployment
```bash
# Make deployment script executable
chmod +x deploy.sh

# Run deployment
./deploy.sh
```

### Option 2: Manual Step-by-Step

#### 1. Deploy Infrastructure
```bash
cd infrastructure/terraform
terraform init
terraform plan -var="db_password=$DB_PASSWORD"
terraform apply
```

#### 2. Build and Push Images
```bash
# Login to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin $(aws sts get-caller-identity --query Account --output text).dkr.ecr.us-east-1.amazonaws.com

# Build and push
docker build -f Dockerfile.api -t $ECR_API_URI:latest .
docker push $ECR_API_URI:latest

docker build -f Dockerfile.dashboard -t $ECR_DASHBOARD_URI:latest .
docker push $ECR_DASHBOARD_URI:latest

docker build -f Dockerfile.prefect -t $ECR_PREFECT_URI:latest .
docker push $ECR_PREFECT_URI:latest
```

#### 3. Deploy Prefect Flows
```bash
pip install prefect
python flows/deployments.py
```

## 🔧 Local Development

### Start Local Stack
```bash
# Start all services
docker-compose up -d

# Services will be available at:
# - API: http://localhost:8000
# - Dashboard: http://localhost:8501
# - MLflow: http://localhost:5000
# - Prefect: http://localhost:4200
```

### Run Prefect Flows Locally
```bash
# Start Prefect server
prefect server start

# In another terminal, run flows
python flows/main_flows.py
```

## 📊 CI/CD Pipeline

The GitHub Actions pipeline automatically:

1. **Tests**: Run unit tests, integration tests, code quality checks
2. **Security**: Vulnerability scanning with Trivy
3. **Build**: Create Docker images for all services
4. **Deploy**: Update infrastructure and deploy to AWS
5. **Monitor**: Health checks and deployment verification

### Required GitHub Secrets
```
AWS_ACCESS_KEY_ID
AWS_SECRET_ACCESS_KEY
DB_PASSWORD
PREFECT_API_URL
PREFECT_API_KEY
```

## 🔍 Monitoring & Observability

### Health Checks
- **API**: `/api/v1/health`
- **Dashboard**: `/_stcore/health`
- **MLflow**: `/health`

### Logging
- Application logs: CloudWatch Logs
- Infrastructure logs: ECS Container Insights
- Custom metrics: Prometheus/CloudWatch

### Alerting
Set up alerts for:
- Model performance degradation
- Data quality issues
- Infrastructure health
- Pipeline failures

## 🛠️ Configuration

### Environment Variables
```bash
# Application
MLFLOW_TRACKING_URI=http://mlflow:5000
USE_S3=true
AWS_DEFAULT_REGION=us-east-1

# Database
DB_HOST=postgres_endpoint
DB_USER=mlflow
DB_PASSWORD=your_password

# Prefect
PREFECT_API_URL=your_prefect_url
PREFECT_API_KEY=your_api_key
```

### Scaling Configuration
- **API**: Auto-scaling 1-10 instances
- **Dashboard**: Fixed 2 instances
- **Prefect**: 1-5 workers based on queue

## 🔒 Security

### Implemented Security Measures
- VPC with private subnets
- Security groups with minimal access
- Encrypted storage (S3, RDS)
- Non-root containers
- Secrets management
- Regular vulnerability scanning

## 📈 Performance Optimization

### Resource Allocation
- **API**: 1 vCPU, 2GB RAM
- **Dashboard**: 0.5 vCPU, 1GB RAM
- **MLflow**: 1 vCPU, 2GB RAM
- **Prefect Worker**: 2 vCPU, 4GB RAM

### Cost Optimization
- Spot instances for non-critical workloads
- S3 lifecycle policies
- Reserved instances for stable workloads
- Auto-scaling policies

## 🐛 Troubleshooting

### Common Issues

#### Deployment Fails
```bash
# Check Terraform state
terraform show

# Check ECS service status
aws ecs describe-services --cluster air-pollution-prediction-cluster

# Check container logs
aws logs tail /ecs/air-pollution-api --follow
```

#### Model Loading Issues
```bash
# Check MLflow connection
curl http://your-mlflow-url/health

# Check model registry
python -c "from mlflow import MlflowClient; print(MlflowClient().list_registered_models())"
```

#### Prefect Flow Failures
```bash
# Check flow runs
prefect flow-run ls

# View flow logs
prefect flow-run logs <flow-run-id>
```

## 📞 Support

For issues and questions:
1. Check the troubleshooting guide above
2. Review application logs in CloudWatch
3. Check GitHub Issues for known problems
4. Contact the development team

## 🎯 Next Steps

After successful deployment:
1. Configure custom domain and SSL
2. Set up monitoring dashboards
3. Configure backup strategies
4. Implement disaster recovery
5. Set up staging environment
6. Add more advanced monitoring
