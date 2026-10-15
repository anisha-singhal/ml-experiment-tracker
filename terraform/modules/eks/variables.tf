variable "name" {
  description = "Cluster name and the prefix for every resource this module creates."
  type        = string
}

variable "environment" {
  description = "Environment label applied to node group labels."
  type        = string
}

variable "kubernetes_version" {
  description = "EKS control plane version."
  type        = string
}

variable "public_subnet_ids" {
  description = "Public subnet ids. Control-plane ENIs are placed here so kubectl can reach the endpoint."
  type        = list(string)
}

variable "private_subnet_ids" {
  description = "Private subnet ids. Worker nodes run here."
  type        = list(string)
}

variable "node_instance_types" {
  description = "Instance types for the managed node group."
  type        = list(string)
}

variable "node_desired_size" {
  description = "Desired number of worker nodes."
  type        = number
}

variable "node_min_size" {
  description = "Minimum number of worker nodes."
  type        = number
}

variable "node_max_size" {
  description = "Maximum number of worker nodes."
  type        = number
}
