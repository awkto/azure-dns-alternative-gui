# Azure DNS Alternative GUI

A custom web-based GUI for managing Azure DNS zones. This application provides a modern, user-friendly interface to view, add, edit, and delete DNS records using Azure Service Principal authentication.

![Azure DNS Manager](https://img.shields.io/badge/Azure-DNS%20Manager-blue)
![Python](https://img.shields.io/badge/Python-3.11+-green)
![Flask](https://img.shields.io/badge/Flask-3.0-lightgrey)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?logo=docker)

## Features

- 🌐 View all DNS records in a specific Azure DNS zone
- ➕ Add new DNS records (A, AAAA, CNAME, MX, TXT, NS, SOA, PTR, SRV)
- ✏️ Edit existing DNS records
- 🗑️ Delete DNS records
- 🔐 Secure authentication using Azure Service Principal
- ⚙️ Web-based configuration management
- 🎨 Modern, responsive web interface with dark mode
- 🔍 Advanced search and filtering by record type
- ⚡ Real-time updates without page refresh
- 🐳 Docker support for easy deployment

## Screenshots

### Light Mode
Modern gradient header with glassmorphism effects, dynamic type filters, and responsive table layout.

### Dark Mode
Beautiful dark theme with optimized colors and smooth transitions.

## Quick Start with Docker

The easiest way to run Azure DNS Manager is using Docker:

```bash
docker run -d -p 5000:5000 \
  -e AZURE_TENANT_ID=your-tenant-id \
  -e AZURE_CLIENT_ID=your-client-id \
  -e AZURE_CLIENT_SECRET=your-client-secret \
  -e AZURE_SUBSCRIPTION_ID=your-subscription-id \
  -e AZURE_RESOURCE_GROUP=your-resource-group \
  -e AZURE_DNS_ZONE=your-dns-zone.com \
  --name azure-dns-manager \
  yourusername/azure-dns-manager:latest
```

Then open `http://localhost:5000` in your browser.

## Architecture

- **Backend**: Python Flask REST API using Azure SDK for Python
- **Frontend**: Vanilla HTML/CSS/JavaScript
- **Authentication**: Azure Service Principal (Client Credentials)
- **Azure SDK**: Direct DNS management via Azure Management APIs

## Prerequisites

1. **Python 3.11 or higher** (for local development)
2. **Docker** (optional, for containerized deployment)
3. **Azure Subscription** with a DNS Zone
4. **Azure Service Principal** with appropriate permissions:
   - DNS Zone Contributor role on the DNS zone
   - Or custom role with permissions: `Microsoft.Network/dnszones/*`

## Deployment Options

### Option 1: Docker (Recommended)

#### Pull and Run from Docker Hub

```bash
# Pull the latest image
docker pull yourusername/azure-dns-manager:latest

# Run with environment variables
docker run -d \
  --name azure-dns-manager \
  -p 5000:5000 \
  -e AZURE_TENANT_ID=your-tenant-id \
  -e AZURE_CLIENT_ID=your-client-id \
  -e AZURE_CLIENT_SECRET=your-client-secret \
  -e AZURE_SUBSCRIPTION_ID=your-subscription-id \
  -e AZURE_RESOURCE_GROUP=your-resource-group \
  -e AZURE_DNS_ZONE=your-dns-zone.com \
  yourusername/azure-dns-manager:latest

# Or use a .env file
docker run -d \
  --name azure-dns-manager \
  -p 5000:5000 \
  --env-file .env \
  yourusername/azure-dns-manager:latest
```

#### Build Docker Image Locally

```bash
# Clone the repository
git clone https://github.com/yourusername/azure-dns-alternative-gui.git
cd azure-dns-alternative-gui

# Build the image
docker build -t azure-dns-manager .

# Run the container
docker run -d -p 5000:5000 --env-file .env azure-dns-manager
```

#### Docker Compose

Create a `docker-compose.yml`:

```yaml
version: '3.8'

services:
  azure-dns-manager:
    image: yourusername/azure-dns-manager:latest
    container_name: azure-dns-manager
    ports:
      - "5000:5000"
    environment:
      - AZURE_TENANT_ID=${AZURE_TENANT_ID}
      - AZURE_CLIENT_ID=${AZURE_CLIENT_ID}
      - AZURE_CLIENT_SECRET=${AZURE_CLIENT_SECRET}
      - AZURE_SUBSCRIPTION_ID=${AZURE_SUBSCRIPTION_ID}
      - AZURE_RESOURCE_GROUP=${AZURE_RESOURCE_GROUP}
      - AZURE_DNS_ZONE=${AZURE_DNS_ZONE}
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "python", "-c", "import requests; requests.get('http://localhost:5000/api/health')"]
      interval: 30s
      timeout: 10s
      retries: 3
```

Then run:
```bash
docker-compose up -d
```

### Option 2: Local Python Installation

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

## Configuration

### First-Time Setup

When you first access the application:

1. If Azure credentials are not configured, you'll be automatically redirected to the **Settings** page
2. Enter your Azure Service Principal credentials:
   - Tenant ID
   - Client ID
   - Client Secret
   - Subscription ID
   - Resource Group
   - DNS Zone name
3. Click **Test Connection** to verify your credentials
4. Click **Save Configuration** to persist the settings
5. You'll be redirected to the main page with your DNS records

### Updating Configuration

To update your Azure credentials later:

1. Click the **⚙️ Settings** button in the header
2. Update the required fields
3. Test and save the new configuration

### Environment Variables

All configuration can be provided via environment variables (useful for Docker):

```env
AZURE_TENANT_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
AZURE_CLIENT_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
AZURE_CLIENT_SECRET=your-client-secret
AZURE_SUBSCRIPTION_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
AZURE_RESOURCE_GROUP=your-resource-group
AZURE_DNS_ZONE=your-domain.com
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
| GET | `/api/config/status` | Check if configuration is complete |
| GET | `/api/config` | Get current configuration |
| POST | `/api/config` | Save configuration |
| POST | `/api/config/test` | Test Azure credentials |
| GET | `/api/records` | List all DNS records |
| POST | `/api/records` | Create a new DNS record |
| PUT | `/api/records/<type>/<name>` | Update a DNS record |
| DELETE | `/api/records/<type>/<name>` | Delete a DNS record |

## CI/CD Pipeline

This project includes automated Docker image building and publishing via GitHub Actions.

### Setting Up CI/CD

1. **Create Docker Hub Account** if you don't have one

2. **Generate Docker Hub Access Token**:
   - Go to Docker Hub → Account Settings → Security
   - Click "New Access Token"
   - Copy the token

3. **Add GitHub Secrets**:
   Go to your GitHub repository → Settings → Secrets and variables → Actions
   
   Add the following secrets:
   - `DOCKERHUB_USERNAME`: Your Docker Hub username
   - `DOCKERHUB_TOKEN`: Your Docker Hub access token

4. **Create and Push a Version Tag**:
   ```bash
   git tag v1.0.0
   git push origin v1.0.0
   ```

5. **Automated Build**: The GitHub Actions workflow will:
   - Build the Docker image for multiple platforms (amd64, arm64)
   - Tag it with the version number and `latest`
   - Push to Docker Hub
   - Create a GitHub release with Docker instructions

### Release Process

```bash
# Create a new version tag
git tag -a v1.2.3 -m "Release version 1.2.3"

# Push the tag to trigger the CI/CD pipeline
git push origin v1.2.3
```

The pipeline will automatically:
- Build multi-platform Docker images (linux/amd64, linux/arm64)
- Push to Docker Hub with tags: `v1.2.3` and `latest`
- Create a GitHub release with Docker run instructions
- Update the Docker Hub repository description

## Project Structure

```
azure-dns-alternative-gui/
├── .github/
│   └── workflows/
│       └── docker-publish.yml   # CI/CD pipeline for Docker
├── static/
│   ├── index.html               # Main DNS records page
│   ├── settings.html            # Configuration page
│   ├── app.js                   # Main page JavaScript
│   ├── settings.js              # Settings page JavaScript
│   └── styles.css               # Modern CSS with dark mode
├── app.py                       # Flask backend application
├── requirements.txt             # Python dependencies
├── Dockerfile                   # Docker image definition
├── .dockerignore               # Docker build exclusions
├── .env.example                # Example environment variables
├── .env                        # Your configuration (not in git)
├── .gitignore                  # Git ignore rules
└── README.md                   # This file
```

## Security Considerations

- ⚠️ This application does not include user authentication for the web interface
- 🔐 Azure credentials are stored in environment variables (never commit `.env` to git)
- 🌐 By default, the app runs on all interfaces (`0.0.0.0`) - consider restricting this in production
- 🔒 Ensure your Service Principal has minimal required permissions
- 🚫 Do not expose this application directly to the internet without proper security measures

## Troubleshooting

### Docker Issues

**Container won't start**
```bash
# Check container logs
docker logs azure-dns-manager

# Check if port is already in use
netstat -an | grep 5000  # Linux/Mac
netstat -ano | findstr :5000  # Windows
```

**Configuration not persisting**
- For Docker: Use environment variables or mount a volume for the .env file
```bash
docker run -d -p 5000:5000 -v $(pwd)/.env:/app/.env azure-dns-manager
```

### Local Development Issues

**"Module not found" errors**
```bash
pip install -r requirements.txt
```

**"Missing required environment variables" error**
Make sure you've created a `.env` file with all required values or configured via the Settings page.

### Azure authentication fails
- Verify your Service Principal credentials are correct
- Check that the Service Principal has appropriate permissions on the DNS zone
- Ensure the subscription ID, resource group, and DNS zone name are correct

### Cannot connect to the application
- Check that the application is running on port 5000
- Verify no firewall is blocking the connection
- Try accessing via `http://127.0.0.1:5000` instead

## Future Enhancements

- [x] User-friendly configuration management UI
- [x] Dark mode support
- [x] Advanced search and filtering
- [x] Docker containerization
- [x] CI/CD pipeline for automated releases
- [ ] User authentication and authorization
- [ ] HTTPS/TLS support
- [ ] Batch operations
- [ ] Record import/export (CSV, JSON)
- [ ] Audit logging and change history
- [ ] Multi-zone support
- [ ] Kubernetes deployment manifests
- [ ] Webhook notifications

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