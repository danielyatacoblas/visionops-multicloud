mock_provider "aws" {}

run "safe_default_plans_zero_resources" {
  command = plan

  variables {
    enable_cloud_resources = false
  }

  assert {
    condition     = length(aws_s3_bucket.artifacts) == 0
    error_message = "The default test must not plan an S3 bucket."
  }
}
