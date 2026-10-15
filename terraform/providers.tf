locals {
  # Credentials are only faked for LocalStack. Against real AWS the provider
  # uses the normal chain: environment, shared credentials file, SSO, instance
  # metadata. No key is ever written into this repository.
  localstack_endpoint = "http://localhost:4566"
}

provider "aws" {
  region = var.aws_region

  # ---- LocalStack-only settings. All no-ops when use_localstack = false. ----
  access_key                  = var.use_localstack ? "test" : null
  secret_key                  = var.use_localstack ? "test" : null
  skip_credentials_validation = var.use_localstack
  skip_metadata_api_check     = var.use_localstack
  skip_requesting_account_id  = var.use_localstack
  # LocalStack serves every bucket from one endpoint, so S3 addressing has to be
  # path-style rather than virtual-hosted, which would need per-bucket DNS.
  s3_use_path_style = var.use_localstack

  dynamic "endpoints" {
    for_each = var.use_localstack ? [1] : []
    content {
      ec2            = local.localstack_endpoint
      iam            = local.localstack_endpoint
      sts            = local.localstack_endpoint
      s3             = local.localstack_endpoint
      cloudwatchlogs = local.localstack_endpoint
      eks            = local.localstack_endpoint
    }
  }

  # Applied to every resource that supports tagging, so cost allocation and
  # "what is this and who owns it" never depend on remembering per-resource tags.
  default_tags {
    tags = {
      Project     = var.project_name
      Environment = var.environment
      ManagedBy   = "terraform"
      Owner       = "Anisha Singhal"
    }
  }
}
