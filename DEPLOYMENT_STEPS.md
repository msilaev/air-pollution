# 🚀 Step-by-Step AWS Deployment Guide

## Prerequisites (30 minutes)

### 1. Install Required Tools

**AWS CLI**
```powershell
# Download and install AWS CLI v2
Invoke-WebRequest -Uri "https://awscli.amazonaws.com/AWSCLIV2.msi" -OutFile "AWSCLIV2.msi"
Start-Process msiexec.exe -ArgumentList "/i AWSCLIV2.msi /quiet" -Wait
```

**Docker Desktop**
```powershell
# Download from https://docs.docker.com/desktop/install/windows-install/
# Install and start Docker Desktop
```

**Terraform**
```powershell
# Download from https://www.terraform.io/downloads
# Extract to C:\terraform and add to PATH
$env:PATH += ";C:\terraform"
```

**Verify installations:**
```powershell
aws --version
docker --version
terraform --version
```

### 2. Configure AWS Credentials
```powershell
aws configure
# AWS Access Key ID: [Your Access Key]
# AWS Secret Access Key: [Your Secret Key]
# Default region name: us-east-1
# Default output format: json

# Test credentials
aws sts get-caller-identity
```

### 3. Clone and Setup Project
```powershell
# Navigate to your project directory
cd C:\Users\mikes\Documents\STUDY\mlops-zoomcamp\air_pollution

# Verify project structure
dir src, tests, flows, infrastructure
```

## Quick Deployment (Option 1) - 45 minutes

### Using PowerShell Script
```powershell
# Make sure you're in the project root
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Run deployment script
.\deploy.ps1 -Environment prod -Region us-east-1

# Follow the prompts and wait for completion
```

## Manual Deployment (Option 2) - 60 minutes

### Step 1: Create S3 Bucket for Terraform State
```powershell
$bucketName = "air-pollution-terraform-state-$(Get-Date -Format 'yyyyMMddHHmmss')"
aws s3 mb "s3://$bucketName" --region us-east-1
aws s3api put-bucket-versioning --bucket $bucketName --versioning-configuration Status=Enabled

# Update main.tf with your bucket name
(Get-Content infrastructure\terraform\main.tf) -replace 'bucket = "air-pollution-terraform-state"', "bucket = `"$bucketName`"" | Set-Content infrastructure\terraform\main.tf
```

### Step 2: Create ECR Repositories
```powershell
$repositories = @("air-pollution/api", "air-pollution/dashboard", "air-pollution/prefect")

foreach ($repo in $repositories) {
    try {
        aws ecr create-repository --repository-name $repo --region us-east-1
        Write-Host "✓ Created repository: $repo" -ForegroundColor Green
    }
    catch {
        Write-Host "⚠ Repository $repo may already exist" -ForegroundColor Yellow
    }
}
```

### Step 3: Build and Push Docker Images
```powershell
# Get your AWS account ID
$accountId = aws sts get-caller-identity --query Account --output text

# Login to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin "$accountId.dkr.ecr.us-east-1.amazonaws.com"

# Build and push API image
docker build -f Dockerfile.api -t air-pollution/api .
docker tag air-pollution/api:latest "$accountId.dkr.ecr.us-east-1.amazonaws.com/air-pollution/api:latest"
docker push "$accountId.dkr.ecr.us-east-1.amazonaws.com/air-pollution/api:latest"

# Build and push Dashboard image
docker build -f Dockerfile.dashboard -t air-pollution/dashboard .
docker tag air-pollution/dashboard:latest "$accountId.dkr.ecr.us-east-1.amazonaws.com/air-pollution/dashboard:latest"
docker push "$accountId.dkr.ecr.us-east-1.amazonaws.com/air-pollution/dashboard:latest"

# Build and push Prefect image
docker build -f Dockerfile.prefect -t air-pollution/prefect .
docker tag air-pollution/prefect:latest "$accountId.dkr.ecr.us-east-1.amazonaws.com/air-pollution/prefect:latest"
docker push "$accountId.dkr.ecr.us-east-1.amazonaws.com/air-pollution/prefect:latest"

Write-Host "✓ All images pushed successfully" -ForegroundColor Green
```

### Step 4: Create Terraform Variables
```powershell
$terraformVars = @"
aws_region = "us-east-1"
environment = "prod"
db_password = "$([System.Web.Security.Membership]::GeneratePassword(16, 2))"
"@

$terraformVars | Out-File -FilePath "terraform.tfvars" -Encoding UTF8
Write-Host "✓ Terraform variables created" -ForegroundColor Green
```

### Step 5: Deploy Infrastructure
```powershell
cd infrastructure\terraform

# Initialize Terraform
terraform init

# Plan deployment
terraform plan -var-file="..\..\terraform.tfvars"

# Apply deployment (this will take 10-15 minutes)
terraform apply -var-file="..\..\terraform.tfvars"

# Get outputs
terraform output

cd ..\..
```

### Step 6: Verify Deployment
```powershell
# Get load balancer DNS name
$albDns = aws elbv2 describe-load-balancers --names "air-pollution-alb" --query 'LoadBalancers[0].DNSName' --output text

Write-Host "🎉 Deployment completed!" -ForegroundColor Green
Write-Host "Load Balancer DNS: $albDns"

# Test health endpoint
try {
    $response = Invoke-RestMethod -Uri "http://$albDns/health" -TimeoutSec 30
    Write-Host "✓ Health check passed: $response" -ForegroundColor Green
}
catch {
    Write-Host "⚠ Health check failed - services may still be starting up" -ForegroundColor Yellow
}
```

## Access Your Deployed Services

After successful deployment, you can access:

- **API**: `http://<load-balancer-dns>/`
- **API Documentation**: `http://<load-balancer-dns>/docs`
- **Dashboard**: `http://<load-balancer-dns>:8501`
- **MLflow**: `http://<load-balancer-dns>:5000`
- **Prefect**: `http://<load-balancer-dns>:4200`

## Testing the Deployment

### Test API Endpoints
```powershell
$albDns = "your-load-balancer-dns"

# Test health
Invoke-RestMethod -Uri "http://$albDns/health"

# Test prediction
$predictionData = @{
    station = "Helsinki_Kallio_2"
    pollutant = "PM2.5"
    hours_ahead = 24
} | ConvertTo-Json

$headers = @{"Content-Type" = "application/json"}
Invoke-RestMethod -Uri "http://$albDns/predict" -Method Post -Body $predictionData -Headers $headers
```

### Test Dashboard
```powershell
# Open dashboard in browser
Start-Process "http://$albDns:8501"
```

## Monitoring and Maintenance

### View Logs
```powershell
# API service logs
aws logs tail /aws/ecs/air-pollution-api --follow

# Dashboard service logs
aws logs tail /aws/ecs/air-pollution-dashboard --follow

# Prefect service logs
aws logs tail /aws/ecs/air-pollution-prefect --follow
```

### Check Service Status
```powershell
# ECS service status
aws ecs describe-services --cluster air-pollution-cluster --services api-service dashboard-service prefect-service mlflow-service

# Load balancer target health
aws elbv2 describe-target-health --target-group-arn $(aws elbv2 describe-target-groups --names "air-pollution-api-tg" --query 'TargetGroups[0].TargetGroupArn' --output text)
```

### Scale Services
```powershell
# Scale API service
aws ecs update-service --cluster air-pollution-cluster --service api-service --desired-count 3

# Scale dashboard service
aws ecs update-service --cluster air-pollution-cluster --service dashboard-service --desired-count 2
```

## Troubleshooting Common Issues

### 1. Services Not Starting
```powershell
# Check ECS service events
aws ecs describe-services --cluster air-pollution-cluster --services api-service --query 'services[0].events'

# Check task definition
aws ecs describe-task-definition --task-definition air-pollution-api
```

### 2. Health Checks Failing
```powershell
# Check target group health
aws elbv2 describe-target-health --target-group-arn <target-group-arn>

# Check container logs
aws logs get-log-events --log-group-name /aws/ecs/air-pollution-api --log-stream-name <stream-name>
```

### 3. Database Connection Issues
```powershell
# Check RDS status
aws rds describe-db-instances --db-instance-identifier air-pollution-database

# Check security groups
aws ec2 describe-security-groups --group-names air-pollution-database-sg
```

## Cost Optimization

### Monitor Costs
```powershell
# Get cost breakdown
aws ce get-cost-and-usage --time-period Start=2024-01-01,End=2024-01-31 --granularity MONTHLY --metrics BlendedCost --group-by Type=DIMENSION,Key=SERVICE
```

### Optimize Resources
- Use Spot instances for development
- Enable auto-scaling for production
- Set up CloudWatch alarms for cost monitoring
- Use lifecycle policies for S3 storage

## Cleanup

### Complete Cleanup
```powershell
cd infrastructure\terraform

# Destroy all resources
terraform destroy -var-file="..\..\terraform.tfvars"

# Delete ECR repositories
aws ecr delete-repository --repository-name air-pollution/api --force
aws ecr delete-repository --repository-name air-pollution/dashboard --force
aws ecr delete-repository --repository-name air-pollution/prefect --force

# Delete S3 buckets (if needed)
aws s3 rb s3://your-terraform-state-bucket --force
aws s3 rb s3://your-mlflow-artifacts-bucket --force

cd ..\..
```

## Next Steps

1. **Configure Domain & SSL**
   - Purchase a domain name
   - Create ACM certificate
   - Update load balancer listeners

2. **Set Up CI/CD Pipeline**
   - Configure GitHub Actions
   - Automate deployments
   - Set up staging environment

3. **Enhance Security**
   - Enable VPC Flow Logs
   - Set up AWS WAF
   - Configure CloudTrail

4. **Monitoring & Alerting**
   - Set up CloudWatch dashboards
   - Configure alarms
   - Set up SNS notifications

5. **Backup & Disaster Recovery**
   - Configure automated backups
   - Set up cross-region replication
   - Test recovery procedures
