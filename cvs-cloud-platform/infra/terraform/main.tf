terraform {
  required_version = ">= 1.6.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

module "eks" {
  source       = "./modules/eks"
  cluster_name = var.cluster_name
}

module "msk" {
  source             = "./modules/msk"
  cluster_name       = "${var.cluster_name}-msk"
  kafka_broker_count = var.kafka_broker_count
}

module "s3" {
  source       = "./modules/s3"
  bucket_name  = var.s3_model_bucket_name
  force_destroy = false
}
