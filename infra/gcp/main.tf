locals {
  name   = "visionops-${var.environment}"
  labels = { project = "visionops", environment = var.environment, managed_by = "terraform" }
}

resource "google_storage_bucket" "artifacts" {
  count                       = var.enable_cloud_resources ? 1 : 0
  name                        = "${var.project_id}-${local.name}-artifacts"
  location                    = var.region
  uniform_bucket_level_access = true
  force_destroy               = true
  labels                      = local.labels
}
