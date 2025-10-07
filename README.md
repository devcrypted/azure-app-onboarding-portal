# TradeX Platform Onboarding Portal

Enterprise-grade Flask application for managing platform onboarding requests
 with multi-stage workflows, audit logging, and Azure integrations.

## 🚀 Features

### Core Capabilities

- **Multi-Request Types**: Application onboarding, firewall rules, organization/LOB management, subscription tracking
- **Structured Firewall Workflow**: Dedicated rule builder with validation, duplicate detection, and environment scope tracking
- **Self-Service Portal**: Intuitive web interface for submitting and tracking requests
- **Admin Workflow**: Approval system with multi-stage pipeline (Draft → Approval → Subscription Assignment → Infrastructure → Handover)
- **Real-Time Tracking**: Live status updates with timeline visualization
- **Audit Trail**: Complete logging of all actions, changes, and approvals
- **Role-Based Access**: Admin panel with granular permissions
- **Dark/Light Mode**: Automatic theme switching based on system preferences

### Technical Stack

- **Backend**: Flask 3.1+ with SQLAlchemy ORM, Pydantic validation
- **Frontend**: TailwindCSS 3.x, Alpine.js 3.x, shadcn/ui design system
- **Database**: SQLite (development) / Azure SQL Server (production)
- **Auth**: Session-based (dev) / Azure AD OAuth (production-ready)
- **Notifications**: Azure Communication Services integration
- **Package Manager**: uv (fast Python package installer)

---

## 📁 Project Structure

```text
tradex-platform-onboarding/
├── app/
│   ├── core/                    # Infrastructure layer
│   │   ├── __init__.py
│   │   └── settings.py          # Pydantic-powered configuration
│   ├── domain/                  # Domain models (business entities)
│   ├── repositories/            # Data access layer (repository pattern)
│   ├── services/                # Business logic layer
│   ├── api.py                   # REST API endpoints
│   ├── web.py                   # Web UI routes
│   ├── models.py                # SQLAlchemy ORM models
│   ├── schemas.py               # Pydantic request/response schemas
│   ├── validation.py            # Extended validation logic
│   ├── email_service.py         # Email notification service
│   ├── utils.py                 # Utility functions
│   ├── main.py                  # Application factory
│   └── templates/               # Jinja2 HTML templates
│       ├── base.html            # Base layout with navigation
│       ├── index.html           # Landing page
│       ├── login.html           # Authentication page
│       ├── dashboard.html       # User dashboard
│       ├── request_form.html    # Onboarding request form
│       ├── firewall_request_form.html   # Firewall request workflow
│       ├── request_detail.html  # Request details with timeline
│       ├── requests.html        # All requests list
│       ├── admin.html           # Admin control panel
│       ├── admin_lookup.html    # Reference data management
│       └── 403.html             # Access denied page
├── instance/                    # SQLite database (auto-created)
├── .env                         # Environment variables (DO NOT COMMIT)
├── .env.example                 # Environment template
├── pyproject.toml               # Dependencies & metadata
├── uv.lock                      # Dependency lockfile
└── README.md                    # This file
```

## Quick Start

### Prerequisites

- Python 3.11+
- [uv](https://github.com/astral-sh/uv) package manager
- ODBC Driver 18 for SQL Server (for Azure SQL only)

### Installation

1. **Install dependencies**:

   ```bash
   uv sync
   ```

2. **Initialize database**:

   ```bash
   uv run flask --app app.main:app init-db
   ```

3. **Run the application**:

   ```bash
   uv run flask --app app.main:app run --debug
   ```

4. **Open browser**: `http://localhost:5000`

### Demo Login

- **Admin**: `admin@tradexfoods.com`
- **User**: Any other email address

## Configuration

### Environment Variables (.env)

**SQLite (Development)**:

```env
DB_TYPE=sqlite
SQLITE_DB_PATH=instance/tradex.db
SECRET_KEY=dev-secret-key-change-in-production
ADMIN_EMAILS=admin@tradexfoods.com
NETWORK_ADMIN_EMAILS=netadmin@tradexfoods.com
SQLALCHEMY_ECHO=false
SESSION_TYPE=filesystem
PERMANENT_SESSION_LIFETIME=3600
```

**Azure SQL (Production)**:

```env
DB_TYPE=mssql
MSSQL_SERVER=your-server.database.windows.net
MSSQL_DATABASE=tradex_metadata
MSSQL_USERNAME=your_username
MSSQL_PASSWORD=your_password
MSSQL_DRIVER=ODBC Driver 18 for SQL Server
SECRET_KEY=your-strong-secret-key
ADMIN_EMAILS=admin1@tradexfoods.com,admin2@tradexfoods.com
SQLALCHEMY_ECHO=false
SESSION_TYPE=filesystem
PERMANENT_SESSION_LIFETIME=7200
```

#### Connection string shortcut (Azure SQL)

- Copy the **ADO.NET** connection string from your Azure SQL resource.
- Set it as the `AZURE_SQL_CONNECTIONSTRING` environment variable. The application will
   automatically translate it into the right SQLAlchemy URI at startup.
- Alternatively, you can set your own `SQLALCHEMY_DATABASE_URI` if you prefer to manage
   the connection string yourself.

**Optional Integrations** (add as needed):

```env
# OAuth (Azure AD / Entra ID)
OAUTH_AUTHORITY=https://login.microsoftonline.com/<tenant-id>/v2.0
OAUTH_CLIENT_ID=<client-id>
OAUTH_CLIENT_SECRET=<client-secret>
OAUTH_REDIRECT_URI=https://localhost:5000/auth/callback
OAUTH_SCOPES=openid,profile,email,offline_access

# Email notifications
EMAIL_SMTP_SERVER=smtp.office365.com
EMAIL_SMTP_PORT=587
EMAIL_USERNAME=alerts@tradexfoods.com
EMAIL_PASSWORD=<smtp-password>
EMAIL_USE_TLS=true

# Azure Communication Services (SMS / Email fallback)
ACS_CONNECTION_STRING=endpoint=https://<resource-name>.communication.azure.com/;accesskey=<key>
ACS_SENDER=DoNotReply
```

### Admin Access

Admins are configured via the `ADMIN_EMAILS` environment variable (comma-separated list).
Only users with emails in this list can:

- See the "Admin" navigation link
- Access `/admin` and `/admin/lookup` pages
- Approve/reject onboarding requests

### Network Admin Access

Network-specific actions (firewall approvals, networking PR reviews) require the
`NETWORK_ADMIN_EMAILS` list. Only users defined here can approve firewall requests
and manage rule deployments.

## Database Schema

**Main Tables**:

- `applications` - Onboarding requests
- `app_environments` - Application environment mappings
- `lookup` - Reference data (Orgs, LOBs, Environments, Regions)
- `request_audit` - Audit trail

**Request Status Flow**:

```text
PENDING → APPROVED → PROVISIONING → COMPLETED
            ↓
         REJECTED
```

## Deployment

### Azure App Service (with GitHub Actions)

1. **Configure application settings** (Portal or CLI)
   - Set database mode: `DB_TYPE=mssql`
   - Provide your Azure SQL credentials either by populating
     `AZURE_SQL_CONNECTIONSTRING` **or** the individual
     `MSSQL_*` fields (`MSSQL_SERVER`, `MSSQL_DATABASE`, `MSSQL_USERNAME`, `MSSQL_PASSWORD`).
   - Keep the driver value aligned with the image: `MSSQL_DRIVER="ODBC Driver 18 for SQL Server"`.
   - Add any other secrets (e.g., `SECRET_KEY`, `ADMIN_EMAILS`, OAuth settings).

   ```powershell
   az webapp config appsettings set `
     --name <web-app-name> `
     --resource-group <resource-group> `
     --settings DB_TYPE=mssql `
                MSSQL_DRIVER="ODBC Driver 18 for SQL Server" `
                AZURE_SQL_CONNECTIONSTRING="Server=tcp:<server>.database.windows.net,1433;Database=<db>;User ID=<user>;Password=<password>;Encrypt=true;TrustServerCertificate=false;Connection Timeout=30" `
                SECRET_KEY="<your-secret>" `
                ADMIN_EMAILS="admin@tradexfoods.com"
   ```

2. **Set the startup command** so Azure launches Gunicorn using the included config:

   ```powershell
   az webapp config set `
     --name <web-app-name> `
     --resource-group <resource-group> `
     --startup-file "gunicorn -c gunicorn.conf.py app.main:app"
   ```

   The provided `gunicorn.conf.py` binds to the platform-assigned port, enables
   threaded workers, and preloads the Flask app for faster cold starts.

3. **Initialize the database** (once per environment). From your development machine
   you can run migrations against Azure SQL over the public endpoint:

   ```powershell
   uv run flask --app app.main:app init-db
   ```

   Ensure your local machine has network access to Azure SQL (firewall rule or private
   endpoint). Alternatively, run the command via the App Service console or a dedicated job.

4. **Deploy**. The included GitHub Actions workflow (`.github/workflows/main_apponboard.yml`)
   logs in with an Azure service principal and pushes the build artifacts to the App Service.
   On each push to `main`, the site is redeployed automatically.

### Production Checklist

- [ ] Change `SECRET_KEY` to a strong random value
- [ ] Configure `ADMIN_EMAILS` with actual admin emails
- [ ] Set up Azure SQL database connection
- [ ] Enable HTTPS (automatic on Azure App Service)
- [ ] Consider Azure AD OAuth for authentication
- [ ] Use Azure Key Vault for secrets

## Troubleshooting

**Port already in use**:

```bash
# Windows PowerShell
netstat -ano | findstr :5000
taskkill /PID <PID> /F
```

**Database issues**:

```bash
# Reinitialize database
uv run flask --app app.main:app init-db
```

---

**Version**: 0.1.0
**Built with**: Flask 3.1.2, TailwindCSS, shadcn/ui, Alpine.js
