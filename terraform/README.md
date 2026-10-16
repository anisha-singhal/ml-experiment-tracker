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
| [`localstack.tfvars`](localstack.tfvars) | Values for the free LocalStack target |
| [`modules/eks/`](modules/eks/) | The EKS cluster, so it can be switched off with one `count` |

22 resources in total: 1 VPC, 4 subnets (2 public + 2 private), 1 IGW, 1 NAT
Gateway + EIP, 3 route tables, 1 S3 gateway endpoint, 2 IAM roles with 6 policy
attachments, 1 EKS cluster, 1 OIDC provider, 1 managed node group, 4 addons and
1 log group.

## Two targets, one configuration

The same HCL applies to either of two places, chosen by variables:

| Target | Command | EKS | Cost |
|---|---|---|---|
| **LocalStack** | `terraform apply -var-file=localstack.tfvars` | off | free |
| **Real AWS** | `terraform apply` (defaults) | on | ~$0.24/hr |

LocalStack's free edition does not implement EKS — the API says so plainly:

```
An error occurred (InternalFailure) when calling the CreateCluster operation:
API for service 'eks' not yet implemented or pro feature
```

Everything else this project declares — VPC, subnets, Internet Gateway, NAT
Gateway, Elastic IP, route tables, the S3 endpoint and the IAM roles — **is**
supported, so the network layer applies for real there. `var.enable_eks = false`
switches the EKS module off, which is why the cluster lives in
[`modules/eks/`](modules/eks/): one `count` on the module block, rather than a
`count` scattered across a dozen resources with every internal reference
rewritten to index `[0]`.

## What has actually been run

**Against LocalStack — the complete lifecycle, genuinely executed:**

```
$ terraform plan -var-file=localstack.tfvars
Plan: 16 to add, 0 to change, 0 to destroy.

$ terraform apply
Apply complete! Resources: 16 added, 0 changed, 0 destroyed.
```

Verified with the AWS CLI rather than taken from Terraform's own state:

```
$ aws ec2 describe-subnets          # PublicIP=True are the public subnets
|     AZ      |     CIDR       | PublicIP  |     SubnetId      |
|  ap-south-1a|  10.0.0.0/20   |  True     |  subnet-3c620fbe  |
|  ap-south-1b|  10.0.16.0/20  |  True     |  subnet-49c1d91b  |
|  ap-south-1a|  10.0.32.0/20  |  False    |  subnet-b026910a  |
|  ap-south-1b|  10.0.48.0/20  |  False    |  subnet-d6721eb3  |

  igw: igw-91b14b68
  nat: nat-3153e4261397bcec9   available   subnet-3c620fbe
```

Two public subnets across two Availability Zones, two private, and the NAT
Gateway in a **public** subnet — placing it in the private subnet it serves
creates a routing loop, which is the classic first-VPC mistake.

```
$ terraform destroy
Destroy complete! Resources: 16 destroyed.
```

Then swept, because an exit code is not evidence:

```
VPCs tagged mltracker : 0
NAT gateways available: 0
Elastic IPs allocated : 0
Internet gateways     : 0
```

That sweep matters far more on real AWS. If an Ingress created a load balancer,
Kubernetes made it and Terraform does not know it exists; the subnet delete then
fails on an unknown network interface, and resources keep billing while the
operator believes everything is gone.

**Against real AWS — applied, verified, destroyed.** In `ap-southeast-2`, on the account's
only permitted region:

```
$ terraform plan -out=tfplan        # Plan: 31 to add
$ terraform apply tfplan
  EKS mltracker-dev            ACTIVE   1.33
  node group mltracker-dev-nodes ACTIVE   2 x t3.medium

$ kubectl get nodes
ip-10-0-46-153.ap-southeast-2.compute.internal   Ready   v1.33.13-eks-b9510e3
ip-10-0-50-214.ap-southeast-2.compute.internal   Ready   v1.33.13-eks-b9510e3

$ terraform destroy
Destroy complete! Resources: 30 destroyed.
```

Console screenshots are in [`../docs/screenshots/`](../docs/screenshots/) (`aws-eks-cluster.png`,
`aws-vpc.png`) and the full transcript, including the post-destroy sweep, is in
[`../docs/terraform-output.txt`](../docs/terraform-output.txt).

Worth reading rather than skipping past. `169.254.169.254` is the EC2 instance
metadata service — the **last** source in the AWS provider's credential chain,
after environment variables, the shared credentials file and SSO. It only answers
on an EC2 instance, so this means *every* source was tried and none existed. It is
not a broken configuration.

`plan` needs credentials because it **refreshes**: it asks AWS what currently
exists before computing a diff. `validate` is offline and only checks syntax,
types and references — which is why a configuration can validate perfectly and
still fail on apply.

Full transcript: [`../docs/terraform-output.txt`](../docs/terraform-output.txt).

## Applying it

### Free, against LocalStack

```bash
docker run -d --name localstack-tf -p 4566:4566 \
  -e SERVICES=ec2,iam,sts,logs,s3 localstack/localstack:3.8

terraform init
terraform plan  -var-file=localstack.tfvars -out=tfplan
terraform apply tfplan
terraform destroy -var-file=localstack.tfvars
```

Nothing is billed and no account is needed. EKS is skipped.

### Against real AWS

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

- **EKS is a child module purely so it can be switched off.** One `count` on the
  module block disables twelve resources at once; doing it with a `count` on each
  resource would mean rewriting every internal cross-reference to index `[0]`.

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
