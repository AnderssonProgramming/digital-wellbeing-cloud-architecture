variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "cluster_name" {
  description = "EKS cluster name"
  type        = string
  default     = "cvs-cloud-platform"
}

variable "kafka_broker_count" {
  description = "Number of MSK brokers"
  type        = number
  default     = 3
}

variable "s3_model_bucket_name" {
  description = "S3 bucket name for model artifacts"
  type        = string
  default     = "cvs-model-artifacts"
}
