from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from azure.identity import ClientSecretCredential
from azure.mgmt.dns import DnsManagementClient
from azure.mgmt.dns.models import RecordSet, ARecord, AaaaRecord, CnameRecord, MxRecord, TxtRecord
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

app = Flask(__name__, static_folder='static')
CORS(app)

# Azure credentials and configuration
TENANT_ID = os.getenv('AZURE_TENANT_ID')
CLIENT_ID = os.getenv('AZURE_CLIENT_ID')
CLIENT_SECRET = os.getenv('AZURE_CLIENT_SECRET')
SUBSCRIPTION_ID = os.getenv('AZURE_SUBSCRIPTION_ID')
RESOURCE_GROUP = os.getenv('AZURE_RESOURCE_GROUP')
DNS_ZONE = os.getenv('AZURE_DNS_ZONE')

# Initialize Azure DNS client
def get_dns_client():
    credential = ClientSecretCredential(
        tenant_id=TENANT_ID,
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET
    )
    return DnsManagementClient(credential, SUBSCRIPTION_ID)

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
    return jsonify({'status': 'healthy', 'zone': DNS_ZONE})

@app.route('/api/records', methods=['GET'])
def get_records():
    """Get all DNS records from the zone"""
    try:
        print(f"Attempting to connect to Azure DNS Zone: {DNS_ZONE}")
        print(f"Resource Group: {RESOURCE_GROUP}")
        print(f"Subscription ID: {SUBSCRIPTION_ID}")
        
        client = get_dns_client()
        record_sets = client.record_sets.list_by_dns_zone(
            RESOURCE_GROUP,
            DNS_ZONE
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
            if record_set.arecords:
                record_data['values'] = [r.ipv4_address for r in record_set.arecords]
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
        return jsonify({'records': records, 'zone': DNS_ZONE})
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
            record_set.arecords = [ARecord(ipv4_address=val) for val in values]
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
            RESOURCE_GROUP,
            DNS_ZONE,
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
            record_set.arecords = [ARecord(ipv4_address=val) for val in values]
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
            RESOURCE_GROUP,
            DNS_ZONE,
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
            RESOURCE_GROUP,
            DNS_ZONE,
            record_name,
            record_type
        )
        
        return jsonify({'message': 'Record deleted successfully', 'name': record_name})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    # Verify environment variables are set
    required_vars = ['AZURE_TENANT_ID', 'AZURE_CLIENT_ID', 'AZURE_CLIENT_SECRET', 
                     'AZURE_SUBSCRIPTION_ID', 'AZURE_RESOURCE_GROUP', 'AZURE_DNS_ZONE']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"ERROR: Missing required environment variables: {', '.join(missing_vars)}")
        print("Please copy .env.example to .env and fill in your Azure credentials.")
        exit(1)
    
    print(f"Starting Azure DNS Manager for zone: {DNS_ZONE}")
    app.run(debug=True, host='0.0.0.0', port=5000)
