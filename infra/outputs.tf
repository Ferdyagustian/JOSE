output "resource_group_name" {
  description = "The name of the Azure Resource Group"
  value       = azurerm_resource_group.rg.name
}

output "storage_account_name" {
  description = "The name of the Azure Storage Account"
  value       = azurerm_storage_account.lakehouse.name
}

output "primary_connection_string" {
  description = "The primary connection string for the storage account (Copy this to GitHub Secrets: AZURE_STORAGE_CONNECTION_STRING)"
  value       = azurerm_storage_account.lakehouse.primary_connection_string
  sensitive   = true
}

output "primary_access_key" {
  description = "The primary access key for the storage account"
  value       = azurerm_storage_account.lakehouse.primary_access_key
  sensitive   = true
}

output "primary_dfs_endpoint" {
  description = "ADLS Gen2 Primary DFS endpoint URL"
  value       = azurerm_storage_account.lakehouse.primary_dfs_endpoint
}

output "container_names" {
  description = "Created Data Lakehouse filesystem containers"
  value       = [for c in azurerm_storage_data_lake_gen2_filesystem.containers : c.name]
}
