# AWS Deployment Guide for Air Pollution Prediction System

## 🎯 Overview
This guide walks you through deploying the complete MLOps air pollution prediction system to AWS using ECS Fargate, RDS, and supporting services.

## 📋 Prerequisites

### 1. AWS Account Setup
- Active AWS account with appropriate permissions
- AWS CLI installed and configured
- Terraform installed (>= 1.0)
- Docker installed and running

### 2. Required Tools
```bash
# Install AWS CLI
curl "https://awscli.amazonaws.com/awscli-exe-windows-x86_64.msi" -o "AWSCLIV2.msi"
msiexec /i AWSCLIV2.msi

# Install Terraform
# Download from https://www.terraform.io/downloads

# Verify installations
aws --version
terraform --version
docker --version
```

### 3. AWS Credentials Configuration
```bash
aws configure
# Enter your AWS Access Key ID
# Enter your AWS Secret Access Key
# Default region: us-east-1
# Default output format: json
```

## 🔧 Pre-Deployment Setup

### 1. Create S3 Bucket for Terraform State
```bash
aws s3 mb s3://air-pollution-terraform-state-$(date +%s)
aws s3api put-bucket-versioning --bucket air-pollution-terraform-state-$(date +%s) --versioning-configuration Status=Enabled
```

### 2. Create ECR Repositories
```bash
# Create repositories for our container images
aws ecr create-repository --repository-name air-pollution/api
aws ecr create-repository --repository-name air-pollution/dashboard
aws ecr create-repository --repository-name air-pollution/prefect
```

### 3. Build and Push Docker Images
```bash
# Get ECR login token
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <account-id>.dkr.ecr.us-east-1.amazonaws.com

# Build and push API image
docker build -f Dockerfile.api -t air-pollution/api .
docker tag air-pollution/api:latest <account-id>.dkr.ecr.us-east-1.amazonaws.com/air-pollution/api:latest
docker push <account-id>.dkr.ecr.us-east-1.amazonaws.com/air-pollution/api:latest

# Build and push Dashboard image
docker build -f Dockerfile.dashboard -t air-pollution/dashboard .
docker tag air-pollution/dashboard:latest <account-id>.dkr.ecr.us-east-1.amazonaws.com/air-pollution/dashboard:latest
docker push <account-id>.dkr.ecr.us-east-1.amazonaws.com/air-pollution/dashboard:latest

# Build and push Prefect image
docker build -f Dockerfile.prefect -t air-pollution/prefect .
docker tag air-pollution/prefect:latest <account-id>.dkr.ecr.us-east-1.amazonaws.com/air-pollution/prefect:latest
docker push <account-id>.dkr.ecr.us-east-1.amazonaws.com/air-pollution/prefect:latest
```

## 🚀 Deployment Steps

### 1. Configure Environment Variables
Create a `.env.aws` file:
```bash
cat > .env.aws << EOF
AWS_REGION=us-east-1
ENVIRONMENT=prod
DB_PASSWORD=your-secure-password
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
MLFLOW_BUCKET_NAME=air-pollution-mlflow-artifacts-$(date +%s)
EOF
```

### 2. Initialize Terraform
```bash
cd infrastructure/terraform
terraform init
```

### 3. Plan Deployment
```bash
terraform plan -var-file="../../.env.aws"
```

### 4. Deploy Infrastructure
```bash
terraform apply -var-file="../../.env.aws"
```

### 5. Deploy ECS Services
```bash
# Update ECS services with new task definitions
aws ecs update-service --cluster air-pollution-cluster --service api-service --force-new-deployment
aws ecs update-service --cluster air-pollution-cluster --service dashboard-service --force-new-deployment
aws ecs update-service --cluster air-pollution-cluster --service prefect-service --force-new-deployment
```

## 📊 Post-Deployment Verification

### 1. Check Service Health
```bash
# Get load balancer URL
aws elbv2 describe-load-balancers --names air-pollution-alb --query 'LoadBalancers[0].DNSName' --output text

# Test API health
curl https://<lb-dns-name>/health

# Test predictions endpoint
curl -X POST https://<lb-dns-name>/predict \
  -H "Content-Type: application/json" \
  -d '{"station": "Helsinki_Kallio_2", "pollutant": "PM2.5", "hours_ahead": 24}'
```

### 2. Access Services
- **API Documentation**: `https://<lb-dns-name>/docs`
- **Dashboard**: `https://<lb-dns-name>:8501`
- **MLflow UI**: `https://<lb-dns-name>:5000`
- **Prefect UI**: `https://<lb-dns-name>:4200`

### 3. Monitor Logs
```bash
# API service logs
aws logs tail /aws/ecs/air-pollution-api --follow

# Dashboard service logs
aws logs tail /aws/ecs/air-pollution-dashboard --follow

# Prefect service logs
aws logs tail /aws/ecs/air-pollution-prefect --follow
```

## 🔒 Security Configuration

### 1. SSL/TLS Certificate
```bash
# Request ACM certificate (if you have a domain)
aws acm request-certificate \
    --domain-name yourdomain.com \
    --validation-method DNS \
    --region us-east-1
```

### 2. Security Groups
The Terraform configuration automatically creates security groups with:
- ALB: HTTPS (443) and HTTP (80) from internet
- ECS Tasks: Only from ALB on required ports
- RDS: Only from ECS tasks on port 5432

### 3. IAM Roles
- ECS Task Execution Role: Pulls images, writes logs
- ECS Task Role: Access to S3, CloudWatch, SQS

## 📈 Monitoring and Alerting

### 1. CloudWatch Dashboards
```bash
# Create custom dashboard
aws cloudwatch put-dashboard --dashboard-name "AirPollutionMetrics" --dashboard-body file://cloudwatch-dashboard.json
```

### 2. CloudWatch Alarms
```bash
# CPU utilization alarm
aws cloudwatch put-metric-alarm \
    --alarm-name "HighCPUUtilization" \
    --alarm-description "Alarm when CPU exceeds 80%" \
    --metric-name CPUUtilization \
    --namespace AWS/ECS \
    --statistic Average \
    --period 300 \
    --threshold 80 \
    --comparison-operator GreaterThanThreshold \
    --evaluation-periods 2
```

## 🔄 CI/CD Pipeline

### 1. GitHub Actions Workflow
The repository includes `.github/workflows/ci-cd.yml` for automated:
- Testing on pull requests
- Building and pushing Docker images
- Deploying to ECS on main branch merges

### 2. Manual Deployment Updates
```bash
# Update a specific service
./deploy.sh --service api --environment prod

# Full redeployment
./deploy.sh --full --environment prod

# Rollback to previous version
./deploy.sh --rollback --service api
```

## 💰 Cost Optimization

### 1. Resource Sizing
- **ECS Tasks**: Start with t3.medium, monitor and adjust
- **RDS**: db.t3.micro for development, db.t3.small for production
- **ALB**: Charged per hour and LCU usage

### 2. Auto Scaling
Configured to scale based on:
- CPU utilization (target: 70%)
- Memory utilization (target: 80%)
- Request count per target

### 3. Cost Monitoring
```bash
# Enable cost allocation tags
aws ce get-cost-and-usage \
    --time-period Start=2024-01-01,End=2024-01-31 \
    --granularity MONTHLY \
    --metrics BlendedCost \
    --group-by Type=DIMENSION,Key=SERVICE
```

## 🛠️ Troubleshooting

### Common Issues

1. **ECS Tasks Not Starting**
   ```bash
   # Check task definition
   aws ecs describe-task-definition --task-definition air-pollution-api
   
   # Check service events
   aws ecs describe-services --cluster air-pollution-cluster --services api-service
   ```

2. **Database Connection Issues**
   ```bash
   # Check RDS status
   aws rds describe-db-instances --db-instance-identifier air-pollution-db
   
   # Test connectivity from ECS task
   aws ecs run-task --cluster air-pollution-cluster --task-definition troubleshoot
   ```

3. **Load Balancer Health Checks Failing**
   ```bash
   # Check target group health
   aws elbv2 describe-target-health --target-group-arn <target-group-arn>
   ```

### Debugging Commands
```bash
# Connect to running ECS task
aws ecs execute-command \
    --cluster air-pollution-cluster \
    --task <task-arn> \
    --container api \
    --interactive \
    --command "/bin/bash"

# View recent CloudWatch logs
aws logs tail /aws/ecs/air-pollution-api --since 1h
```

## 🔄 Cleanup

### Remove All Resources
```bash
# Destroy Terraform resources
cd infrastructure/terraform
terraform destroy -var-file="../../.env.aws"

# Delete ECR repositories
aws ecr delete-repository --repository-name air-pollution/api --force
aws ecr delete-repository --repository-name air-pollution/dashboard --force
aws ecr delete-repository --repository-name air-pollution/prefect --force

# Delete S3 buckets
aws s3 rb s3://your-terraform-state-bucket --force
aws s3 rb s3://your-mlflow-artifacts-bucket --force
```

## 📚 Additional Resources

- [AWS ECS Best Practices](https://docs.aws.amazon.com/AmazonECS/latest/bestpracticesguide/)
- [Terraform AWS Provider Documentation](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)
- [MLflow on AWS](https://mlflow.org/docs/latest/tracking.html#amazon-s3)
- [Prefect Cloud Documentation](https://docs.prefect.io/latest/)

## 📞 Support

For deployment issues:
1. Check the troubleshooting section above
2. Review AWS CloudWatch logs
3. Consult the project README.md
4. Open an issue in the project repository
