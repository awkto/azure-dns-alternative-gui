from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from flasgger import Swagger, swag_from
from azure.identity import ClientSecretCredential
from azure.mgmt.dns import DnsManagementClient
from azure.mgmt.dns.models import RecordSet, ARecord, AaaaRecord, CnameRecord, MxRecord, TxtRecord
from dotenv import load_dotenv, set_key
import os
import json

# Load environment variables
load_dotenv()

app = Flask(__name__, static_folder='static')
CORS(app)

# Swagger configuration
swagger_config = {
    "headers": [],
    "specs": [
        {
            "endpoint": 'apispec',
            "route": '/apispec.json',
            "rule_filter": lambda rule: True,
            "model_filter": lambda tag: True,
        }
    ],
    "static_url_path": "/flasgger_static",
    "swagger_ui": True,
    "specs_route": "/apidocs"
}

swagger_template = {
    "swagger": "2.0",
    "info": {
        "title": "Azure DNS Manager API",
        "description": "REST API for managing Azure DNS zones and records",
        "version": "1.0.0",
        "contact": {
            "name": "Azure DNS Manager",
        }
    },
    "basePath": "/",
    "schemes": ["http", "https"],
    "tags": [
        {
            "name": "Health",
            "description": "Health check endpoints"
        },
        {
            "name": "Configuration",
            "description": "Azure configuration management"
        },
        {
            "name": "DNS Records",
            "description": "DNS record operations"
        }
    ]
}

swagger = Swagger(app, config=swagger_config, template=swagger_template)

# Azure credentials and configuration (mutable for runtime updates)
config = {
    'TENANT_ID': os.getenv('AZURE_TENANT_ID'),
    'CLIENT_ID': os.getenv('AZURE_CLIENT_ID'),
    'CLIENT_SECRET': os.getenv('AZURE_CLIENT_SECRET'),
    'SUBSCRIPTION_ID': os.getenv('AZURE_SUBSCRIPTION_ID'),
    'RESOURCE_GROUP': os.getenv('AZURE_RESOURCE_GROUP'),
    'DNS_ZONE': os.getenv('AZURE_DNS_ZONE')
}

# Legacy support - keep these for compatibility
TENANT_ID = config['TENANT_ID']
CLIENT_ID = config['CLIENT_ID']
CLIENT_SECRET = config['CLIENT_SECRET']
SUBSCRIPTION_ID = config['SUBSCRIPTION_ID']
RESOURCE_GROUP = config['RESOURCE_GROUP']
DNS_ZONE = config['DNS_ZONE']

def is_config_complete():
    """Check if all required configuration is present"""
    return all([
        config.get('TENANT_ID'),
        config.get('CLIENT_ID'),
        config.get('CLIENT_SECRET'),
        config.get('SUBSCRIPTION_ID'),
        config.get('RESOURCE_GROUP'),
        config.get('DNS_ZONE')
    ])

def update_config(new_config):
    """Update the configuration in memory and .env file"""
    global config, TENANT_ID, CLIENT_ID, CLIENT_SECRET, SUBSCRIPTION_ID, RESOURCE_GROUP, DNS_ZONE
    
    config.update(new_config)
    
    # Update global variables
    TENANT_ID = config['TENANT_ID']
    CLIENT_ID = config['CLIENT_ID']
    CLIENT_SECRET = config['CLIENT_SECRET']
    SUBSCRIPTION_ID = config['SUBSCRIPTION_ID']
    RESOURCE_GROUP = config['RESOURCE_GROUP']
    DNS_ZONE = config['DNS_ZONE']
    
    # Save to .env file
    env_file = '.env'
    if not os.path.exists(env_file):
        with open(env_file, 'w') as f:
            f.write('')
    
    set_key(env_file, 'AZURE_TENANT_ID', config['TENANT_ID'])
    set_key(env_file, 'AZURE_CLIENT_ID', config['CLIENT_ID'])
    set_key(env_file, 'AZURE_CLIENT_SECRET', config['CLIENT_SECRET'])
    set_key(env_file, 'AZURE_SUBSCRIPTION_ID', config['SUBSCRIPTION_ID'])
    set_key(env_file, 'AZURE_RESOURCE_GROUP', config['RESOURCE_GROUP'])
    set_key(env_file, 'AZURE_DNS_ZONE', config['DNS_ZONE'])

# Initialize Azure DNS client
def get_dns_client():
    """Get DNS client only if configuration is complete"""
    if not is_config_complete():
        raise ValueError("Azure configuration is incomplete. Please configure your credentials in Settings.")
    
    credential = ClientSecretCredential(
        tenant_id=config['TENANT_ID'],
        client_id=config['CLIENT_ID'],
        client_secret=config['CLIENT_SECRET']
    )
    return DnsManagementClient(credential, config['SUBSCRIPTION_ID'])

@app.route('/')
def index():
    """Serve the main HTML page"""
    return send_from_directory('static', 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    """Serve static files"""
    return send_from_directory('static', path)

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint
    ---
    tags:
      - Health
    summary: Check API health status
    description: Returns the health status of the API and the configured DNS zone
    responses:
      200:
        description: API is healthy
        schema:
          type: object
          properties:
            status:
              type: string
              example: healthy
            zone:
              type: string
              example: example.com
    """
    return jsonify({'status': 'healthy', 'zone': config.get('DNS_ZONE')})

@app.route('/api/config/status', methods=['GET'])
def config_status():
    """Check if Azure configuration is complete
    ---
    tags:
      - Configuration
    summary: Check configuration status
    description: Returns whether Azure credentials are configured
    responses:
      200:
        description: Configuration status
        schema:
          type: object
          properties:
            configured:
              type: boolean
              example: true
            zone:
              type: string
              example: example.com
            resource_group:
              type: string
              example: my-resource-group
      500:
        description: Server error
        schema:
          type: object
          properties:
            error:
              type: string
    """
    try:
        complete = is_config_complete()
        return jsonify({
            'configured': complete,
            'zone': config.get('DNS_ZONE') if complete else None,
            'resource_group': config.get('RESOURCE_GROUP') if complete else None
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/config', methods=['GET'])
def get_config():
    """Get current configuration (with masked secret)
    ---
    tags:
      - Configuration
    summary: Get current configuration
    description: Returns the current Azure configuration with client secret masked
    responses:
      200:
        description: Current configuration
        schema:
          type: object
          properties:
            tenant_id:
              type: string
              example: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
            client_id:
              type: string
              example: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
            client_secret:
              type: string
              example: "***"
            subscription_id:
              type: string
              example: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
            resource_group:
              type: string
              example: my-resource-group
            dns_zone:
              type: string
              example: example.com
            has_secret:
              type: boolean
              example: true
      500:
        description: Server error
        schema:
          type: object
          properties:
            error:
              type: string
    """
    try:
        client_secret = config.get('CLIENT_SECRET', '')
        masked_secret = client_secret if client_secret else ''

        return jsonify({
            'tenant_id': config.get('TENANT_ID', ''),
            'client_id': config.get('CLIENT_ID', ''),
            'client_secret': masked_secret,
            'subscription_id': config.get('SUBSCRIPTION_ID', ''),
            'resource_group': config.get('RESOURCE_GROUP', ''),
            'dns_zone': config.get('DNS_ZONE', ''),
            'has_secret': bool(client_secret)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/config', methods=['POST'])
def save_config():
    """Save Azure configuration
    ---
    tags:
      - Configuration
    summary: Save Azure configuration
    description: Save Azure Service Principal credentials and DNS zone configuration
    parameters:
      - in: body
        name: body
        description: Azure configuration
        required: true
        schema:
          type: object
          required:
            - tenant_id
            - client_id
            - client_secret
            - subscription_id
            - resource_group
            - dns_zone
          properties:
            tenant_id:
              type: string
              example: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
            client_id:
              type: string
              example: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
            client_secret:
              type: string
              example: your-client-secret
            subscription_id:
              type: string
              example: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
            resource_group:
              type: string
              example: my-resource-group
            dns_zone:
              type: string
              example: example.com
    responses:
      200:
        description: Configuration saved successfully
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: true
            message:
              type: string
              example: Configuration saved successfully
            zone:
              type: string
              example: example.com
      400:
        description: Missing required fields
        schema:
          type: object
          properties:
            error:
              type: string
      500:
        description: Server error
        schema:
          type: object
          properties:
            error:
              type: string
    """
    try:
        data = request.json

        # Validate required fields
        required_fields = ['tenant_id', 'client_id', 'client_secret', 'subscription_id', 'resource_group', 'dns_zone']
        missing_fields = [field for field in required_fields if not data.get(field)]

        if missing_fields:
            return jsonify({'error': f'Missing required fields: {", ".join(missing_fields)}'}), 400

        # Update configuration
        new_config = {
            'TENANT_ID': data['tenant_id'],
            'CLIENT_ID': data['client_id'],
            'CLIENT_SECRET': data['client_secret'],
            'SUBSCRIPTION_ID': data['subscription_id'],
            'RESOURCE_GROUP': data['resource_group'],
            'DNS_ZONE': data['dns_zone']
        }

        update_config(new_config)

        return jsonify({
            'success': True,
            'message': 'Configuration saved successfully',
            'zone': config['DNS_ZONE']
        })
    except Exception as e:
        print(f"Error saving configuration: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/config/test', methods=['POST'])
def test_config():
    """Test Azure credentials before saving
    ---
    tags:
      - Configuration
    summary: Test Azure credentials
    description: Validate Azure credentials by attempting to connect and list DNS records
    parameters:
      - in: body
        name: body
        description: Azure configuration to test
        required: true
        schema:
          type: object
          required:
            - tenant_id
            - client_id
            - client_secret
            - subscription_id
            - resource_group
            - dns_zone
          properties:
            tenant_id:
              type: string
              example: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
            client_id:
              type: string
              example: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
            client_secret:
              type: string
              example: your-client-secret
            subscription_id:
              type: string
              example: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
            resource_group:
              type: string
              example: my-resource-group
            dns_zone:
              type: string
              example: example.com
    responses:
      200:
        description: Connection test successful
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: true
            message:
              type: string
              example: Connection successful! Found 10 DNS records.
            record_count:
              type: integer
              example: 10
            zone:
              type: string
              example: example.com
      400:
        description: Missing required fields
        schema:
          type: object
          properties:
            error:
              type: string
      401:
        description: Authentication failed
        schema:
          type: object
          properties:
            error:
              type: string
      403:
        description: Authorization failed
        schema:
          type: object
          properties:
            error:
              type: string
      404:
        description: Resource not found
        schema:
          type: object
          properties:
            error:
              type: string
      500:
        description: Server error
        schema:
          type: object
          properties:
            error:
              type: string
    """
    try:
        data = request.json

        # Validate required fields
        required_fields = ['tenant_id', 'client_id', 'client_secret', 'subscription_id', 'resource_group', 'dns_zone']
        missing_fields = [field for field in required_fields if not data.get(field)]

        if missing_fields:
            return jsonify({'error': f'Missing required fields: {", ".join(missing_fields)}'}), 400

        # Try to create a client and list records
        try:
            credential = ClientSecretCredential(
                tenant_id=data['tenant_id'],
                client_id=data['client_id'],
                client_secret=data['client_secret']
            )
            test_client = DnsManagementClient(credential, data['subscription_id'])

            # Try to list records to verify access
            record_sets = list(test_client.record_sets.list_by_dns_zone(
                data['resource_group'],
                data['dns_zone']
            ))

            record_count = len(record_sets)

            return jsonify({
                'success': True,
                'message': f'Connection successful! Found {record_count} DNS records.',
                'record_count': record_count,
                'zone': data['dns_zone']
            })
        except Exception as azure_error:
            error_msg = str(azure_error)
            if 'AADSTS' in error_msg:
                return jsonify({'error': 'Authentication failed. Please check your Tenant ID, Client ID, and Client Secret.'}), 401
            elif 'ResourceGroupNotFound' in error_msg:
                return jsonify({'error': f'Resource group "{data["resource_group"]}" not found.'}), 404
            elif 'ResourceNotFound' in error_msg or 'ZoneNotFound' in error_msg:
                return jsonify({'error': f'DNS zone "{data["dns_zone"]}" not found in resource group "{data["resource_group"]}".'}), 404
            elif 'AuthorizationFailed' in error_msg:
                return jsonify({'error': 'Authorization failed. The service principal does not have permission to access this DNS zone.'}), 403
            else:
                return jsonify({'error': f'Connection failed: {error_msg}'}), 500

    except Exception as e:
        print(f"Error testing configuration: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/records', methods=['GET'])
def get_records():
    """Get all DNS records from the zone
    ---
    tags:
      - DNS Records
    summary: List all DNS records
    description: Retrieve all DNS records from the configured Azure DNS zone
    responses:
      200:
        description: List of DNS records
        schema:
          type: object
          properties:
            records:
              type: array
              items:
                type: object
                properties:
                  name:
                    type: string
                    example: www
                  type:
                    type: string
                    example: A
                  ttl:
                    type: integer
                    example: 3600
                  fqdn:
                    type: string
                    example: www.example.com
                  values:
                    type: array
                    items:
                      type: string
                    example: ["192.168.1.1"]
            zone:
              type: string
              example: example.com
      400:
        description: Configuration incomplete
        schema:
          type: object
          properties:
            error:
              type: string
      500:
        description: Server error
        schema:
          type: object
          properties:
            error:
              type: string
            details:
              type: string
    """
    try:
        # Check if configuration is complete
        if not is_config_complete():
            return jsonify({'error': 'Azure configuration is incomplete. Please configure your credentials.'}), 400

        print(f"Attempting to connect to Azure DNS Zone: {config['DNS_ZONE']}")
        print(f"Resource Group: {config['RESOURCE_GROUP']}")
        print(f"Subscription ID: {config['SUBSCRIPTION_ID']}")

        client = get_dns_client()
        record_sets = client.record_sets.list_by_dns_zone(
            config['RESOURCE_GROUP'],
            config['DNS_ZONE']
        )

        records = []
        for record_set in record_sets:
            record_data = {
                'name': record_set.name,
                'type': record_set.type.split('/')[-1],  # Extract record type (A, CNAME, etc.)
                'ttl': record_set.ttl,
                'fqdn': record_set.fqdn
            }

            # Extract record values based on type
            if record_set.a_records:
                record_data['values'] = [r.ipv4_address for r in record_set.a_records]
            elif record_set.aaaa_records:
                record_data['values'] = [r.ipv6_address for r in record_set.aaaa_records]
            elif record_set.cname_record:
                record_data['values'] = [record_set.cname_record.cname]
            elif record_set.mx_records:
                record_data['values'] = [f"{r.preference} {r.exchange}" for r in record_set.mx_records]
            elif record_set.txt_records:
                record_data['values'] = [' '.join(r.value) for r in record_set.txt_records]
            elif record_set.ns_records:
                record_data['values'] = [r.nsdname for r in record_set.ns_records]
            elif record_set.ptr_records:
                record_data['values'] = [r.ptrdname for r in record_set.ptr_records]
            elif record_set.srv_records:
                record_data['values'] = [f"{r.priority} {r.weight} {r.port} {r.target}" for r in record_set.srv_records]
            else:
                record_data['values'] = []

            records.append(record_data)

        print(f"Successfully retrieved {len(records)} records")
        return jsonify({'records': records, 'zone': config['DNS_ZONE']})
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"ERROR: {str(e)}")
        print(error_details)
        return jsonify({'error': str(e), 'details': error_details}), 500

@app.route('/api/records', methods=['POST'])
def create_record():
    """Create a new DNS record
    ---
    tags:
      - DNS Records
    summary: Create a new DNS record
    description: Add a new DNS record to the configured Azure DNS zone
    parameters:
      - in: body
        name: body
        description: DNS record details
        required: true
        schema:
          type: object
          required:
            - name
            - type
            - values
          properties:
            name:
              type: string
              example: www
              description: The record name (subdomain) or @ for the root domain
            type:
              type: string
              enum: [A, AAAA, CNAME, MX, TXT]
              example: A
              description: The DNS record type
            ttl:
              type: integer
              example: 3600
              default: 3600
              description: Time To Live in seconds
            values:
              type: array
              items:
                type: string
              example: ["192.168.1.1"]
              description: Array of record values (format depends on record type)
    responses:
      201:
        description: Record created successfully
        schema:
          type: object
          properties:
            message:
              type: string
              example: Record created successfully
            name:
              type: string
              example: www
      400:
        description: Missing required fields or validation error
        schema:
          type: object
          properties:
            error:
              type: string
      500:
        description: Server error
        schema:
          type: object
          properties:
            error:
              type: string
    """
    try:
        data = request.json
        record_name = data.get('name')
        record_type = data.get('type')
        ttl = data.get('ttl', 3600)
        values = data.get('values', [])

        if not record_name or not record_type or not values:
            return jsonify({'error': 'Missing required fields: name, type, values'}), 400

        client = get_dns_client()

        # Create the appropriate record set based on type
        record_set = RecordSet(ttl=ttl)

        if record_type == 'A':
            record_set.a_records = [ARecord(ipv4_address=val) for val in values]
        elif record_type == 'AAAA':
            record_set.aaaa_records = [AaaaRecord(ipv6_address=val) for val in values]
        elif record_type == 'CNAME':
            if len(values) > 1:
                return jsonify({'error': 'CNAME records can only have one value'}), 400
            record_set.cname_record = CnameRecord(cname=values[0])
        elif record_type == 'MX':
            mx_records = []
            for val in values:
                parts = val.split(' ', 1)
                if len(parts) == 2:
                    mx_records.append(MxRecord(preference=int(parts[0]), exchange=parts[1]))
            record_set.mx_records = mx_records
        elif record_type == 'TXT':
            record_set.txt_records = [TxtRecord(value=[val]) for val in values]
        else:
            return jsonify({'error': f'Unsupported record type: {record_type}'}), 400

        # Create the record
        result = client.record_sets.create_or_update(
            config['RESOURCE_GROUP'],
            config['DNS_ZONE'],
            record_name,
            record_type,
            record_set
        )

        return jsonify({'message': 'Record created successfully', 'name': record_name}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/records/<record_type>/<path:record_name>', methods=['PUT'])
def update_record(record_type, record_name):
    """Update an existing DNS record
    ---
    tags:
      - DNS Records
    summary: Update a DNS record
    description: Update an existing DNS record's TTL and values
    parameters:
      - in: path
        name: record_type
        type: string
        required: true
        description: The DNS record type (A, AAAA, CNAME, MX, TXT)
        example: A
      - in: path
        name: record_name
        type: string
        required: true
        description: The record name (subdomain) or @ for the root domain
        example: www
      - in: body
        name: body
        description: Updated record details
        required: true
        schema:
          type: object
          required:
            - values
          properties:
            ttl:
              type: integer
              example: 3600
              default: 3600
              description: Time To Live in seconds
            values:
              type: array
              items:
                type: string
              example: ["192.168.1.1"]
              description: Array of record values (format depends on record type)
    responses:
      200:
        description: Record updated successfully
        schema:
          type: object
          properties:
            message:
              type: string
              example: Record updated successfully
            name:
              type: string
              example: www
      400:
        description: Missing required fields or validation error
        schema:
          type: object
          properties:
            error:
              type: string
      500:
        description: Server error
        schema:
          type: object
          properties:
            error:
              type: string
    """
    try:
        data = request.json
        ttl = data.get('ttl', 3600)
        values = data.get('values', [])

        if not values:
            return jsonify({'error': 'Missing required field: values'}), 400

        client = get_dns_client()

        # Create the appropriate record set based on type
        record_set = RecordSet(ttl=ttl)

        if record_type == 'A':
            record_set.a_records = [ARecord(ipv4_address=val) for val in values]
        elif record_type == 'AAAA':
            record_set.aaaa_records = [AaaaRecord(ipv6_address=val) for val in values]
        elif record_type == 'CNAME':
            if len(values) > 1:
                return jsonify({'error': 'CNAME records can only have one value'}), 400
            record_set.cname_record = CnameRecord(cname=values[0])
        elif record_type == 'MX':
            mx_records = []
            for val in values:
                parts = val.split(' ', 1)
                if len(parts) == 2:
                    mx_records.append(MxRecord(preference=int(parts[0]), exchange=parts[1]))
            record_set.mx_records = mx_records
        elif record_type == 'TXT':
            record_set.txt_records = [TxtRecord(value=[val]) for val in values]
        else:
            return jsonify({'error': f'Unsupported record type: {record_type}'}), 400

        # Update the record
        result = client.record_sets.create_or_update(
            config['RESOURCE_GROUP'],
            config['DNS_ZONE'],
            record_name,
            record_type,
            record_set
        )

        return jsonify({'message': 'Record updated successfully', 'name': record_name})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/records/<record_type>/<path:record_name>', methods=['DELETE'])
def delete_record(record_type, record_name):
    """Delete a DNS record
    ---
    tags:
      - DNS Records
    summary: Delete a DNS record
    description: Remove a DNS record from the configured Azure DNS zone
    parameters:
      - in: path
        name: record_type
        type: string
        required: true
        description: The DNS record type (A, AAAA, CNAME, MX, TXT)
        example: A
      - in: path
        name: record_name
        type: string
        required: true
        description: The record name (subdomain) or @ for the root domain
        example: www
    responses:
      200:
        description: Record deleted successfully
        schema:
          type: object
          properties:
            message:
              type: string
              example: Record deleted successfully
            name:
              type: string
              example: www
      500:
        description: Server error
        schema:
          type: object
          properties:
            error:
              type: string
    """
    try:
        client = get_dns_client()

        # Delete the record
        client.record_sets.delete(
            config['RESOURCE_GROUP'],
            config['DNS_ZONE'],
            record_name,
            record_type
        )

        return jsonify({'message': 'Record deleted successfully', 'name': record_name})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    # Check if environment variables are set and log a warning if not
    required_vars = ['AZURE_TENANT_ID', 'AZURE_CLIENT_ID', 'AZURE_CLIENT_SECRET', 
                     'AZURE_SUBSCRIPTION_ID', 'AZURE_RESOURCE_GROUP', 'AZURE_DNS_ZONE']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"WARNING: Missing environment variables: {', '.join(missing_vars)}")
        print("The application will start, but you need to configure Azure credentials in Settings.")
        print(f"Starting Azure DNS Manager (unconfigured)")
    else:
        print(f"Starting Azure DNS Manager for zone: {DNS_ZONE}")
    
    app.run(debug=True, host='0.0.0.0', port=5000)
