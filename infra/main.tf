terraform {
  required_version = ">= 1.5.0"
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.100"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }
}

provider "azurerm" {
  features {}
}

# Unique suffix for globally unique Azure Storage Account name
resource "random_string" "suffix" {
  length  = 6
  special = false
  upper   = false
}

# Azure Resource Group
resource "azurerm_resource_group" "rg" {
  name     = "rg-${var.project_name}-${var.environment}"
  location = var.location

  tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# Azure Data Lake Storage Gen2 (StorageV2 with Hierarchical Namespace enabled)
resource "azurerm_storage_account" "lakehouse" {
  name                     = "st${var.project_name}${random_string.suffix.result}"
  resource_group_name      = azurerm_resource_group.rg.name
  location                 = azurerm_resource_group.rg.location
  account_tier             = var.storage_account_tier
  account_replication_type = var.storage_replication_type
  account_kind             = "StorageV2"
  is_hns_enabled           = true # Enables ADLS Gen2 Hierarchical Namespace
  min_tls_version          = "TLS1_2"

  blob_properties {
    delete_retention_policy {
      days = 7
    }
  }

  tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# Data Lake Storage Gen2 Containers (Bronze, Silver, Gold)
resource "azurerm_storage_data_lake_gen2_filesystem" "containers" {
  for_each           = toset(["bronze", "silver", "gold"])
  name               = each.key
  storage_account_id = azurerm_storage_account.lakehouse.id
}
