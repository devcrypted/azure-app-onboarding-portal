variable "subscription_id" {
  type        = string
  description = "Azure subscription ID to deploy resources into. Leave empty to use the credentials from the current Azure CLI/SP context."
  default     = null
}

variable "tenant_id" {
  type        = string
  description = "Azure Active Directory tenant ID. Leave empty to use the credentials from the current Azure CLI/SP context."
  default     = null
}

variable "location" {
  type        = string
  description = "Azure region where resources should be created."
  default     = "Central India"
}

variable "project_name" {
  type        = string
  description = "Short name for this deployment. Used as a prefix for resource names."
  default     = "apponboard"

  validation {
    condition     = can(regex("^[A-Za-z0-9-]{3,30}$", var.project_name))
    error_message = "project_name must be 3-30 characters and may only contain letters, numbers, and hyphens."
  }
}

variable "environment" {
  type        = string
  description = "Environment name (e.g. dev, test, prod)."
  default     = "prod"

  validation {
    condition     = can(regex("^[A-Za-z0-9-]{2,20}$", var.environment))
    error_message = "environment must be 2-20 characters and may only contain letters, numbers, and hyphens."
  }
}

variable "sql_administrator_login" {
  type        = string
  description = "Administrator username for the Azure SQL logical server."
  default     = "sqladminuser"
  validation {
    condition     = can(regex("^[A-Za-z0-9_\\-]{8,}$", var.sql_administrator_login))
    error_message = "The SQL administrator login must be at least 8 characters and contain only letters, numbers, underscores, or hyphens."
  }
}

variable "sql_sku_name" {
  type        = string
  description = "Azure SQL database SKU name."
  default     = "Basic"
}

variable "sql_auto_pause_delay" {
  type        = number
  description = "Auto-pause delay in minutes for the Azure SQL database when using serverless compute. Set to -1 to disable auto-pausing."
  default     = null
}

variable "app_service_sku" {
  type        = string
  description = "App Service Plan SKU (e.g. B1, P1v3)."
  default     = "B1"
}

variable "github_owner" {
  type        = string
  description = "GitHub organization or username that hosts the deployment repository."
  default     = "devcrypted"
}

variable "github_repository" {
  type        = string
  description = "GitHub repository name (without owner)."
  default     = "azure-app-onboarding-portal"
}

variable "github_branch" {
  type        = string
  description = "Git branch that GitHub Actions should deploy from."
  default     = "main"
}
