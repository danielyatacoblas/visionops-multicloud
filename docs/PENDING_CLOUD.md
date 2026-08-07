# Pending cloud validation

No AWS, GCP or Azure resource has been deployed during local development.

Before changing that status:

1. confirm account/subscription/project and owner;
2. configure federated CI identity and least privilege;
3. select a region after quota, service availability and cost checks;
4. configure remote Terraform state and locking;
5. add budget alerts and a hard application spending guard;
6. deploy one cloud at a time, run smoke tests and collect redacted evidence;
7. destroy resources and verify no billable dependencies remain.

Project-specific managed services for **VisionOps** are architectural targets, not verified claims.
