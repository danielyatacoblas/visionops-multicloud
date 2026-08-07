output "artifact_store" {
  description = "Artifact storage created only when the safety switch is enabled."
  value       = try(aws_s3_bucket.artifacts[0].id, null)
}
