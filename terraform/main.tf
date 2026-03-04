terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
  backend "s3" {
    bucket = "banking-ml-terraform-state"
    key    = "infrastructure/terraform.tfstate"
    region = "us-east-1"
  }
}

provider "aws" {
  region = var.aws_region
  default_tags {
    tags = {
      Project     = "banking-ml-platform"
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}

# S3 Buckets
resource "aws_s3_bucket" "bronze" {
  bucket = "banking-ml-bronze-${var.environment}"
}

resource "aws_s3_bucket_encryption" "bronze" {
  bucket = aws_s3_bucket.bronze.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket" "silver" {
  bucket = "banking-ml-silver-${var.environment}"
}

resource "aws_s3_bucket_encryption" "silver" {
  bucket = aws_s3_bucket.silver.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket" "models" {
  bucket = "banking-ml-models-${var.environment}"
}

resource "aws_s3_bucket_versioning" "models" {
  bucket = aws_s3_bucket.models.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket" "dlq" {
  bucket = "banking-ml-dlq-${var.environment}"
}

# Kinesis Stream
resource "aws_kinesis_stream" "fraud_transactions" {
  name             = "fraud-transactions-${var.environment}"
  shard_count      = var.kinesis_shard_count
  retention_period = 24

  stream_mode_details {
    stream_mode = "PROVISIONED"
  }
}

# IAM Role for Lambda
resource "aws_iam_role" "lambda_role" {
  name = "fraud-stream-lambda-role-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "lambda.amazonaws.com"
      }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_kinesis" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaKinesisExecutionRole"
}

resource "aws_iam_role_policy" "lambda_s3" {
  name = "lambda-s3-access"
  role = aws_iam_role.lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "s3:PutObject",
        "s3:GetObject"
      ]
      Resource = [
        "${aws_s3_bucket.bronze.arn}/*",
        "${aws_s3_bucket.dlq.arn}/*"
      ]
    }]
  })
}

# Lambda Function
resource "aws_lambda_function" "fraud_processor" {
  filename      = "lambda_deployment.zip"
  function_name = "fraud-stream-processor-${var.environment}"
  role          = aws_iam_role.lambda_role.arn
  handler       = "lambda_handler.lambda_handler"
  runtime       = "python3.11"
  timeout       = 60
  memory_size   = 512

  environment {
    variables = {
      BRONZE_S3_BUCKET = aws_s3_bucket.bronze.id
      DLQ_S3_BUCKET    = aws_s3_bucket.dlq.id
      ENVIRONMENT      = var.environment
    }
  }
}

resource "aws_lambda_event_source_mapping" "kinesis_trigger" {
  event_source_arn  = aws_kinesis_stream.fraud_transactions.arn
  function_name     = aws_lambda_function.fraud_processor.arn
  starting_position = "LATEST"
  batch_size        = 1000
  maximum_batching_window_in_seconds = 60
}

# ECS Cluster
resource "aws_ecs_cluster" "banking_ml" {
  name = "banking-ml-cluster-${var.environment}"
}

# ECR Repository
resource "aws_ecr_repository" "api" {
  name                 = "banking-ml-api"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }
}

# Outputs
output "bronze_bucket" {
  value = aws_s3_bucket.bronze.id
}

output "silver_bucket" {
  value = aws_s3_bucket.silver.id
}

output "models_bucket" {
  value = aws_s3_bucket.models.id
}

output "kinesis_stream" {
  value = aws_kinesis_stream.fraud_transactions.name
}

output "ecs_cluster" {
  value = aws_ecs_cluster.banking_ml.name
}
