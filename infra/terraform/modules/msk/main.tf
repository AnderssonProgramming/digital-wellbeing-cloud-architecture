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

variable "kafka_broker_count" {
  type    = number
  default = 3
}

resource "aws_security_group" "msk" {
  name        = "${var.cluster_name}-sg"
  description = "Security group for CVS MSK cluster"
  vpc_id      = "vpc-aaaaaaaa"
}

resource "aws_msk_cluster" "this" {
  cluster_name           = var.cluster_name
  kafka_version          = "3.6.0"
  number_of_broker_nodes = var.kafka_broker_count

  broker_node_group_info {
    instance_type   = "kafka.t3.small"
    client_subnets  = ["subnet-aaaaaaaa", "subnet-bbbbbbbb", "subnet-cccccccc"]
    security_groups = [aws_security_group.msk.id]

    storage_info {
      ebs_storage_info {
        volume_size = 50
      }
    }
  }

  encryption_info {
    encryption_in_transit {
      client_broker = "TLS"
      in_cluster    = true
    }
  }
}

output "cluster_arn" {
  value = aws_msk_cluster.this.arn
}

output "bootstrap_brokers_tls" {
  value = aws_msk_cluster.this.bootstrap_brokers_tls
}
