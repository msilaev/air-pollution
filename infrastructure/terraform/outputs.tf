# Outputs for the Air Pollution Prediction System deployment

output "vpc_id" {
  description = "ID of the VPC"
  value       = aws_vpc.main.id
}

output "load_balancer_dns_name" {
  description = "DNS name of the load balancer"
  value       = aws_lb.main.dns_name
}

output "load_balancer_zone_id" {
  description = "Zone ID of the load balancer"
  value       = aws_lb.main.zone_id
}

output "ecs_cluster_name" {
  description = "Name of the ECS cluster"
  value       = aws_ecs_cluster.main.name
}

output "database_endpoint" {
  description = "RDS instance endpoint"
  value       = aws_db_instance.main.endpoint
  sensitive   = true
}

output "s3_mlflow_artifacts_bucket" {
  description = "S3 bucket for MLflow artifacts"
  value       = aws_s3_bucket.mlflow_artifacts.bucket
}

output "s3_data_storage_bucket" {
  description = "S3 bucket for data storage"
  value       = aws_s3_bucket.data_storage.bucket
}

output "api_url" {
  description = "API endpoint URL"
  value       = "http://${aws_lb.main.dns_name}"
}

output "dashboard_url" {
  description = "Dashboard URL"
  value       = "http://${aws_lb.main.dns_name}:8501"
}

output "mlflow_url" {
  description = "MLflow tracking server URL"
  value       = "http://${aws_lb.main.dns_name}:5000"
}

output "prefect_url" {
  description = "Prefect server URL"
  value       = "http://${aws_lb.main.dns_name}:4200"
}

output "deployment_summary" {
  description = "Deployment summary information"
  value = {
    environment     = var.environment
    region         = var.aws_region
    project_name   = local.project_name
    services = {
      api       = "http://${aws_lb.main.dns_name}"
      dashboard = "http://${aws_lb.main.dns_name}:8501"
      mlflow    = "http://${aws_lb.main.dns_name}:5000"
      prefect   = "http://${aws_lb.main.dns_name}:4200"
    }
    documentation = "http://${aws_lb.main.dns_name}/docs"
  }
}
