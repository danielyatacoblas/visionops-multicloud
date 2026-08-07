output "artifact_store" {
  description = "Artifact storage created only when the safety switch is enabled."
  value       = try(azurerm_storage_account.artifacts[0].name, null)
}
