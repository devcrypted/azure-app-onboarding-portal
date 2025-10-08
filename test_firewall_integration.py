"""
Quick integration test for firewall request creation with new structured schema.
Run with: uv run python test_firewall_integration.py
"""

import json
import requests

BASE_URL = "http://localhost:5000"
USER_EMAIL = "test@tradexfoods.com"

# Sample payload matching new schema
payload = {
    "source_application_id": None,  # Optional - would filter environments if provided
    "collection_name": "tradex-dev-test-collection",
    "application_name": "TradeX Test App",
    "organization": "McCain Foods",
    "lob": "Digital",
    "platform": "Azure",
    "environment_scopes": ["DEV", "TEST"],
    "destination_service": "Azure Firewall",
    "justification": "Testing new structured firewall request schema with rule collections",
    "requested_effective_date": None,
    "expires_at": None,
    "github_pr_url": None,
    "ip_groups": {
        "backend-servers": ["10.0.1.0/24", "10.0.2.0/24"],
        "web-servers": ["10.0.10.0/24"],
    },
    "application_rules": {
        "action": "Allow",
        "priority": None,  # Auto-calculate
        "rules": [
            {
                "name": "allow-https-outbound",
                "ritm_number": "RITM0012345",
                "description": "Allow HTTPS to external APIs",
                "protocols": [{"type": "Https", "port": 443}],
                "source_ip_addresses": ["10.0.0.0/16"],
                "source_ip_groups": ["backend-servers"],
                "destination_fqdns": ["*.azure.com", "api.example.com"],
                "destination_addresses": [],
            }
        ],
    },
    "network_rules": {
        "action": "Allow",
        "priority": None,  # Auto-calculate
        "rules": [
            {
                "name": "allow-sql-internal",
                "ritm_number": None,
                "description": "Allow SQL Server traffic to database subnet",
                "protocols": ["TCP"],
                "source_ip_addresses": ["10.0.10.0/24"],
                "source_ip_groups": ["web-servers"],
                "destination_ip_addresses": ["10.0.100.0/24"],
                "destination_ip_groups": [],
                "destination_ports": ["1433"],
                "destination_fqdns": [],
            }
        ],
    },
    "nat_rules": {
        "action": "Dnat",
        "priority": None,  # Auto-calculate
        "rules": [
            {
                "name": "dnat-web-to-internal",
                "ritm_number": None,
                "description": "NAT public IP to internal web server",
                "protocols": ["TCP"],
                "source_ip_addresses": ["0.0.0.0/0"],
                "source_ip_groups": [],
                "destination_address": "203.0.113.10",
                "destination_ports": ["443"],
                "translated_address": "10.0.10.100",
                "translated_port": 443,
            }
        ],
    },
}


def test_create_firewall_request():
    """Test creating a firewall request with structured rule collections."""
    print("=" * 80)
    print("Testing Firewall Request Creation (New Schema)")
    print("=" * 80)
    print()

    print("📤 Sending payload to /api/requests/firewall...")
    print(json.dumps(payload, indent=2))
    print()

    try:
        response = requests.post(
            f"{BASE_URL}/api/requests/firewall",
            json=payload,
            headers={"Content-Type": "application/json", "X-User-Email": USER_EMAIL},
            timeout=10,
        )

        print(f"📥 Response Status: {response.status_code}")
        print()

        if response.status_code == 201:
            data = response.json()
            print("✅ SUCCESS - Request created!")
            print(f"   Request ID: {data.get('request_id')}")
            print(f"   App ID: {data.get('app_id')}")
            print(f"   App Code: {data.get('app_code')}")
            print(f"   Status: {data.get('application_status')}")
            print()

            # Show collection document
            fw_request = data.get("firewall_request", {})
            if fw_request.get("collection_document"):
                print("📄 Generated Terraform Document:")
                doc = json.loads(fw_request["collection_document"])
                print(json.dumps(doc, indent=2))

            return True

        else:
            error_data = response.json()
            print(f"❌ ERROR - {response.status_code}")
            print(f"   Message: {error_data.get('error')}")
            if "details" in error_data:
                print("   Validation Errors:")
                for err in error_data["details"]:
                    print(f"     - {err.get('loc')}: {err.get('msg')}")
            if "duplicates" in error_data:
                print("   Duplicates detected:")
                for dup in error_data["duplicates"]:
                    print(f"     - Rule: {dup.get('rule', {}).get('name')}")

            return False

    except requests.exceptions.ConnectionError:
        print("❌ ERROR - Could not connect to server")
        print(f"   Make sure Flask is running at {BASE_URL}")
        print("   Run: uv run flask --app app.main:app run --debug")
        return False

    except Exception as e:
        print(f"❌ ERROR - Unexpected error: {e}")
        return False


if __name__ == "__main__":
    success = test_create_firewall_request()
    exit(0 if success else 1)
