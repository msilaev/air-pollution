# PowerShell deployment script for Windows
# Air Pollution Prediction MLOps Pipeline - AWS Deployment

param(
    [string]$Environment = "prod",
    [string]$Region = "us-east-1",
    [string]$Action = "deploy",
    [switch]$SkipTests = $false,
    [switch]$Force = $false
)

# Configuration
$ErrorActionPreference = "Stop"
$ProjectName = "air-pollution-prediction"
$AwsAccountId = ""

# Colors for output
$Green = "Green"
$Yellow = "Yellow"
$Red = "Red"

function Write-Info {
    param([string]$Message)
    Write-Host "[INFO] $Message" -ForegroundColor $Green
}

function Write-Warn {
    param([string]$Message)
    Write-Host "[WARN] $Message" -ForegroundColor $Yellow
}

function Write-Error {
    param([string]$Message)
    Write-Host "[ERROR] $Message" -ForegroundColor $Red
}

function Test-Prerequisites {
    Write-Info "Checking prerequisites..."

    # Check AWS CLI
    try {
        $null = aws --version
        Write-Info "✓ AWS CLI found"
    }
    catch {
        Write-Error "AWS CLI not found. Please install AWS CLI first."
        exit 1
    }

    # Check Docker
    try {
        $null = docker --version
        Write-Info "✓ Docker found"
    }
    catch {
        Write-Error "Docker not found. Please install Docker Desktop first."
        exit 1
    }

    # Check Terraform
    try {
        $null = terraform --version
        Write-Info "✓ Terraform found"
    }
    catch {
        Write-Error "Terraform not found. Please install Terraform first."
        exit 1
    }

    # Check AWS credentials
    try {
        $global:AwsAccountId = aws sts get-caller-identity --query Account --output text
        Write-Info "✓ AWS credentials configured (Account: $AwsAccountId)"
    }
    catch {
        Write-Error "AWS credentials not configured. Run 'aws configure' first."
        exit 1
    }
}

function New-S3StateBackend {
    Write-Info "Setting up S3 backend for Terraform state..."

    $BucketName = "air-pollution-terraform-state-$(Get-Date -Format 'yyyyMMddHHmmss')"

    try {
        aws s3 mb "s3://$BucketName" --region $Region
        aws s3api put-bucket-versioning --bucket $BucketName --versioning-configuration Status=Enabled

        $EncryptionConfig = @{
            Rules = @(
                @{
                    ApplyServerSideEncryptionByDefault = @{
                        SSEAlgorithm = "AES256"
                    }
                }
            )
        } | ConvertTo-Json -Depth 3 -Compress

        aws s3api put-bucket-encryption --bucket $BucketName --server-side-encryption-configuration $EncryptionConfig

        Write-Info "✓ Created S3 bucket: $BucketName"
        return $BucketName
    }
    catch {
        Write-Error "Failed to create S3 bucket: $_"
        exit 1
    }
}

function New-ECRRepositories {
    Write-Info "Creating ECR repositories..."

    $Repositories = @("air-pollution/api", "air-pollution/dashboard", "air-pollution/prefect")

    foreach ($Repo in $Repositories) {
        try {
            aws ecr create-repository --repository-name $Repo --region $Region 2>$null
            Write-Info "✓ Created ECR repository: $Repo"
        }
        catch {
            Write-Warn "ECR repository $Repo may already exist"
        }
    }
}

function Build-PushDockerImages {
    Write-Info "Building and pushing Docker images..."

    # Get ECR login
    $LoginPassword = aws ecr get-login-password --region $Region
    $LoginPassword | docker login --username AWS --password-stdin "$AwsAccountId.dkr.ecr.$Region.amazonaws.com"

    # Build and push images
    $Images = @(
        @{Name="api"; Dockerfile="Dockerfile.api"},
        @{Name="dashboard"; Dockerfile="Dockerfile.dashboard"},
        @{Name="prefect"; Dockerfile="Dockerfile.prefect"}
    )

    foreach ($Image in $Images) {
        $LocalTag = "air-pollution/$($Image.Name):latest"
        $RemoteTag = "$AwsAccountId.dkr.ecr.$Region.amazonaws.com/air-pollution/$($Image.Name):latest"

        Write-Info "Building $LocalTag..."
        docker build -f $Image.Dockerfile -t $LocalTag .

        Write-Info "Tagging and pushing $RemoteTag..."
        docker tag $LocalTag $RemoteTag
        docker push $RemoteTag

        Write-Info "✓ Pushed $RemoteTag"
    }
}

function Deploy-Infrastructure {
    Write-Info "Deploying infrastructure with Terraform..."

    # Create terraform variables file
    $TerraformVars = @"
aws_region = "$Region"
environment = "$Environment"
db_password = "$(New-Guid)"
"@

    $TerraformVars | Out-File -FilePath "terraform.tfvars" -Encoding UTF8

    # Initialize and apply Terraform
    Set-Location "infrastructure/terraform"

    try {
        terraform init
        terraform plan -var-file="../../terraform.tfvars"

        if ($Force -or (Read-Host "Deploy infrastructure? (y/N)") -eq "y") {
            terraform apply -var-file="../../terraform.tfvars" -auto-approve
            Write-Info "✓ Infrastructure deployed successfully"
        }
    }
    catch {
        Write-Error "Terraform deployment failed: $_"
        exit 1
    }
    finally {
        Set-Location "../.."
    }
}

function Test-Deployment {
    Write-Info "Testing deployment..."

    # Get load balancer DNS name
    $LoadBalancerDns = aws elbv2 describe-load-balancers --names "air-pollution-alb" --query 'LoadBalancers[0].DNSName' --output text

    if ($LoadBalancerDns -and $LoadBalancerDns -ne "None") {
        Write-Info "Load Balancer DNS: $LoadBalancerDns"

        # Test health endpoint
        try {
            $Response = Invoke-RestMethod -Uri "http://$LoadBalancerDns/health" -TimeoutSec 30
            Write-Info "✓ Health check passed: $Response"
        }
        catch {
            Write-Warn "Health check failed, but deployment may still be starting up"
        }

        # Test prediction endpoint
        try {
            $PredictionData = @{
                station = "Helsinki_Kallio_2"
                pollutant = "PM2.5"
                hours_ahead = 24
            } | ConvertTo-Json

            $Headers = @{"Content-Type" = "application/json"}
            $Response = Invoke-RestMethod -Uri "http://$LoadBalancerDns/predict" -Method Post -Body $PredictionData -Headers $Headers -TimeoutSec 30
            Write-Info "✓ Prediction endpoint working: $($Response.prediction)"
        }
        catch {
            Write-Warn "Prediction endpoint test failed: $_"
        }
    }
    else {
        Write-Warn "Could not find load balancer DNS name"
    }
}

function Remove-Infrastructure {
    Write-Info "Destroying infrastructure..."

    Set-Location "infrastructure/terraform"

    try {
        if ($Force -or (Read-Host "Destroy all infrastructure? This cannot be undone! (y/N)") -eq "y") {
            terraform destroy -var-file="../../terraform.tfvars" -auto-approve
            Write-Info "✓ Infrastructure destroyed"
        }
    }
    catch {
        Write-Error "Failed to destroy infrastructure: $_"
    }
    finally {
        Set-Location "../.."
    }

    # Clean up ECR repositories
    $Repositories = @("air-pollution/api", "air-pollution/dashboard", "air-pollution/prefect")

    foreach ($Repo in $Repositories) {
        try {
            aws ecr delete-repository --repository-name $Repo --force --region $Region 2>$null
            Write-Info "✓ Deleted ECR repository: $Repo"
        }
        catch {
            Write-Warn "Failed to delete ECR repository: $Repo"
        }
    }
}

function Show-Usage {
    Write-Host @"
Air Pollution Prediction - AWS Deployment Script

Usage: .\deploy.ps1 [OPTIONS]

Options:
    -Environment    Deployment environment (dev, staging, prod) [default: prod]
    -Region         AWS region [default: us-east-1]
    -Action         Action to perform (deploy, destroy, test) [default: deploy]
    -SkipTests      Skip running tests before deployment
    -Force          Skip confirmation prompts

Examples:
    .\deploy.ps1                                    # Deploy to prod
    .\deploy.ps1 -Environment dev                   # Deploy to dev environment
    .\deploy.ps1 -Action destroy -Force             # Destroy infrastructure
    .\deploy.ps1 -Action test                       # Test existing deployment
"@
}

# Main execution
Write-Host "🚀 Air Pollution Prediction - AWS Deployment" -ForegroundColor Cyan
Write-Host "Environment: $Environment | Region: $Region | Action: $Action`n"

switch ($Action.ToLower()) {
    "deploy" {
        Test-Prerequisites

        if (-not $SkipTests) {
            Write-Info "Running tests..."
            try {
                pytest tests/ -v
                Write-Info "✓ All tests passed"
            }
            catch {
                Write-Error "Tests failed. Use -SkipTests to bypass."
                exit 1
            }
        }

        $StateBackend = New-S3StateBackend
        New-ECRRepositories
        Build-PushDockerImages
        Deploy-Infrastructure

        Write-Info "Waiting for services to start up..."
        Start-Sleep -Seconds 60
        Test-Deployment

        Write-Info "🎉 Deployment completed successfully!"
        Write-Info "Next steps:"
        Write-Info "1. Configure your domain name and SSL certificate"
        Write-Info "2. Set up monitoring and alerting"
        Write-Info "3. Configure CI/CD pipeline"
    }

    "destroy" {
        Test-Prerequisites
        Remove-Infrastructure
        Write-Info "🧹 Cleanup completed"
    }

    "test" {
        Test-Prerequisites
        Test-Deployment
    }

    default {
        Write-Error "Unknown action: $Action"
        Show-Usage
        exit 1
    }
}
