data "azurerm_client_config" "current" {}

resource "random_string" "suffix" {
  length  = 4
  lower   = true
  upper   = false
  numeric = true
  special = false
}

resource "random_password" "sql_admin" {
  length           = 20
  special          = true
  override_special = "!#$%*()-_=+[]{}"
}

locals {
  sanitized_project = lower(var.project_name)
  sanitized_env     = lower(var.environment)
  base_prefix       = "${local.sanitized_project}-${local.sanitized_env}"

  resource_group_name = "${local.base_prefix}-rg"
  service_plan_name   = "${local.base_prefix}-asp"
  web_app_name        = "${local.base_prefix}-web-${random_string.suffix.result}"
  sql_server_name     = substr(replace("${local.base_prefix}-sql-${random_string.suffix.result}", "_", ""), 0, 60)
  sql_database_name   = replace("${local.sanitized_project}_${local.sanitized_env}", "-", "_")

  sql_user_login = "${var.sql_administrator_login}@${local.sql_server_name}"

  sql_connection_string = format(
    "Server=tcp:%s,1433;Database=%s;User ID=%s;Password=%s;Encrypt=true;TrustServerCertificate=false;Connection Timeout=30;",
    azurerm_mssql_server.primary.fully_qualified_domain_name,
    azurerm_mssql_database.primary.name,
    local.sql_user_login,
    random_password.sql_admin.result,
  )

  github_repo_url = "https://github.com/${var.github_owner}/${var.github_repository}"
}

resource "azurerm_resource_group" "primary" {
  name     = local.resource_group_name
  location = var.location
}

resource "azurerm_service_plan" "primary" {
  name                = local.service_plan_name
  location            = azurerm_resource_group.primary.location
  resource_group_name = azurerm_resource_group.primary.name

  os_type  = "Linux"
  sku_name = var.app_service_sku
}

resource "azurerm_mssql_server" "primary" {
  name                         = local.sql_server_name
  resource_group_name          = azurerm_resource_group.primary.name
  location                     = azurerm_resource_group.primary.location
  version                      = "12.0"
  administrator_login          = var.sql_administrator_login
  administrator_login_password = random_password.sql_admin.result

  minimum_tls_version = "1.2"
}

resource "azurerm_mssql_firewall_rule" "allow_azure_services" {
  name             = "AllowAzureServices"
  server_id        = azurerm_mssql_server.primary.id
  start_ip_address = "0.0.0.0"
  end_ip_address   = "0.0.0.0"
}

resource "azurerm_mssql_database" "primary" {
  name        = local.sql_database_name
  server_id   = azurerm_mssql_server.primary.id
  sku_name    = var.sql_sku_name
  collation   = "SQL_Latin1_General_CP1_CI_AS"
  max_size_gb = 2

  lifecycle {
    ignore_changes = [threat_detection_policy]
  }

  auto_pause_delay_in_minutes = var.sql_auto_pause_delay
}

resource "azuread_application" "github" {
  display_name = "${title(var.project_name)} GitHub Deploy"

  owners = [data.azurerm_client_config.current.object_id]
}

resource "azuread_service_principal" "github" {
  client_id = azuread_application.github.client_id
}

resource "azuread_application_password" "github" {
  application_id    = azuread_application.github.id
  display_name      = "GitHub Actions Deployment"
  end_date_relative = "8760h"
}

resource "azurerm_role_assignment" "github_contributor" {
  scope                = azurerm_resource_group.primary.id
  role_definition_name = "Contributor"
  principal_id         = azuread_service_principal.github.id
}

resource "azurerm_linux_web_app" "primary" {
  name                = local.web_app_name
  resource_group_name = azurerm_resource_group.primary.name
  location            = azurerm_resource_group.primary.location
  service_plan_id     = azurerm_service_plan.primary.id

  identity {
    type = "SystemAssigned"
  }

  site_config {
    application_stack {
      python_version = "3.12"
    }

    always_on  = true
    ftps_state = "Disabled"
  }

  app_settings = {
    "APP_ENV"                        = var.environment
    "DB_TYPE"                        = "mssql"
    "AZURE_SQL_CONNECTIONSTRING"     = local.sql_connection_string
    "SQLALCHEMY_DATABASE_URI"        = local.sql_connection_string
    "SECRET_KEY"                     = "change-me"
    "SCM_DO_BUILD_DURING_DEPLOYMENT" = "1"
    "WEBSITE_WEBDEPLOY_USE_SCM"      = "true"
  }

  connection_string {
    name  = "Database"
    type  = "SQLAzure"
    value = local.sql_connection_string
  }

  lifecycle {
    ignore_changes = [app_settings["SECRET_KEY"]]
  }
}
