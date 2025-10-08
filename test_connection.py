"""Test script to verify Azure DNS connection"""
from azure.identity import ClientSecretCredential
from azure.mgmt.dns import DnsManagementClient
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Azure credentials and configuration
TENANT_ID = os.getenv('AZURE_TENANT_ID')
CLIENT_ID = os.getenv('AZURE_CLIENT_ID')
CLIENT_SECRET = os.getenv('AZURE_CLIENT_SECRET')
SUBSCRIPTION_ID = os.getenv('AZURE_SUBSCRIPTION_ID')
RESOURCE_GROUP = os.getenv('AZURE_RESOURCE_GROUP')
DNS_ZONE = os.getenv('AZURE_DNS_ZONE')

print("Testing Azure DNS Connection...")
print(f"Tenant ID: {TENANT_ID}")
print(f"Client ID: {CLIENT_ID}")
print(f"Subscription ID: {SUBSCRIPTION_ID}")
print(f"Resource Group: {RESOURCE_GROUP}")
print(f"DNS Zone: {DNS_ZONE}")
print("-" * 50)

try:
    # Create credential
    print("\n1. Creating credentials...")
    credential = ClientSecretCredential(
        tenant_id=TENANT_ID,
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET
    )
    print("✓ Credentials created successfully")
    
    # Create DNS client
    print("\n2. Creating DNS Management Client...")
    client = DnsManagementClient(credential, SUBSCRIPTION_ID)
    print("✓ DNS client created successfully")
    
    # Try to list records
    print(f"\n3. Attempting to list records from zone: {DNS_ZONE}")
    record_sets = client.record_sets.list_by_dns_zone(
        RESOURCE_GROUP,
        DNS_ZONE
    )
    
    # Convert to list to actually execute the request
    records_list = list(record_sets)
    print(f"✓ Successfully retrieved {len(records_list)} records")
    
    # Display first few records
    print("\nFirst 5 records:")
    for i, record in enumerate(records_list[:5]):
        print(f"  - {record.name} ({record.type.split('/')[-1]}) TTL: {record.ttl}")
    
    print("\n" + "=" * 50)
    print("✓ Connection test PASSED!")
    print("=" * 50)
    
except Exception as e:
    import traceback
    print("\n" + "=" * 50)
    print("✗ Connection test FAILED!")
    print("=" * 50)
    print(f"\nError: {str(e)}")
    print("\nFull traceback:")
    print(traceback.format_exc())
