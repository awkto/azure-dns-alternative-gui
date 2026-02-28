// Use relative URL so it works regardless of hostname/IP
const API_BASE_URL = '/api';

// Auth check — redirect to setup or login if not authenticated
async function checkAuth() {
    try {
        const response = await fetch(`${API_BASE_URL}/auth/status`);
        const data = await response.json();
        if (data.setup_required) {
            window.location.href = '/setup.html';
            return false;
        }
        if (!data.authenticated) {
            window.location.href = '/login.html';
            return false;
        }
        return true;
    } catch (error) {
        console.error('Auth check failed:', error);
        window.location.href = '/login.html';
        return false;
    }
}

// Wrap fetch to intercept 401 responses globally
const _originalFetch = window.fetch;
window.fetch = async function(...args) {
    const response = await _originalFetch.apply(this, args);
    if (response.status === 401) {
        const url = typeof args[0] === 'string' ? args[0] : args[0]?.url || '';
        if (!url.includes('/api/auth/')) {
            window.location.href = '/login.html';
        }
    }
    return response;
};

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

// Raw mode state
let rawMode = false;

const ENV_KEY_MAP = {
    'AZURE_TENANT_ID':       'tenant_id',
    'AZURE_CLIENT_ID':       'client_id',
    'AZURE_CLIENT_SECRET':   'client_secret',
    'AZURE_SUBSCRIPTION_ID': 'subscription_id',
    'AZURE_RESOURCE_GROUP':  'resource_group',
    'AZURE_DNS_ZONE':        'dns_zone',
};

function serializeToRaw() {
    return [
        `AZURE_TENANT_ID='${tenantIdInput.value}'`,
        `AZURE_CLIENT_ID='${clientIdInput.value}'`,
        `AZURE_CLIENT_SECRET='${clientSecretInput.value}'`,
        `AZURE_SUBSCRIPTION_ID='${subscriptionIdInput.value}'`,
        `AZURE_RESOURCE_GROUP='${resourceGroupInput.value}'`,
        `AZURE_DNS_ZONE='${dnsZoneInput.value}'`,
    ].join('\n');
}

function parseRaw(text) {
    text = (text || '').trim();
    if (!text) return {};

    // Try JSON first
    if (text.startsWith('{')) {
        try {
            const obj = JSON.parse(text);
            const result = {};
            for (const [envKey, fieldKey] of Object.entries(ENV_KEY_MAP)) {
                if (obj[fieldKey]  !== undefined) result[fieldKey] = obj[fieldKey];
                else if (obj[envKey] !== undefined) result[fieldKey] = obj[envKey];
            }
            return result;
        } catch (e) { /* fall through */ }
    }

    // .env format: KEY=value  or  KEY='value'  or  KEY="value"
    const result = {};
    for (const line of text.split('\n')) {
        const trimmed = line.trim();
        if (!trimmed || trimmed.startsWith('#')) continue;
        const eqIdx = trimmed.indexOf('=');
        if (eqIdx === -1) continue;
        const key = trimmed.slice(0, eqIdx).trim();
        let val = trimmed.slice(eqIdx + 1).trim();
        if ((val.startsWith("'") && val.endsWith("'")) ||
            (val.startsWith('"') && val.endsWith('"'))) {
            val = val.slice(1, -1);
        }
        const fieldKey = ENV_KEY_MAP[key];
        if (fieldKey) result[fieldKey] = val;
    }
    return result;
}

function toggleRawMode() {
    const azureFormFields = document.getElementById('azureFormFields');
    const rawInput = document.getElementById('rawConfigInput');
    const toggleBtn = document.getElementById('toggleRawModeBtn');

    if (!rawMode) {
        // Form → Raw: serialize current values into textarea
        rawInput.value = serializeToRaw();
        azureFormFields.style.display = 'none';
        rawInput.style.display = 'block';
        rawInput.focus();
        toggleBtn.innerHTML = `
            <svg class="btn-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24" style="width:14px;height:14px;">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16"/>
            </svg>
            Form`;
        rawMode = true;
    } else {
        // Raw → Form: parse textarea back into fields
        const parsed = parseRaw(rawInput.value);
        if (parsed.tenant_id       !== undefined) tenantIdInput.value       = parsed.tenant_id;
        if (parsed.client_id       !== undefined) clientIdInput.value       = parsed.client_id;
        if (parsed.client_secret   !== undefined) clientSecretInput.value   = parsed.client_secret;
        if (parsed.subscription_id !== undefined) subscriptionIdInput.value = parsed.subscription_id;
        if (parsed.resource_group  !== undefined) resourceGroupInput.value  = parsed.resource_group;
        if (parsed.dns_zone        !== undefined) dnsZoneInput.value        = parsed.dns_zone;
        rawInput.style.display = 'none';
        azureFormFields.style.display = 'block';
        toggleBtn.innerHTML = `
            <svg class="btn-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24" style="width:14px;height:14px;">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4"/>
            </svg>
            Raw`;
        rawMode = false;
    }
}

// Initialize
document.addEventListener('DOMContentLoaded', async () => {
    // Check authentication first
    const isAuthenticated = await checkAuth();
    if (!isAuthenticated) return;

    loadCurrentConfig();
    loadApiToken();

    settingsForm.addEventListener('submit', handleSaveConfig);
    testConnectionBtn.addEventListener('click', handleTestConnection);
    toggleSecretBtn.addEventListener('click', toggleSecretVisibility);

    const toggleRawModeBtn = document.getElementById('toggleRawModeBtn');
    if (toggleRawModeBtn) {
        toggleRawModeBtn.addEventListener('click', toggleRawMode);
    }

    const toggleTokenBtn = document.getElementById('toggleTokenBtn');
    if (toggleTokenBtn) {
        toggleTokenBtn.addEventListener('click', toggleApiTokenVisibility);
    }

    const copyTokenBtn = document.getElementById('copyTokenBtn');
    if (copyTokenBtn) {
        copyTokenBtn.addEventListener('click', copyApiToken);
    }

    const regenerateTokenBtn = document.getElementById('regenerateTokenBtn');
    if (regenerateTokenBtn) {
        regenerateTokenBtn.addEventListener('click', regenerateApiToken);
    }
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
    if (rawMode) {
        const rawInput = document.getElementById('rawConfigInput');
        const parsed = parseRaw(rawInput ? rawInput.value : '');
        return {
            tenant_id:       (parsed.tenant_id       || '').trim(),
            client_id:       (parsed.client_id       || '').trim(),
            client_secret:   (parsed.client_secret   || '').trim(),
            subscription_id: (parsed.subscription_id || '').trim(),
            resource_group:  (parsed.resource_group  || '').trim(),
            dns_zone:        (parsed.dns_zone         || '').trim(),
        };
    }
    return {
        tenant_id:       tenantIdInput.value.trim(),
        client_id:       clientIdInput.value.trim(),
        client_secret:   clientSecretInput.value.trim(),
        subscription_id: subscriptionIdInput.value.trim(),
        resource_group:  resourceGroupInput.value.trim(),
        dns_zone:        dnsZoneInput.value.trim(),
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

// API Token management
async function loadApiToken() {
    try {
        const response = await fetch(`${API_BASE_URL}/auth/token`);
        if (!response.ok) return;
        const data = await response.json();
        const tokenInput = document.getElementById('apiTokenInput');
        if (tokenInput) tokenInput.value = data.api_token;
    } catch (error) {
        console.error('Failed to load API token:', error);
    }
}

function toggleApiTokenVisibility() {
    const tokenInput = document.getElementById('apiTokenInput');
    const eyeEl = document.getElementById('tokenEyeIcon');
    const eyeOffEl = document.getElementById('tokenEyeOffIcon');
    if (!tokenInput) return;
    if (tokenInput.type === 'password') {
        tokenInput.type = 'text';
        if (eyeEl) eyeEl.style.display = 'none';
        if (eyeOffEl) eyeOffEl.style.display = 'block';
    } else {
        tokenInput.type = 'password';
        if (eyeEl) eyeEl.style.display = 'block';
        if (eyeOffEl) eyeOffEl.style.display = 'none';
    }
}

async function copyApiToken() {
    const tokenInput = document.getElementById('apiTokenInput');
    if (!tokenInput || !tokenInput.value) return;
    try {
        await navigator.clipboard.writeText(tokenInput.value);
        showSuccess('API token copied to clipboard');
    } catch (e) {
        showError('Failed to copy token');
    }
}

async function regenerateApiToken() {
    if (!confirm('Regenerate the API token? Any scripts using the old token will need to be updated.')) return;
    try {
        const response = await fetch(`${API_BASE_URL}/auth/token/regenerate`, { method: 'POST' });
        const data = await response.json();
        if (response.ok) {
            const tokenInput = document.getElementById('apiTokenInput');
            if (tokenInput) tokenInput.value = data.api_token;
            showSuccess('API token regenerated successfully');
        } else {
            showError(data.error || 'Failed to regenerate token');
        }
    } catch (error) {
        showError(`Regenerate failed: ${error.message}`);
    }
}
