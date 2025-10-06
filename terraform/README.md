# Azure Infrastructure Terraform Deployment

This module provisions all cloud assets required by the onboarding portal:

- Resource group
- Azure SQL logical server and database (serverless, auto-pausing)
- App Service Plan (Linux) and App Service configured for the Flask app
- Connection string wiring between the App Service and Azure SQL
- Azure AD application, service principal, and RBAC assignment for GitHub Actions deploys

## Prerequisites

- Terraform v1.6 or newer
- Azure CLI logged in with sufficient privileges (Contributor on the target subscription)
- (Optional) GitHub personal access token if you plan to automate creation of repository secrets

## Usage

```powershell
cd terraform
terraform init
terraform apply `
  -var "project_name=apponboard" `
  -var "environment=prod" `
   -var "location=Central India"
```

### Important Variables

| Variable | Description | Default |
| --- | --- | --- |
| `subscription_id` | Target subscription. Leave empty to inherit from Azure CLI/SP context. | `null` |
| `tenant_id` | Azure AD tenant. Leave empty to inherit from default context. | `null` |
| `project_name` | Short name used in resource naming. | `apponboard` |
| `environment` | Environment suffix (dev/test/prod). | `prod` |
| `location` | Azure region for all resources. | `Central India` |
| `github_owner` | GitHub account or organization. | `devcrypted` |
| `github_repository` | Repository name (without owner). | `azure-app-onboarding-portal` |
| `github_branch` | Branch to deploy from. | `main` |
| `app_service_sku` | Linux App Service Plan SKU. | `B1` |
| `sql_sku_name` | Azure SQL Database SKU. | `Basic` |
| `sql_auto_pause_delay` | Auto-pause delay for serverless tiers (set when using serverless SKUs). | `null` |

### Post-Deployment Steps

1. Copy the `service_principal_client_id`, `service_principal_secret`, and `service_principal_tenant_id`
   outputs into GitHub repository secrets:

   - `AZUREAPPSERVICE_CLIENTID`
   - `AZUREAPPSERVICE_CLIENTSECRET`
   - `AZUREAPPSERVICE_TENANTID`
   - `AZUREAPPSERVICE_SUBSCRIPTIONID` (use the subscription you deployed to)

2. Update `.github/workflows/main_apponboard.yml` secrets references if needed. The workflow already
   expects the secret names above.

3. (Optional) Rotate the generated secrets by re-running `terraform apply -replace=azuread_service_principal_password.github`.

4. Trigger the GitHub Actions workflow to deploy the newly provisioned App Service. The workflow
   uses the generated service principal to publish the application package.

### Destroying Resources

```powershell
terraform destroy
```

## Notes

- The App Service is configured with system-assigned managed identity for future enhancements.
- The SQL database defaults to the `Basic` tier to minimize cost. Update `sql_sku_name`,
  `sql_auto_pause_delay`, or other settings if you need higher performance or serverless capabilities.
- Secrets and sensitive outputs are marked accordingly; use secure storage when persisting them.
