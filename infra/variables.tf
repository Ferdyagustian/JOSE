variable "project_name" {
  description = "Project name identifier used for prefixing resources"
  type        = string
  default     = "jobradar"
}

variable "environment" {
  description = "Deployment environment (e.g. dev, prod)"
  type        = string
  default     = "prod"
}

variable "location" {
  description = "Azure region for all resources"
  type        = string
  default     = "southeastasia"
}

variable "storage_account_tier" {
  description = "Storage account tier"
  type        = string
  default     = "Standard"
}

variable "storage_replication_type" {
  description = "Storage account replication type"
  type        = string
  default     = "LRS"
}
