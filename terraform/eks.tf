# The EKS cluster lives in a module so the whole thing can be switched off with
# one `count`, rather than scattering a count across a dozen resources and
# rewriting every internal reference to index [0].
#
# It is switched off when running against LocalStack, whose free edition does
# not implement EKS - the API answers:
#   "API for service 'eks' not yet implemented or pro feature"
# Every other resource in this project (VPC, subnets, IGW, NAT Gateway, EIP,
# route tables, IAM roles) is supported, so the VPC applies for real there.
module "eks" {
  count  = var.enable_eks ? 1 : 0
  source = "./modules/eks"

  name               = local.name
  environment        = var.environment
  kubernetes_version = var.kubernetes_version

  public_subnet_ids  = aws_subnet.public[*].id
  private_subnet_ids = aws_subnet.private[*].id

  node_instance_types = var.node_instance_types
  node_desired_size   = var.node_desired_size
  node_min_size       = var.node_min_size
  node_max_size       = var.node_max_size
}
