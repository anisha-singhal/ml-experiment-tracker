output "cluster_name" {
  description = "EKS cluster name."
  value       = one(module.eks[*].cluster_name)
}

output "cluster_endpoint" {
  description = "Kubernetes API server endpoint."
  value       = one(module.eks[*].cluster_endpoint)
}

output "cluster_version" {
  description = "Kubernetes version actually running, read back from the cluster."
  value       = one(module.eks[*].cluster_version)
}

output "cluster_certificate_authority_data" {
  description = "Base64 CA bundle for the API server."
  value       = one(module.eks[*].cluster_certificate_authority_data)
  sensitive   = true
}

output "oidc_provider_arn" {
  description = "OIDC provider ARN, referenced by IRSA trust policies."
  value       = one(module.eks[*].oidc_provider_arn)
}

output "vpc_id" {
  description = "VPC id."
  value       = aws_vpc.main.id
}

output "vpc_cidr" {
  description = "VPC CIDR block."
  value       = aws_vpc.main.cidr_block
}

output "public_subnet_ids" {
  description = "Public subnet ids, one per AZ."
  value       = aws_subnet.public[*].id
}

output "private_subnet_ids" {
  description = "Private subnet ids, one per AZ."
  value       = aws_subnet.private[*].id
}

output "availability_zones" {
  description = "AZs the subnets were spread across."
  value       = local.azs
}

output "node_group_name" {
  description = "Managed node group name."
  value       = one(module.eks[*].node_group_name)
}

output "configure_kubectl" {
  description = "Command to point kubectl at this cluster."
  value       = var.enable_eks ? "aws eks update-kubeconfig --region ${var.aws_region} --name ${local.name}" : "EKS disabled (enable_eks = false)"
}
