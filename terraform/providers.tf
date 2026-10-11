provider "aws" {
  region = var.aws_region

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
