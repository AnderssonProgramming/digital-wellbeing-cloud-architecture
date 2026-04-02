terraform {
  required_providers {
    aws = {
      source = "hashicorp/aws"
    }
  }
}

variable "cluster_name" {
  type = string
}

resource "aws_iam_role" "eks_cluster_role" {
  name = "${var.cluster_name}-cluster-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = { Service = "eks.amazonaws.com" }
      Action = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "eks_cluster_policy" {
  role       = aws_iam_role.eks_cluster_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSClusterPolicy"
}

resource "aws_iam_role" "eks_node_role" {
  name = "${var.cluster_name}-node-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = { Service = "ec2.amazonaws.com" }
      Action = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "worker_node_policy" {
  role       = aws_iam_role.eks_node_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSWorkerNodePolicy"
}

resource "aws_iam_role_policy_attachment" "cni_policy" {
  role       = aws_iam_role.eks_node_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKS_CNI_Policy"
}

resource "aws_iam_role_policy_attachment" "ecr_read_only" {
  role       = aws_iam_role.eks_node_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly"
}

resource "aws_eks_cluster" "this" {
  name     = var.cluster_name
  role_arn = aws_iam_role.eks_cluster_role.arn
  version  = "1.29"

  vpc_config {
    subnet_ids              = ["subnet-aaaaaaaa", "subnet-bbbbbbbb", "subnet-cccccccc"]
    endpoint_public_access  = true
    endpoint_private_access = true
  }

  depends_on = [aws_iam_role_policy_attachment.eks_cluster_policy]
}

resource "aws_eks_node_group" "ingestion" {
  cluster_name    = aws_eks_cluster.this.name
  node_group_name = "${var.cluster_name}-ingestion"
  node_role_arn   = aws_iam_role.eks_node_role.arn
  subnet_ids      = aws_eks_cluster.this.vpc_config[0].subnet_ids
  instance_types  = ["t3.medium"]

  scaling_config {
    desired_size = 2
    min_size     = 2
    max_size     = 4
  }
}

resource "aws_eks_node_group" "processing" {
  cluster_name    = aws_eks_cluster.this.name
  node_group_name = "${var.cluster_name}-processing"
  node_role_arn   = aws_iam_role.eks_node_role.arn
  subnet_ids      = aws_eks_cluster.this.vpc_config[0].subnet_ids
  instance_types  = ["t3.medium"]

  scaling_config {
    desired_size = 3
    min_size     = 3
    max_size     = 6
  }
}

resource "aws_eks_node_group" "data_ml" {
  cluster_name    = aws_eks_cluster.this.name
  node_group_name = "${var.cluster_name}-data-ml"
  node_role_arn   = aws_iam_role.eks_node_role.arn
  subnet_ids      = aws_eks_cluster.this.vpc_config[0].subnet_ids
  instance_types  = ["t3.large"]

  scaling_config {
    desired_size = 2
    min_size     = 2
    max_size     = 4
  }
}

output "cluster_name" {
  value = aws_eks_cluster.this.name
}

output "cluster_arn" {
  value = aws_eks_cluster.this.arn
}
