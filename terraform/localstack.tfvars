# Values for applying against LocalStack rather than real AWS.
#   terraform apply -var-file=localstack.tfvars
#
# EKS is off because LocalStack's free edition does not implement it. Every
# other resource in this project is supported and is created for real.

use_localstack = true
enable_eks     = false

aws_region   = "ap-south-1"
project_name = "mltracker"
environment  = "dev"

vpc_cidr = "10.0.0.0/16"
az_count = 2

enable_nat_gateway = true
single_nat_gateway = true
