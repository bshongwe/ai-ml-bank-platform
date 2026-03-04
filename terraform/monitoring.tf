# CloudWatch Log Groups
resource "aws_cloudwatch_log_group" "ecs_api" {
  name              = "/ecs/banking-api"
  retention_in_days = 30
}

resource "aws_cloudwatch_log_group" "lambda" {
  name              = "/aws/lambda/fraud-stream-processor-${var.environment}"
  retention_in_days = 30
}

# API Alarms
resource "aws_cloudwatch_metric_alarm" "api_high_cpu" {
  alarm_name          = "banking-api-high-cpu-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "CPUUtilization"
  namespace           = "AWS/ECS"
  period              = 300
  statistic           = "Average"
  threshold           = 80
  alarm_description   = "API CPU utilization is too high"
  alarm_actions       = [aws_sns_topic.alerts.arn]

  dimensions = {
    ServiceName = aws_ecs_service.api.name
    ClusterName = aws_ecs_cluster.banking_ml.name
  }
}

resource "aws_cloudwatch_metric_alarm" "api_high_memory" {
  alarm_name          = "banking-api-high-memory-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "MemoryUtilization"
  namespace           = "AWS/ECS"
  period              = 300
  statistic           = "Average"
  threshold           = 85
  alarm_description   = "API memory utilization is too high"
  alarm_actions       = [aws_sns_topic.alerts.arn]

  dimensions = {
    ServiceName = aws_ecs_service.api.name
    ClusterName = aws_ecs_cluster.banking_ml.name
  }
}

resource "aws_cloudwatch_metric_alarm" "alb_5xx_errors" {
  alarm_name          = "banking-api-5xx-errors-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "HTTPCode_Target_5XX_Count"
  namespace           = "AWS/ApplicationELB"
  period              = 60
  statistic           = "Sum"
  threshold           = 10
  alarm_description   = "API returning too many 5xx errors"
  alarm_actions       = [aws_sns_topic.alerts.arn]

  dimensions = {
    LoadBalancer = aws_lb.api.arn_suffix
  }
}

# Lambda Alarms
resource "aws_cloudwatch_metric_alarm" "lambda_errors" {
  alarm_name          = "fraud-processor-errors-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = 300
  statistic           = "Sum"
  threshold           = 5
  alarm_description   = "Lambda function errors detected"
  alarm_actions       = [aws_sns_topic.alerts.arn]

  dimensions = {
    FunctionName = aws_lambda_function.fraud_processor.function_name
  }
}

resource "aws_cloudwatch_metric_alarm" "lambda_throttles" {
  alarm_name          = "fraud-processor-throttles-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "Throttles"
  namespace           = "AWS/Lambda"
  period              = 300
  statistic           = "Sum"
  threshold           = 1
  alarm_description   = "Lambda function being throttled"
  alarm_actions       = [aws_sns_topic.alerts.arn]

  dimensions = {
    FunctionName = aws_lambda_function.fraud_processor.function_name
  }
}

# Kinesis Alarms
resource "aws_cloudwatch_metric_alarm" "kinesis_iterator_age" {
  alarm_name          = "kinesis-high-iterator-age-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "GetRecords.IteratorAgeMilliseconds"
  namespace           = "AWS/Kinesis"
  period              = 300
  statistic           = "Maximum"
  threshold           = 60000
  alarm_description   = "Kinesis stream processing lag detected"
  alarm_actions       = [aws_sns_topic.alerts.arn]

  dimensions = {
    StreamName = aws_kinesis_stream.fraud_transactions.name
  }
}

# SNS Topic for Alerts
resource "aws_sns_topic" "alerts" {
  name = "banking-ml-alerts-${var.environment}"
}

resource "aws_sns_topic_subscription" "email" {
  topic_arn = aws_sns_topic.alerts.arn
  protocol  = "email"
  endpoint  = var.alert_email
}

output "sns_topic_arn" {
  value = aws_sns_topic.alerts.arn
}
