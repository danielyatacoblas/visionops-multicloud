locals {
  name = "visionops-${var.environment}"
  tags = { project = "visionops-multicloud", environment = var.environment, managed_by = "terraform", owner = var.owner }
}

resource "aws_s3_bucket" "artifacts" {
  count         = var.enable_cloud_resources ? 1 : 0
  bucket_prefix = "${local.name}-"
  force_destroy = true
  tags          = local.tags
}
