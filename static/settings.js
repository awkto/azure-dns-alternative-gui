const API_BASE_URL = 'http://localhost:5000/api';

// DOM Elements
const settingsForm = document.getElementById('settingsForm');
const testConnectionBtn = document.getElementById('testConnectionBtn');
const loadingMessage = document.getElementById('loadingMessage');
const successMessage = document.getElementById('successMessage');
const errorMessage = document.getElementById('errorMessage');

const tenantIdInput = document.getElementById('tenantId');
const clientIdInput = document.getElementById('clientId');
const clientSecretInput = document.getElementById('clientSecret');
const subscriptionIdInput = document.getElementById('subscriptionId');
const resourceGroupInput = document.getElementById('resourceGroup');
const dnsZoneInput = document.getElementById('dnsZone');

const toggleSecretBtn = document.getElementById('toggleSecretBtn');
const eyeIcon = document.getElementById('eyeIcon');
const eyeOffIcon = document.getElementById('eyeOffIcon');

// Track if this is a first-time setup
let isSetupMode = false;

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    loadCurrentConfig();
    
    settingsForm.addEventListener('submit', handleSaveConfig);
    testConnectionBtn.addEventListener('click', handleTestConnection);
    toggleSecretBtn.addEventListener('click', toggleSecretVisibility);
});

// Toggle secret visibility
function toggleSecretVisibility() {
    if (clientSecretInput.type === 'password') {
        clientSecretInput.type = 'text';
        eyeIcon.style.display = 'none';
        eyeOffIcon.style.display = 'block';
    } else {
        clientSecretInput.type = 'password';
        eyeIcon.style.display = 'block';
        eyeOffIcon.style.display = 'none';
    }
}

// Load current configuration
async function loadCurrentConfig() {
    try {
        showLoading(true);
        hideMessages();
        
        const response = await fetch(`${API_BASE_URL}/config`);
        const data = await response.json();
        
        if (response.ok) {
            // Check if any configuration is missing (SETUP MODE)
            const hasAnyConfig = data.tenant_id || data.client_id || data.subscription_id || 
                                data.resource_group || data.dns_zone;
            
            isSetupMode = !hasAnyConfig;
            
            // Update UI based on setup mode
            const backNavigation = document.getElementById('backNavigation');
            const settingsDescription = document.getElementById('settingsDescription');
            
            if (isSetupMode) {
                // Hide back button in setup mode
                if (backNavigation) {
                    backNavigation.style.display = 'none';
                }
                // Update description for first-time setup
                if (settingsDescription) {
                    settingsDescription.innerHTML = '🚀 <strong>Welcome!</strong> Please configure your Azure credentials to get started.';
                }
            } else {
                // Show back button when configuration exists
                if (backNavigation) {
                    backNavigation.style.display = 'block';
                }
            }
            
            // Populate form with current config
            tenantIdInput.value = data.tenant_id || '';
            clientIdInput.value = data.client_id || '';
            clientSecretInput.value = data.client_secret || '';
            subscriptionIdInput.value = data.subscription_id || '';
            resourceGroupInput.value = data.resource_group || '';
            dnsZoneInput.value = data.dns_zone || '';
            
            // Make secret field not required if it exists
            if (data.has_secret) {
                clientSecretInput.required = false;
            }
        }
        
        showLoading(false);
    } catch (error) {
        showLoading(false);
        showError(`Failed to load configuration: ${error.message}`);
    }
}

// Test connection
async function handleTestConnection(e) {
    e.preventDefault();
    
    try {
        hideMessages();
        testConnectionBtn.disabled = true;
        testConnectionBtn.innerHTML = '<span>Testing...</span>';
        
        const config = getFormData();
        
        // Validate required fields
        if (!validateConfig(config)) {
            showError('Please fill in all required fields');
            return;
        }
        
        const response = await fetch(`${API_BASE_URL}/config/test`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(config),
        });
        
        const data = await response.json();
        
        if (response.ok) {
            showSuccess(`✅ ${data.message}`);
        } else {
            showError(data.error || 'Connection test failed');
        }
    } catch (error) {
        showError(`Test failed: ${error.message}`);
    } finally {
        testConnectionBtn.disabled = false;
        testConnectionBtn.innerHTML = `
            <svg class="btn-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
            </svg>
            Test Connection
        `;
    }
}

// Save configuration
async function handleSaveConfig(e) {
    e.preventDefault();
    
    try {
        hideMessages();
        
        const config = getFormData();
        
        // Validate required fields
        if (!validateConfig(config)) {
            showError('Please fill in all required fields');
            return;
        }
        
        const response = await fetch(`${API_BASE_URL}/config`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(config),
        });
        
        const data = await response.json();
        
        if (response.ok) {
            showSuccess(`✅ Configuration saved successfully! DNS Zone: ${data.zone}`);
            
            // Redirect to main page after 2 seconds
            setTimeout(() => {
                window.location.href = '/';
            }, 2000);
        } else {
            showError(data.error || 'Failed to save configuration');
        }
    } catch (error) {
        showError(`Save failed: ${error.message}`);
    }
}

// Helper functions
function getFormData() {
    return {
        tenant_id: tenantIdInput.value.trim(),
        client_id: clientIdInput.value.trim(),
        client_secret: clientSecretInput.value.trim(),
        subscription_id: subscriptionIdInput.value.trim(),
        resource_group: resourceGroupInput.value.trim(),
        dns_zone: dnsZoneInput.value.trim()
    };
}

function validateConfig(config) {
    return config.tenant_id && config.client_id && config.client_secret && 
           config.subscription_id && config.resource_group && config.dns_zone;
}

function showLoading(show) {
    loadingMessage.style.display = show ? 'block' : 'none';
}

function showSuccess(message) {
    successMessage.textContent = message;
    successMessage.style.display = 'block';
    errorMessage.style.display = 'none';
    
    // Auto-hide after 10 seconds
    setTimeout(() => {
        successMessage.style.display = 'none';
    }, 10000);
}

function showError(message) {
    errorMessage.textContent = message;
    errorMessage.style.display = 'block';
    successMessage.style.display = 'none';
}

function hideMessages() {
    successMessage.style.display = 'none';
    errorMessage.style.display = 'none';
}
