#!/bin/bash

# Deployment script for Air Pollution Prediction MLOps Pipeline
set -e

echo "🚀 Starting deployment of Air Pollution Prediction MLOps Pipeline"

# Configuration
AWS_REGION=${AWS_REGION:-us-east-1}
PROJECT_NAME="air-pollution-prediction"
ENVIRONMENT=${ENVIRONMENT:-prod}

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Helper functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."

    # Check if AWS CLI is installed and configured
    if ! command -v aws &> /dev/null; then
        log_error "AWS CLI is not installed. Please install it first."
        exit 1
    fi

    # Check if Docker is installed
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed. Please install it first."
        exit 1
    fi

    # Check if Terraform is installed
    if ! command -v terraform &> /dev/null; then
        log_error "Terraform is not installed. Please install it first."
        exit 1
    fi

    # Check AWS credentials
    if ! aws sts get-caller-identity &> /dev/null; then
        log_error "AWS credentials not configured. Please run 'aws configure'."
        exit 1
    fi

    log_info "Prerequisites check passed ✅"
}

# Create S3 bucket for Terraform state
create_terraform_state_bucket() {
    log_info "Creating S3 bucket for Terraform state..."

    BUCKET_NAME="${PROJECT_NAME}-terraform-state-$(openssl rand -hex 4)"

    if aws s3api head-bucket --bucket $BUCKET_NAME 2>/dev/null; then
        log_warn "Bucket $BUCKET_NAME already exists"
    else
        aws s3api create-bucket \
            --bucket $BUCKET_NAME \
            --region $AWS_REGION \
            --create-bucket-configuration LocationConstraint=$AWS_REGION 2>/dev/null || true

        aws s3api put-bucket-versioning \
            --bucket $BUCKET_NAME \
            --versioning-configuration Status=Enabled

        log_info "Created Terraform state bucket: $BUCKET_NAME"
        echo "Update backend configuration in main.tf with bucket name: $BUCKET_NAME"
    fi
}

# Deploy infrastructure with Terraform
deploy_infrastructure() {
    log_info "Deploying infrastructure with Terraform..."

    cd infrastructure/terraform

    # Initialize Terraform
    terraform init

    # Create workspace if it doesn't exist
    terraform workspace select $ENVIRONMENT 2>/dev/null || terraform workspace new $ENVIRONMENT

    # Plan deployment
    terraform plan \
        -var="environment=$ENVIRONMENT" \
        -var="aws_region=$AWS_REGION" \
        -var="db_password=${DB_PASSWORD:-$(openssl rand -base64 32)}" \
        -out=tfplan

    # Apply deployment
    log_info "Applying Terraform configuration..."
    terraform apply -auto-approve tfplan

    # Get outputs
    ECR_API_URI=$(terraform output -raw ecr_api_repository_url)
    ECR_DASHBOARD_URI=$(terraform output -raw ecr_dashboard_repository_url)
    ECR_PREFECT_URI=$(terraform output -raw ecr_prefect_repository_url)

    cd ../..

    log_info "Infrastructure deployment completed ✅"
    echo "ECR API Repository: $ECR_API_URI"
    echo "ECR Dashboard Repository: $ECR_DASHBOARD_URI"
    echo "ECR Prefect Repository: $ECR_PREFECT_URI"
}

# Build and push Docker images
build_and_push_images() {
    log_info "Building and pushing Docker images..."

    # Login to ECR
    aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $(aws sts get-caller-identity --query Account --output text).dkr.ecr.$AWS_REGION.amazonaws.com

    # Build and push API image
    log_info "Building API image..."
    docker build -f Dockerfile.api -t $ECR_API_URI:latest .
    docker push $ECR_API_URI:latest

    # Build and push Dashboard image
    log_info "Building Dashboard image..."
    docker build -f Dockerfile.dashboard -t $ECR_DASHBOARD_URI:latest .
    docker push $ECR_DASHBOARD_URI:latest

    # Build and push Prefect image
    log_info "Building Prefect image..."
    docker build -f Dockerfile.prefect -t $ECR_PREFECT_URI:latest .
    docker push $ECR_PREFECT_URI:latest

    log_info "Docker images built and pushed ✅"
}

# Deploy Prefect flows
deploy_prefect_flows() {
    log_info "Deploying Prefect flows..."

    # Install Prefect if not installed
    if ! command -v prefect &> /dev/null; then
        log_info "Installing Prefect..."
        pip install prefect
    fi

    # Set Prefect API URL (you'll need to update this with your Prefect Cloud URL)
    if [ -n "$PREFECT_API_URL" ]; then
        prefect config set PREFECT_API_URL=$PREFECT_API_URL
    fi

    if [ -n "$PREFECT_API_KEY" ]; then
        prefect config set PREFECT_API_KEY=$PREFECT_API_KEY
    fi

    # Deploy flows
    python flows/deployments.py

    log_info "Prefect flows deployed ✅"
}

# Run deployment
main() {
    log_info "🎯 Air Pollution Prediction MLOps Deployment"
    log_info "Environment: $ENVIRONMENT"
    log_info "AWS Region: $AWS_REGION"
    echo ""

    check_prerequisites
    create_terraform_state_bucket
    deploy_infrastructure
    build_and_push_images
    deploy_prefect_flows

    log_info "🎉 Deployment completed successfully!"
    echo ""
    echo "Next steps:"
    echo "1. Update your DNS to point to the Load Balancer"
    echo "2. Configure SSL certificate if using custom domain"
    echo "3. Set up monitoring and alerting"
    echo "4. Configure Prefect workers"
    echo ""
    echo "Access points:"
    echo "- API: http://$(terraform -chdir=infrastructure/terraform output -raw load_balancer_dns)/api/v1/health"
    echo "- Dashboard: http://$(terraform -chdir=infrastructure/terraform output -raw load_balancer_dns)"
    echo "- MLflow: http://$(terraform -chdir=infrastructure/terraform output -raw load_balancer_dns):5000"
}

# Run main function
main "$@"
