output "artifact_store" {
  description = "Artifact storage created only when the safety switch is enabled."
  value       = try(google_storage_bucket.artifacts[0].name, null)
}
