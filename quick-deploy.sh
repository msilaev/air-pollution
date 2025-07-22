#!/bin/bash

# Quick AWS Deployment Script for Air Pollution Prediction System
# This script automates the entire deployment process

set -e

echo "🚀 Air Pollution Prediction System - Quick AWS Deployment"
echo "=========================================================="

# Configuration
export AWS_REGION=${AWS_REGION:-us-east-1}
export ENVIRONMENT=${ENVIRONMENT:-prod}
export PROJECT_NAME="air-pollution-prediction"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Step 1: Prerequisites Check
log_info "Step 1: Checking prerequisites..."

if ! command -v aws &> /dev/null; then
    log_error "AWS CLI not found. Please install AWS CLI first."
    exit 1
fi

if ! command -v docker &> /dev/null; then
    log_error "Docker not found. Please install Docker first."
    exit 1
fi

if ! command -v terraform &> /dev/null; then
    log_error "Terraform not found. Please install Terraform first."
    exit 1
fi

# Get AWS Account ID
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
log_info "✓ AWS Account ID: $AWS_ACCOUNT_ID"

# Step 2: Create S3 bucket for Terraform state
log_info "Step 2: Creating S3 bucket for Terraform state..."

TERRAFORM_BUCKET="${PROJECT_NAME}-terraform-state-$(date +%s)"
aws s3 mb s3://$TERRAFORM_BUCKET --region $AWS_REGION
aws s3api put-bucket-versioning --bucket $TERRAFORM_BUCKET --versioning-configuration Status=Enabled
log_info "✓ Created Terraform state bucket: $TERRAFORM_BUCKET"

# Step 3: Create ECR repositories
log_info "Step 3: Creating ECR repositories..."

for repo in api dashboard prefect; do
    aws ecr create-repository --repository-name ${PROJECT_NAME}/${repo} --region $AWS_REGION 2>/dev/null || log_warn "Repository ${repo} may already exist"
done
log_info "✓ ECR repositories created"

# Step 4: Build and push Docker images
log_info "Step 4: Building and pushing Docker images..."

# Login to ECR
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com

# Build and push images
for service in api dashboard prefect; do
    log_info "Building ${service} image..."

    case $service in
        "api")
            dockerfile="Dockerfile.api"
            ;;
        "dashboard")
            dockerfile="Dockerfile.dashboard"
            ;;
        "prefect")
            dockerfile="Dockerfile.prefect"
            ;;
    esac

    local_tag="${PROJECT_NAME}/${service}:latest"
    remote_tag="$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/${PROJECT_NAME}/${service}:latest"

    docker build -f $dockerfile -t $local_tag .
    docker tag $local_tag $remote_tag
    docker push $remote_tag

    log_info "✓ Pushed ${service} image"
done

# Step 5: Generate Terraform variables
log_info "Step 5: Generating Terraform configuration..."

cat > terraform.tfvars << EOF
aws_region = "$AWS_REGION"
environment = "$ENVIRONMENT"
db_password = "$(openssl rand -base64 32)"
aws_account_id = "$AWS_ACCOUNT_ID"
terraform_state_bucket = "$TERRAFORM_BUCKET"
EOF

# Update main.tf with the correct bucket name
sed -i.bak "s/bucket = \"air-pollution-terraform-state\"/bucket = \"$TERRAFORM_BUCKET\"/" infrastructure/terraform/main.tf

# Step 6: Deploy infrastructure
log_info "Step 6: Deploying infrastructure with Terraform..."

cd infrastructure/terraform

terraform init
terraform plan -var-file="../../terraform.tfvars"

read -p "Deploy infrastructure? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    terraform apply -var-file="../../terraform.tfvars" -auto-approve
    log_info "✓ Infrastructure deployed successfully"
else
    log_warn "Deployment cancelled by user"
    exit 0
fi

cd ../..

# Step 7: Get deployment outputs
log_info "Step 7: Getting deployment information..."

cd infrastructure/terraform
ALB_DNS=$(terraform output -raw load_balancer_dns_name 2>/dev/null || echo "Not available")
cd ../..

log_info "✓ Load Balancer DNS: $ALB_DNS"

# Step 8: Wait for services to start
log_info "Step 8: Waiting for services to start up..."
sleep 60

# Step 9: Test deployment
log_info "Step 9: Testing deployment..."

if [ "$ALB_DNS" != "Not available" ]; then
    # Test health endpoint
    if curl -f -s "http://$ALB_DNS/health" > /dev/null; then
        log_info "✓ Health check passed"
    else
        log_warn "Health check failed - services may still be starting"
    fi

    # Test prediction endpoint
    if curl -f -s -X POST "http://$ALB_DNS/predict" \
        -H "Content-Type: application/json" \
        -d '{"station":"Helsinki_Kallio_2","pollutant":"PM2.5","hours_ahead":24}' > /dev/null; then
        log_info "✓ Prediction endpoint working"
    else
        log_warn "Prediction endpoint test failed - may need more time to start"
    fi
fi

# Step 10: Display access information
log_info "Step 10: Deployment Summary"
echo "================================"
echo
echo "🎉 Deployment completed successfully!"
echo
echo "Service URLs:"
echo "  API:       http://$ALB_DNS"
echo "  Dashboard: http://$ALB_DNS:8501"
echo "  MLflow:    http://$ALB_DNS:5000"
echo "  Prefect:   http://$ALB_DNS:4200"
echo
echo "API Documentation: http://$ALB_DNS/docs"
echo
echo "Next Steps:"
echo "1. Configure your domain name and SSL certificate"
echo "2. Set up monitoring and alerting"
echo "3. Configure CI/CD pipeline"
echo "4. Review security settings"
echo
echo "To destroy the infrastructure:"
echo "  cd infrastructure/terraform"
echo "  terraform destroy -var-file=\"../../terraform.tfvars\""
echo

log_info "Deployment script completed successfully!"
