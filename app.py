from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
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
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'zone': config.get('DNS_ZONE')})

@app.route('/api/config/status', methods=['GET'])
def config_status():
    """Check if Azure configuration is complete"""
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
    """Get current configuration (with masked secret)"""
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
    """Save Azure configuration"""
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
    """Test Azure credentials before saving"""
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
    """Get all DNS records from the zone"""
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
    """Create a new DNS record"""
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
    """Update an existing DNS record"""
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
    """Delete a DNS record"""
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
