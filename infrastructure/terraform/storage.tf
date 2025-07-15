# RDS PostgreSQL for MLflow
resource "aws_db_subnet_group" "main" {
  name       = "${local.project_name}-db-subnet-group"
  subnet_ids = aws_subnet.private[*].id

  # tags = merge(local.common_tags, {
  #   Name = "${local.project_name}-db-subnet-group"
  # })
}

resource "aws_security_group" "rds" {
  name        = "${local.project_name}-rds-sg"
  description = "Security group for RDS database"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.ecs_tasks.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.common_tags, {
    Name = "${local.project_name}-rds-sg"
  })
}

resource "aws_db_instance" "main" {
  identifier                = "${local.project_name}-postgres"
  allocated_storage         = 20
  max_allocated_storage     = 100
  storage_type             = "gp2"
  engine                   = "postgres"
  engine_version           = "16.3"
  instance_class           = "db.t3.micro"
  db_name                  = "mlflow"
  username                 = var.db_username
  password                 = var.db_password
  parameter_group_name     = "default.postgres16"
  db_subnet_group_name     = aws_db_subnet_group.main.name
  vpc_security_group_ids   = [aws_security_group.rds.id]
  backup_retention_period  = 7
  backup_window           = "03:00-04:00"
  maintenance_window      = "sun:04:00-sun:05:00"
  skip_final_snapshot     = true
  deletion_protection     = false

  # tags = merge(local.common_tags, {
  #   Name = "${local.project_name}-postgres"
  # })
}

# S3 bucket for MLflow artifacts and data storage
resource "aws_s3_bucket" "mlflow_artifacts" {
  bucket = "${local.project_name}-mlflow-artifacts-${random_string.bucket_suffix.result}"

  tags = merge(local.common_tags, {
    Name = "${local.project_name}-mlflow-artifacts"
  })
}

resource "aws_s3_bucket" "data_storage" {
  bucket = "${local.project_name}-data-storage-${random_string.bucket_suffix.result}"

  tags = merge(local.common_tags, {
    Name = "${local.project_name}-data-storage"
  })
}

resource "random_string" "bucket_suffix" {
  length  = 8
  special = false
  upper   = false
}

resource "aws_s3_bucket_versioning" "mlflow_artifacts" {
  bucket = aws_s3_bucket.mlflow_artifacts.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_versioning" "data_storage" {
  bucket = aws_s3_bucket.data_storage.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "mlflow_artifacts" {
  bucket = aws_s3_bucket.mlflow_artifacts.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "data_storage" {
  bucket = aws_s3_bucket.data_storage.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}
