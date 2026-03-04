variable "vpc_id" {
  description = "VPC ID for ECS and ALB"
  type        = string
  default     = ""
}

variable "public_subnet_ids" {
  description = "Public subnet IDs for ALB"
  type        = list(string)
  default     = []
}

variable "private_subnet_ids" {
  description = "Private subnet IDs for ECS tasks"
  type        = list(string)
  default     = []
}

variable "ssl_certificate_arn" {
  description = "ACM certificate ARN for HTTPS"
  type        = string
  default     = ""
}

variable "alert_email" {
  description = "Email for CloudWatch alerts"
  type        = string
  default     = "alerts@bank.example.com"
}
