# ECS Task Definition
resource "aws_ecs_task_definition" "api" {
  family                   = "banking-api"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "1024"
  memory                   = "4096"
  execution_role_arn       = aws_iam_role.ecs_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([{
    name      = "banking-api"
    image     = "${aws_ecr_repository.api.repository_url}:api-latest"
    essential = true

    portMappings = [{
      containerPort = 8000
      protocol      = "tcp"
    }]

    environment = [
      { name = "ENVIRONMENT", value = var.environment },
      { name = "MODEL_REGISTRY", value = "s3://${aws_s3_bucket.models.id}" }
    ]

    secrets = [
      {
        name      = "AWS_ACCESS_KEY_ID"
        valueFrom = aws_secretsmanager_secret.api_aws_key.arn
      },
      {
        name      = "AWS_SECRET_ACCESS_KEY"
        valueFrom = aws_secretsmanager_secret.api_aws_secret.arn
      }
    ]

    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.ecs_api.name
        "awslogs-region"        = var.aws_region
        "awslogs-stream-prefix" = "api"
      }
    }

    healthCheck = {
      command     = ["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"]
      interval    = 30
      timeout     = 5
      retries     = 3
      startPeriod = 60
    }
  }])
}

# IAM Roles
resource "aws_iam_role" "ecs_execution" {
  name = "banking-api-ecs-execution-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "ecs-tasks.amazonaws.com"
      }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "ecs_execution" {
  role       = aws_iam_role.ecs_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_role_policy" "ecs_execution_secrets" {
  name = "secrets-access"
  role = aws_iam_role.ecs_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "secretsmanager:GetSecretValue"
      ]
      Resource = [
        aws_secretsmanager_secret.api_aws_key.arn,
        aws_secretsmanager_secret.api_aws_secret.arn
      ]
    }]
  })
}

resource "aws_iam_role" "ecs_task" {
  name = "banking-api-ecs-task-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "ecs-tasks.amazonaws.com"
      }
    }]
  })
}

resource "aws_iam_role_policy" "ecs_task_s3" {
  name = "s3-access"
  role = aws_iam_role.ecs_task.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "s3:GetObject",
        "s3:ListBucket"
      ]
      Resource = [
        aws_s3_bucket.models.arn,
        "${aws_s3_bucket.models.arn}/*"
      ]
    }]
  })
}

# Secrets
resource "aws_secretsmanager_secret" "api_aws_key" {
  name                    = "banking/api/aws-key-${var.environment}"
  recovery_window_in_days = 7
}

resource "aws_secretsmanager_secret" "api_aws_secret" {
  name                    = "banking/api/aws-secret-${var.environment}"
  recovery_window_in_days = 7
}
