# Terraform — AWS VPC and EKS

Provisions the cloud infrastructure the application runs on: a two-AZ VPC and an
EKS cluster with a managed node group.

## What it creates

```
                        Internet
                            │
                     [ Internet Gateway ]
                            │
        ┌───────────────────┴───────────────────┐   VPC 10.0.0.0/16
        │                                       │
        │  public  10.0.0.0/20   (AZ-a)         │  public  10.0.16.0/20  (AZ-b)
        │    NAT Gateway, load balancers        │    load balancers
        │    route 0.0.0.0/0 → IGW              │
        │               │                       │
        │               ▼                       │
        │  private 10.0.32.0/20  (AZ-a)         │  private 10.0.48.0/20  (AZ-b)
        │    EKS worker nodes                   │    EKS worker nodes
        │    route 0.0.0.0/0 → NAT              │
        └───────────────────────────────────────┘
                            │
                   [ EKS control plane ]
                      ENIs in both tiers
```

| File | Contains |
|---|---|
| [`versions.tf`](versions.tf) | Terraform and provider version constraints, commented S3 backend |
| [`providers.tf`](providers.tf) | AWS provider and `default_tags` |
| [`variables.tf`](variables.tf) | Inputs with validation |
| [`vpc.tf`](vpc.tf) | VPC, IGW, subnets, NAT, route tables, S3 endpoint |
| [`eks.tf`](eks.tf) | IAM roles, cluster, OIDC provider, node group, addons |
| [`outputs.tf`](outputs.tf) | Cluster endpoint, subnet ids, kubeconfig command |
| [`terraform.tfvars.example`](terraform.tfvars.example) | Example values — **no credentials** |

22 resources in total: 1 VPC, 4 subnets (2 public + 2 private), 1 IGW, 1 NAT
Gateway + EIP, 3 route tables, 1 S3 gateway endpoint, 2 IAM roles with 6 policy
attachments, 1 EKS cluster, 1 OIDC provider, 1 managed node group, 4 addons and
1 log group.

## Verified so far

`init`, `fmt` and `validate` have been run and pass:

```
$ terraform init
Terraform has been successfully initialized!

$ terraform fmt -check -recursive
$ echo $?
0

$ terraform validate
Success! The configuration is valid.
```

`plan` has **not** been run against an account, because it needs credentials:

```
$ terraform plan
Error: No valid credential sources found

Error: failed to refresh cached credentials, no EC2 IMDS role found,
operation error ec2imds: GetMetadata, request canceled, context deadline exceeded
```

Worth reading rather than skipping past. `169.254.169.254` is the EC2 instance
metadata service — the **last** source in the AWS provider's credential chain,
after environment variables, the shared credentials file and SSO. It only
answers on an EC2 instance, so this error means *every* source was tried and
none existed. It is not a broken configuration.

`plan` needs credentials because it **refreshes**: it asks AWS what currently
exists before computing a diff. `validate` is offline and only checks syntax,
types and references — which is why a configuration can validate perfectly and
still fail on apply.

## Applying it

```bash
export AWS_PROFILE=your-profile          # or AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY
cp terraform.tfvars.example terraform.tfvars

terraform init
terraform plan -out=tfplan               # screenshot this
terraform apply tfplan                   # ~15-20 minutes, mostly the EKS control plane

aws eks update-kubeconfig --region ap-south-1 --name mltracker-dev
kubectl get nodes                        # should list the worker nodes
```

Then deploy the application onto it:

```bash
kubectl apply -f ../k8s/namespace.yaml
helm upgrade --install mltracker ../helm/mltracker -n ml-tracker \
  --set backend.image.repository=ghcr.io/anisha-singhal/ml-experiment-tracker-backend \
  --set backend.image.tag=<commit-sha> \
  --set frontend.image.repository=ghcr.io/anisha-singhal/ml-experiment-tracker-frontend \
  --set frontend.image.tag=<commit-sha>
```

## Tearing it down

```bash
terraform destroy                        # screenshot this too
```

**Destroy when the evaluation is finished.** An idle EKS cluster bills whether
anything runs on it or not.

One ordering trap: if a `type: LoadBalancer` Service or an Ingress created an
AWS load balancer, that load balancer was made by Kubernetes and is *not* in
Terraform state. Terraform will fail to delete the subnets because an unknown
ENI still occupies them. Delete the Kubernetes resources first:

```bash
helm uninstall mltracker -n ml-tracker
kubectl delete svc --all -n ml-tracker
# wait for the AWS load balancers to disappear, then
terraform destroy
```

## Cost

Approximate `ap-south-1` on-demand pricing, with `single_nat_gateway = true`:

| Resource | Rate | Per day |
|---|---|---|
| EKS control plane | $0.10/hr | ~$2.40 |
| 2 × t3.medium nodes | ~$0.0448/hr each | ~$2.15 |
| NAT Gateway | $0.045/hr + data | ~$1.10 |
| EBS (2 × 20 GB gp3) | ~$0.08/GB-month | ~$0.11 |
| **Total** | | **~$5.75/day** |

A few hours for an evaluation is well under a dollar. The VPC, subnets, route
tables, IAM roles and the S3 endpoint are free.

`enable_nat_gateway = false` removes the largest line item, at the cost of
private subnets having no outbound route — nodes then cannot pull images
without VPC endpoints for ECR.

## Decisions worth explaining

- **Raw resources, not the community modules.** `terraform-aws-modules/eks` is
  excellent and would be the right call on a team. Written out here because the
  IAM roles, the OIDC provider and the subnet tags are the parts actually worth
  understanding, and a module hides all three.

- **Subnet CIDRs are computed, not hardcoded.** `cidrsubnet(var.vpc_cidr, 4, i)`
  with the private range offset by `az_count`, so changing `az_count` cannot
  make the two groups overlap.

- **AZs come from a data source**, filtered to `opt-in-not-required`. Hardcoding
  `ap-south-1a` breaks in any other region and in accounts where an AZ is opted
  out.

- **The `kubernetes.io/role/elb` subnet tags are not decoration.** Without them
  the AWS load balancer controller cannot work out where to place an
  internet-facing load balancer, and a `type: LoadBalancer` Service stays
  `<pending>` with no useful error.

- **`ignore_changes` on `desired_size`.** Once a cluster autoscaler is running
  it owns that number; without this, every `terraform apply` would scale the
  node group back to whatever is committed here.

- **The CloudWatch log group is declared explicitly.** EKS creates it anyway if
  left out — with no expiry, so it keeps billing long after the cluster is gone.

- **An OIDC provider is created even though nothing uses it yet.** It is what
  makes IRSA possible, so a pod can assume an IAM role through a projected
  service-account token instead of holding an AWS access key in a Secret.

- **The S3 gateway endpoint is free and routes ECR layer pulls off the NAT
  Gateway**, which is otherwise billed per GB processed.
