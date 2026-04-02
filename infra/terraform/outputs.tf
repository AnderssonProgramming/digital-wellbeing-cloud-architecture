output "eks_cluster_name" {
  description = "Name of the EKS cluster"
  value       = module.eks.cluster_name
}

output "eks_cluster_arn" {
  description = "ARN of the EKS cluster"
  value       = module.eks.cluster_arn
}

output "msk_cluster_arn" {
  description = "ARN of the MSK cluster"
  value       = module.msk.cluster_arn
}

output "msk_bootstrap_brokers" {
  description = "TLS bootstrap brokers for MSK"
  value       = module.msk.bootstrap_brokers_tls
}

output "model_bucket_name" {
  description = "S3 bucket for model artifacts"
  value       = module.s3.bucket_name
}
