terraform {
  required_version = ">= 1.6.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    tls = {
      source  = "hashicorp/tls"
      version = "~> 4.0"
    }
  }

  # Remote state belongs in S3 with DynamoDB locking for any shared
  # environment. Left local here so the project can be evaluated without first
  # provisioning a state bucket.
  #
  # backend "s3" {
  #   bucket         = "mltracker-tfstate"
  #   key            = "eks/terraform.tfstate"
  #   region         = "ap-south-1"
  #   dynamodb_table = "mltracker-tf-locks"
  #   encrypt        = true
  # }
}
