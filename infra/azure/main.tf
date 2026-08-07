locals {
  name = "visionops${var.environment}"
  tags = { project = "visionops-multicloud", environment = var.environment, managed_by = "terraform", owner = var.owner }
}

resource "azurerm_resource_group" "main" {
  count    = var.enable_cloud_resources ? 1 : 0
  name     = "rg-${local.name}"
  location = var.region
  tags     = local.tags
}

resource "azurerm_storage_account" "artifacts" {
  count                    = var.enable_cloud_resources ? 1 : 0
  name                     = substr("st${local.name}artifacts", 0, 24)
  resource_group_name      = azurerm_resource_group.main[0].name
  location                 = azurerm_resource_group.main[0].location
  account_tier             = "Standard"
  account_replication_type = "LRS"
  min_tls_version          = "TLS1_2"
  tags                     = local.tags
}
