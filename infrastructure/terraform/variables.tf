# Variables for Terraform configuration
variable "aws_region" {
  description = "AWS region for deployment"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "prod"
}

variable "instance_type" {
  description = "EC2 instance type for ECS tasks"
  type        = string
  default     = "t3.medium"
}

variable "min_capacity" {
  description = "Minimum number of ECS tasks"
  type        = number
  default     = 1
}

variable "max_capacity" {
  description = "Maximum number of ECS tasks"
  type        = number
  default     = 10
}

variable "api_port" {
  description = "Port for the API service"
  type        = number
  default     = 8000
}

variable "dashboard_port" {
  description = "Port for the dashboard service"
  type        = number
  default     = 8501
}

variable "db_username" {
  description = "Database username"
  type        = string
  default     = "mlflow"
}

variable "db_password" {
  description = "Database password"
  type        = string
  sensitive   = true
}

variable "domain_name" {
  description = "Domain name for the application"
  type        = string
  default     = ""
}

variable "certificate_arn" {
  description = "ARN of SSL certificate for HTTPS"
  type        = string
  default     = ""
}
