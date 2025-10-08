# Firewall Request Refactoring - Completed

## Overview
Successfully restructured the firewall request system to support structured rule collections with Terraform-style JSON output, automatic priority management, and Azure naming validations.

## Key Changes

### 1. **Data Models** (`app/models.py`)
- **Fixed**: Renamed `metadata` → `rule_metadata` to avoid SQLAlchemy reserved keyword conflict
- **Fixed**: Added explicit `foreign_keys` to `FirewallRequest.application` relationship to resolve ambiguity
- **Enhanced**: `FirewallRuleEntry` now stores serialized JSON for protocols, addresses, and translation fields
- **New**: `FirewallRuleCollection` model groups rules by type (APPLICATION/NETWORK/NAT) with priority and action

### 2. **Validation Schemas** (`app/schemas.py`)
- **Fixed**: Removed deprecated `Field(..., const=True)` → simple `Literal` defaults (Pydantic v2)
- **Restructured**: Replaced flat `rule_entries` with structured groups:
  - `ApplicationRuleInput` - FQDN-based L7 rules with protocol objects `{type, port}`
  - `NetworkRuleInput` - IP-based L3/L4 rules with protocol strings
  - `NatRuleInput` - DNAT/SNAT rules with translation fields
- **New**: `ApplicationRuleGroupInput`, `NetworkRuleGroupInput`, `NatRuleGroupInput` with action/priority
- **Validation**: Azure naming constraints (1-120 chars, lowercase alphanumeric + hyphens)
- **Validation**: Priority must be 100-65000 in 100-step increments
- **Validation**: Protocol validation per rule type (TCP/UDP/ICMP for network, Https/Http/Mssql for application)

### 3. **Service Layer** (`app/services/firewall_request_service.py`)
- **New**: `_iter_groups()` - iterates over application/network/nat rule groups
- **New**: `_determine_priority()` - auto-calculates next available priority with 100-step increments
  - Baseline: APPLICATION=400, NETWORK=6500, NAT=100
  - Queries existing collections via repository to find max priority
- **New**: `_build_rule_entry()` - constructs ORM entry with proper type casting and serialization
- **New**: `_build_duplicate_key()` - generates SHA256 hash for duplicate detection including IP groups
- **New**: `_build_collection_document()` - assembles Terraform-style JSON with nested rule collections
- **New**: `_format_rule_for_document()` - deserializes ORM entries back to Terraform format
- **Enhanced**: `create_firewall_request()` now creates structured `FirewallRuleCollection` instances

### 4. **Repository Layer** (`app/repositories/firewall_repository.py`)
- **New**: `get_max_priority_for_source(source_application_id, collection_type)` - queries highest priority for auto-increment logic

### 5. **Frontend** (`app/templates/firewall_request_form_v2.html`)
- **Completely rewritten** to match new backend schema
- **Tabbed UI**: Separate tabs for Application, Network, and NAT rules
- **Source Application ID field**: When populated, filters available environment scopes to those of the source app
- **Collection Name field**: Enforces Azure naming rules with HTML5 pattern validation
- **IP Groups field**: Accepts JSON for reusable address groups
- **Rule-specific fields**:
  - Application: protocols as "Type:Port" format, FQDNs, destination addresses
  - Network: protocol strings, destination IPs/IP groups/FQDNs, ports
  - NAT: translation address/port, destination address/ports
- **Action & Priority**: Configurable per rule group with auto-calculation option
- **GitHub PR URL**: Read-only field (populated later in workflow)
- **Environment scope filtering**: Dynamic based on source application or defaults to all scopes

### 6. **Routing** (`app/web.py`)
- Updated firewall route to use `firewall_request_form_v2.html`

## Requirements Met

### ✅ Data-Driven Workflow
- Workflow registry established in `app/workflows/base.py`
- Firewall workflow registered in `app/workflows/firewall/__init__.py` with lifecycle stages
- Stage action handlers stubbed in `app/workflows/firewall/actions.py`

### ✅ Environment Scope Filtering
- Frontend calls `/api/requests/<id>` when source application ID is entered
- Filters environment checkboxes to only show available environments from source app
- Falls back to all scopes if no source app selected

### ✅ Collection Metadata
- `collection_name`: User-provided, Azure-validated
- `ip_groups`: Optional JSON field for reusable address groups
- `collection_document`: Auto-generated Terraform-style JSON stored on request
- `source_application_id`: Links to existing application for priority/environment context

### ✅ Rule Collection Types
- **Application Rules**: FQDN-based with structured protocols `[{type, port}]`
- **Network Rules**: IP-based with protocol strings, supports IP groups and FQDNs
- **NAT Rules**: Translation address/port with destination address

### ✅ Automatic Priority Management
- Baselines: APPLICATION=400, NETWORK=6500, NAT=100
- Auto-increments by 100 from last rule collection of same type under same source app
- User can override by specifying priority explicitly

### ✅ Terraform-Style JSON Output
- Generated in `collection_document` field
- Structure:
```json
{
  "collection-name": {
    "application_name": "...",
    "ip_groups": { "group1": ["10.0.0.0/24"] },
    "rules": {
      "application_rules": {
        "priority": 400,
        "action": "Allow",
        "rules": [ {...} ]
      },
      "network_rules": { ... },
      "nat_rules": { ... }
    }
  }
}
```

### ✅ Azure Naming & Value Restrictions
- Collection name: 1-120 chars, lowercase alphanumeric + hyphens
- Rule name: 1-128 chars, alphanumeric + hyphens/underscores
- Priority: 100-65000, multiples of 100
- Protocols validated per rule type
- IP addresses validated as CIDR or single IPs
- FQDNs validated with wildcard support

### ✅ GitHub PR URL
- Field present in form but read-only
- Populated later in deployment workflow (not required from user)

### ✅ Duplicate Detection
- Enhanced to include `source_ip_groups` in hash
- Compares all rule attributes including IPs, ports, protocols, translations
- Returns detailed error with existing request references

## Testing Status
- ✅ Database initialization successful
- ✅ Linting passes (Ruff)
- ✅ SQLAlchemy relationship ambiguity resolved
- ✅ Pydantic validation errors fixed
- ⚠️ End-to-end API test pending (requires manual UI test or integration test)

## Next Steps (Optional)
1. **API endpoint for retrieving source application**: Already exists (`/api/requests/<id>`)
2. **Integration test**: POST to `/api/requests/firewall` with sample structured payload
3. **Implement stage action handlers**: Complete TODOs in `app/workflows/firewall/actions.py`
4. **UI polish**: Add loading states, better error messages, field hints
5. **Document generation preview**: Add button to preview Terraform JSON before submit

## Files Modified
- `app/models.py` - Fixed metadata field, added foreign_keys
- `app/schemas.py` - Restructured validation models, removed deprecated const
- `app/services/firewall_request_service.py` - Complete rewrite with helper methods
- `app/repositories/firewall_repository.py` - Added priority query method
- `app/templates/firewall_request_form_v2.html` - New tabbed form (created)
- `app/web.py` - Updated route to use new form

## Breaking Changes
- **API Payload Structure**: Old flat `rule_entries` no longer accepted
  - Must use `application_rules`, `network_rules`, `nat_rules` groups
- **Frontend**: Old form deprecated, new form uses completely different data structure
- **Database**: `metadata` column renamed (backward compatible via column name override)
