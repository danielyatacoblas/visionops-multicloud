# AWS infrastructure

This folder is intentionally safe by default: `enable_cloud_resources = false`.

1. Authenticate locally without saving credentials in this repository.
2. Copy `environments/demo/terraform.tfvars.example` to `environments/demo/terraform.tfvars`.
3. Run `terraform init`, `terraform fmt -check`, `terraform validate` and `terraform plan`.
4. Review identity, region, quota, cost, retention and teardown.
5. Enable real resources only during an approved cloud-validation session.

The complete managed-service topology is documented in the root README and remains `PENDING_CLOUD_VALIDATION`.
