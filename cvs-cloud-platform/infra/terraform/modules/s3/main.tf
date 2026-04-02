terraform {
  required_providers {
    aws = {
      source = "hashicorp/aws"
    }
  }
}

variable "bucket_name" {
  type = string
}

variable "force_destroy" {
  type    = bool
  default = false
}

resource "aws_s3_bucket" "model_artifacts" {
  bucket        = var.bucket_name
  force_destroy = var.force_destroy
}

resource "aws_s3_bucket_versioning" "model_artifacts" {
  bucket = aws_s3_bucket.model_artifacts.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "model_artifacts" {
  bucket = aws_s3_bucket.model_artifacts.id

  rule {
    id     = "expire-after-180-days"
    status = "Enabled"

    expiration {
      days = 180
    }
  }
}

output "bucket_name" {
  value = aws_s3_bucket.model_artifacts.bucket
}
