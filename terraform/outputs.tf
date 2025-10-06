output "resource_group_name" {
  description = "Name of the resource group hosting the onboarding portal resources."
  value       = azurerm_resource_group.primary.name
}

output "web_app_name" {
  description = "Name of the Azure App Service hosting the Flask application."
  value       = azurerm_linux_web_app.primary.name
}

output "web_app_hostname" {
  description = "Default hostname for the App Service."
  value       = azurerm_linux_web_app.primary.default_hostname
}

output "sql_server_name" {
  description = "Name of the Azure SQL logical server."
  value       = azurerm_mssql_server.primary.name
}

output "sql_database_name" {
  description = "Azure SQL database that backs the onboarding portal."
  value       = azurerm_mssql_database.primary.name
}

output "sql_administrator_login" {
  description = "Administrator login for the Azure SQL server."
  value       = var.sql_administrator_login
}

output "sql_administrator_password" {
  description = "Password for the Azure SQL administrator login."
  value       = random_password.sql_admin.result
  sensitive   = true
}

output "app_service_connection_string" {
  description = "SQL connection string injected into the App Service configuration."
  value       = local.sql_connection_string
  sensitive   = true
}

output "service_principal_client_id" {
  description = "Client ID of the service principal used by GitHub Actions."
  value       = azuread_service_principal.github.client_id
}

output "service_principal_tenant_id" {
  description = "Tenant ID associated with the GitHub Actions service principal."
  value       = coalesce(var.tenant_id, data.azurerm_client_config.current.tenant_id)
}

output "service_principal_secret" {
  description = "Client secret for the GitHub Actions service principal. Use as a GitHub secret."
  value       = azuread_application_password.github.value
  sensitive   = true
}

output "github_repository_url" {
  description = "GitHub repository configured for continuous deployment."
  value       = local.github_repo_url
}
