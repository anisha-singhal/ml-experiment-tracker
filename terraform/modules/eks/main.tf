# ------------------------------------------------------ cluster IAM role ----

data "aws_iam_policy_document" "cluster_assume_role" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["eks.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "cluster" {
  name               = "${var.name}-eks-cluster-role"
  assume_role_policy = data.aws_iam_policy_document.cluster_assume_role.json
}

resource "aws_iam_role_policy_attachment" "cluster_policy" {
  role       = aws_iam_role.cluster.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSClusterPolicy"
}

# --------------------------------------------------------------- logging ----

resource "aws_cloudwatch_log_group" "cluster" {
  # EKS writes to this exact name. Declaring it explicitly means retention is
  # controlled - otherwise EKS creates it with "never expire" and it bills
  # forever after the cluster is deleted.
  name              = "/aws/eks/${var.name}/cluster"
  retention_in_days = 7
}

# --------------------------------------------------------------- cluster ----

resource "aws_eks_cluster" "main" {
  name     = var.name
  role_arn = aws_iam_role.cluster.arn
  version  = var.kubernetes_version

  vpc_config {
    # Control-plane ENIs in both tiers: public so kubectl can reach the
    # endpoint, private so the control plane can reach node kubelets.
    subnet_ids              = concat(var.public_subnet_ids, var.private_subnet_ids)
    endpoint_private_access = true
    endpoint_public_access  = true
    # Deliberately open for evaluation. A real cluster restricts this to an
    # office or VPN CIDR.
    public_access_cidrs = ["0.0.0.0/0"]
  }

  enabled_cluster_log_types = ["api", "audit", "authenticator"]

  access_config {
    # API mode replaces the old aws-auth ConfigMap. The creating principal is
    # granted admin automatically, so a mistake here cannot lock everyone out
    # of a cluster that has no other access entry.
    authentication_mode                         = "API_AND_CONFIG_MAP"
    bootstrap_cluster_creator_admin_permissions = true
  }

  tags = { Name = var.name }

  depends_on = [
    aws_iam_role_policy_attachment.cluster_policy,
    aws_cloudwatch_log_group.cluster,
  ]
}

# ------------------------------------------------- OIDC provider for IRSA ----

data "tls_certificate" "cluster" {
  url = aws_eks_cluster.main.identity[0].oidc[0].issuer
}

# IRSA: a pod assumes an IAM role through a projected service-account token,
# so no AWS access key is ever stored in a Kubernetes Secret.
resource "aws_iam_openid_connect_provider" "cluster" {
  url             = aws_eks_cluster.main.identity[0].oidc[0].issuer
  client_id_list  = ["sts.amazonaws.com"]
  thumbprint_list = [data.tls_certificate.cluster.certificates[0].sha1_fingerprint]
}

# --------------------------------------------------------- node IAM role ----

data "aws_iam_policy_document" "node_assume_role" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["ec2.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "node" {
  name               = "${var.name}-eks-node-role"
  assume_role_policy = data.aws_iam_policy_document.node_assume_role.json
}

resource "aws_iam_role_policy_attachment" "node" {
  for_each = toset([
    "arn:aws:iam::aws:policy/AmazonEKSWorkerNodePolicy",
    "arn:aws:iam::aws:policy/AmazonEKS_CNI_Policy", # pod IPs from the VPC
    "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly",
    "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore", # shell without SSH or port 22
  ])

  role       = aws_iam_role.node.name
  policy_arn = each.value
}

# ------------------------------------------------------------ node group ----

resource "aws_eks_node_group" "main" {
  cluster_name    = aws_eks_cluster.main.name
  node_group_name = "${var.name}-nodes"
  node_role_arn   = aws_iam_role.node.arn
  # Private subnets: nodes reach the internet outbound through NAT and are not
  # directly reachable from it.
  subnet_ids = var.private_subnet_ids

  instance_types = var.node_instance_types
  capacity_type  = "ON_DEMAND"
  disk_size      = 20

  scaling_config {
    desired_size = var.node_desired_size
    min_size     = var.node_min_size
    max_size     = var.node_max_size
  }

  update_config {
    # Replace at most one node at a time during a version upgrade.
    max_unavailable = 1
  }

  labels = {
    role        = "general"
    environment = var.environment
  }

  lifecycle {
    # The cluster autoscaler owns desired_size once it is running; without this
    # every terraform apply would scale the group back to the committed number.
    ignore_changes = [scaling_config[0].desired_size]
  }

  tags = { Name = "${var.name}-nodes" }

  depends_on = [aws_iam_role_policy_attachment.node]
}

# ---------------------------------------------------------------- addons ----

# Addons are created after the node group so their pods have somewhere to be
# scheduled; otherwise they sit Pending and the apply reports a false failure.
resource "aws_eks_addon" "vpc_cni" {
  cluster_name                = aws_eks_cluster.main.name
  addon_name                  = "vpc-cni"
  resolve_conflicts_on_create = "OVERWRITE"
  depends_on                  = [aws_eks_node_group.main]
}

resource "aws_eks_addon" "coredns" {
  cluster_name                = aws_eks_cluster.main.name
  addon_name                  = "coredns"
  resolve_conflicts_on_create = "OVERWRITE"
  depends_on                  = [aws_eks_node_group.main]
}

resource "aws_eks_addon" "kube_proxy" {
  cluster_name                = aws_eks_cluster.main.name
  addon_name                  = "kube-proxy"
  resolve_conflicts_on_create = "OVERWRITE"
  depends_on                  = [aws_eks_node_group.main]
}

resource "aws_eks_addon" "ebs_csi" {
  # Without this driver a PersistentVolumeClaim on EKS stays Pending forever
  # and the event message does not say why.
  cluster_name                = aws_eks_cluster.main.name
  addon_name                  = "aws-ebs-csi-driver"
  resolve_conflicts_on_create = "OVERWRITE"
  depends_on                  = [aws_eks_node_group.main]
}
