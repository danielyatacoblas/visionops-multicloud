mock_provider "azurerm" {}

run "safe_default_plans_zero_resources" {
  command = plan

  variables {
    enable_cloud_resources = false
  }

  assert {
    condition     = length(azurerm_resource_group.main) == 0 && length(azurerm_storage_account.artifacts) == 0
    error_message = "The default test must not plan an Azure resource group or storage account."
  }
}
