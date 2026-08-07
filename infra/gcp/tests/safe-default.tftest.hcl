mock_provider "google" {}

run "safe_default_plans_zero_resources" {
  command = plan

  variables {
    enable_cloud_resources = false
  }

  assert {
    condition     = length(google_storage_bucket.artifacts) == 0
    error_message = "The default test must not plan a Cloud Storage bucket."
  }
}
