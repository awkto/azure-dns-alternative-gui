# Azure DNS Alternative GUI

A custom web-based GUI for managing Azure DNS zones. This application provides a simple interface to view, add, edit, and delete DNS records using Azure Service Principal authentication.

![Azure DNS Manager](https://img.shields.io/badge/Azure-DNS%20Manager-blue)
![Python](https://img.shields.io/badge/Python-3.8+-green)
![Flask](https://img.shields.io/badge/Flask-3.0-lightgrey)

## Features

- 🌐 View all DNS records in a specific Azure DNS zone
- ➕ Add new DNS records (A, AAAA, CNAME, MX, TXT)
- ✏️ Edit existing DNS records
- 🗑️ Delete DNS records
- 🔐 Secure authentication using Azure Service Principal
- 🎨 Modern, responsive web interface
- ⚡ Real-time updates without page refresh

## Architecture

- **Backend**: Python Flask REST API using Azure SDK for Python
- **Frontend**: Vanilla HTML/CSS/JavaScript
- **Authentication**: Azure Service Principal (Client Credentials)
- **Azure SDK**: Direct DNS management via Azure Management APIs

## Prerequisites

1. **Python 3.8 or higher**
2. **Azure Subscription** with a DNS Zone
3. **Azure Service Principal** with appropriate permissions:
   - DNS Zone Contributor role on the DNS zone
   - Or custom role with permissions: `Microsoft.Network/dnszones/*`

## Setup Instructions

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/azure-dns-alternative-gui.git
cd azure-dns-alternative-gui
```

### 2. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 3. Create Azure Service Principal

If you don't have a Service Principal yet, create one:

```bash
# Login to Azure
az login

# Create a Service Principal
az ad sp create-for-rbac --name "dns-manager-sp" --role "DNS Zone Contributor" --scopes /subscriptions/{subscription-id}/resourceGroups/{resource-group}/providers/Microsoft.Network/dnszones/{dns-zone-name}
```

This command will output:
```json
{
  "appId": "your-client-id",
  "displayName": "dns-manager-sp",
  "password": "your-client-secret",
  "tenant": "your-tenant-id"
}
```

### 4. Configure Environment Variables

Copy the example environment file and fill in your Azure credentials:

```bash
cp .env.example .env
```

Edit `.env` with your values:

```env
# Azure Service Principal Credentials
AZURE_TENANT_ID=your-tenant-id-here
AZURE_CLIENT_ID=your-client-id-here
AZURE_CLIENT_SECRET=your-client-secret-here

# Azure DNS Configuration
AZURE_SUBSCRIPTION_ID=your-subscription-id-here
AZURE_RESOURCE_GROUP=your-resource-group-here
AZURE_DNS_ZONE=your-dns-zone.com
```

**Important**: Never commit the `.env` file to version control!

### 5. Run the Application

```bash
python app.py
```

The application will start on `http://localhost:5000`

### 6. Access the GUI

Open your web browser and navigate to:
```
http://localhost:5000
```

## Usage Guide

### Viewing DNS Records

The main page displays all DNS records in your configured zone in a table format showing:
- Record name and FQDN
- Record type (A, AAAA, CNAME, MX, TXT, etc.)
- TTL (Time To Live)
- Record values

### Adding a New Record

1. Fill in the "Add New DNS Record" form:
   - **Record Name**: Enter the subdomain name (e.g., `www`, `mail`) or `@` for the root domain
   - **Record Type**: Select from A, AAAA, CNAME, MX, or TXT
   - **TTL**: Set Time To Live in seconds (default: 3600)
   - **Values**: Enter record values (one per line)
     - For A records: IP addresses (e.g., `192.168.1.1`)
     - For CNAME: Target domain (e.g., `target.example.com`)
     - For MX: Priority and exchange (e.g., `10 mail.example.com`)
     - For TXT: Text values (e.g., `v=spf1 include:_spf.google.com ~all`)

2. Click "Add Record"

### Editing a Record

1. Click the "✏️ Edit" button next to any record
2. Modify the TTL or values in the modal dialog
3. Click "Update Record"

### Deleting a Record

1. Click the "🗑️ Delete" button next to any record
2. Confirm the deletion in the dialog

### Refreshing Records

Click the "🔄 Refresh" button in the header to reload all records from Azure.

## API Endpoints

The backend provides the following REST API endpoints:

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/health` | Health check and zone info |
| GET | `/api/records` | List all DNS records |
| POST | `/api/records` | Create a new DNS record |
| PUT | `/api/records/<type>/<name>` | Update a DNS record |
| DELETE | `/api/records/<type>/<name>` | Delete a DNS record |

## Project Structure

```
azure-dns-alternative-gui/
├── app.py                  # Flask backend application
├── requirements.txt        # Python dependencies
├── .env.example           # Example environment variables
├── .env                   # Your configuration (not in git)
├── .gitignore            # Git ignore rules
├── README.md             # This file
└── static/
    ├── index.html        # Main HTML page
    ├── app.js            # Frontend JavaScript
    └── styles.css        # CSS styling
```

## Security Considerations

- ⚠️ This application does not include user authentication for the web interface
- 🔐 Azure credentials are stored in environment variables (never commit `.env` to git)
- 🌐 By default, the app runs on all interfaces (`0.0.0.0`) - consider restricting this in production
- 🔒 Ensure your Service Principal has minimal required permissions
- 🚫 Do not expose this application directly to the internet without proper security measures

## Troubleshooting

### "Module not found" errors
```bash
pip install -r requirements.txt
```

### "Missing required environment variables" error
Make sure you've created a `.env` file with all required values.

### Azure authentication fails
- Verify your Service Principal credentials are correct
- Check that the Service Principal has appropriate permissions on the DNS zone
- Ensure the subscription ID, resource group, and DNS zone name are correct

### Cannot connect to the application
- Check that the application is running on port 5000
- Verify no firewall is blocking the connection
- Try accessing via `http://127.0.0.1:5000` instead

## Future Enhancements

- [ ] User authentication and authorization
- [ ] Support for more DNS record types (SRV, PTR, etc.)
- [ ] Batch operations
- [ ] Record import/export
- [ ] Audit logging
- [ ] Multi-zone support
- [ ] HTTPS support

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is open source and available under the MIT License.

## Acknowledgments

- Built with [Flask](https://flask.palletsprojects.com/)
- Azure integration via [Azure SDK for Python](https://github.com/Azure/azure-sdk-for-python)
- Icons: Emoji characters for simplicity

---

**Note**: This is a development tool. For production use, implement proper security measures including user authentication, HTTPS, and access controls.