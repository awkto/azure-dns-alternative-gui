const API_BASE_URL = '/api';

async function checkAuth() {
    try {
        const response = await fetch(`${API_BASE_URL}/auth/status`);
        const data = await response.json();
        if (data.setup_required) { window.location.href = '/setup.html'; return false; }
        if (!data.authenticated) { window.location.href = '/login.html'; return false; }
        return true;
    } catch { window.location.href = '/login.html'; return false; }
}

const _originalFetch = window.fetch;
window.fetch = async function(...args) {
    const response = await _originalFetch.apply(this, args);
    if (response.status === 401) {
        const url = typeof args[0] === 'string' ? args[0] : args[0]?.url || '';
        if (!url.includes('/api/auth/')) window.location.href = '/login.html';
    }
    return response;
};

const successMessage = document.getElementById('successMessage');
const errorMessage = document.getElementById('errorMessage');

let isSetupMode = false;
let rawMode = false;

const ENV_KEY_MAP = {
    'AZURE_TENANT_ID': 'tenant_id', 'AZURE_CLIENT_ID': 'client_id',
    'AZURE_CLIENT_SECRET': 'client_secret', 'AZURE_SUBSCRIPTION_ID': 'subscription_id',
    'AZURE_RESOURCE_GROUP': 'resource_group', 'AZURE_DNS_ZONE': 'dns_zone',
};

function serializeToRaw() {
    return [
        `AZURE_TENANT_ID='${document.getElementById('tenantId').value}'`,
        `AZURE_CLIENT_ID='${document.getElementById('clientId').value}'`,
        `AZURE_CLIENT_SECRET='${document.getElementById('clientSecret').value}'`,
        `AZURE_SUBSCRIPTION_ID='${document.getElementById('subscriptionId').value}'`,
        `AZURE_RESOURCE_GROUP='${document.getElementById('resourceGroup').value}'`,
        `AZURE_DNS_ZONE='${document.getElementById('dnsZone').value}'`,
    ].join('\n');
}

function parseRaw(text) {
    text = (text || '').trim();
    if (!text) return {};
    if (text.startsWith('{')) {
        try {
            const obj = JSON.parse(text);
            const result = {};
            for (const [envKey, fieldKey] of Object.entries(ENV_KEY_MAP)) {
                if (obj[fieldKey] !== undefined) result[fieldKey] = obj[fieldKey];
                else if (obj[envKey] !== undefined) result[fieldKey] = obj[envKey];
            }
            return result;
        } catch {}
    }
    const result = {};
    for (const line of text.split('\n')) {
        const trimmed = line.trim();
        if (!trimmed || trimmed.startsWith('#')) continue;
        const eqIdx = trimmed.indexOf('=');
        if (eqIdx === -1) continue;
        const key = trimmed.slice(0, eqIdx).trim();
        let val = trimmed.slice(eqIdx + 1).trim();
        if ((val.startsWith("'") && val.endsWith("'")) || (val.startsWith('"') && val.endsWith('"'))) val = val.slice(1, -1);
        const fieldKey = ENV_KEY_MAP[key];
        if (fieldKey) result[fieldKey] = val;
    }
    return result;
}

function toggleRawMode() {
    const fields = document.getElementById('azureFormFields');
    const rawInput = document.getElementById('rawConfigInput');
    const btn = document.getElementById('toggleRawModeBtn');
    if (!rawMode) {
        rawInput.value = serializeToRaw();
        fields.style.display = 'none';
        rawInput.style.display = 'block';
        rawInput.focus();
        btn.innerHTML = '<svg fill="none" stroke="currentColor" viewBox="0 0 24 24" style="width:14px;height:14px;"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16"/></svg> Form';
        rawMode = true;
    } else {
        const parsed = parseRaw(rawInput.value);
        if (parsed.tenant_id !== undefined) document.getElementById('tenantId').value = parsed.tenant_id;
        if (parsed.client_id !== undefined) document.getElementById('clientId').value = parsed.client_id;
        if (parsed.client_secret !== undefined) document.getElementById('clientSecret').value = parsed.client_secret;
        if (parsed.subscription_id !== undefined) document.getElementById('subscriptionId').value = parsed.subscription_id;
        if (parsed.resource_group !== undefined) document.getElementById('resourceGroup').value = parsed.resource_group;
        if (parsed.dns_zone !== undefined) document.getElementById('dnsZone').value = parsed.dns_zone;
        rawInput.style.display = 'none';
        fields.style.display = 'block';
        btn.innerHTML = '<svg fill="none" stroke="currentColor" viewBox="0 0 24 24" style="width:14px;height:14px;"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4"/></svg> Raw';
        rawMode = false;
    }
}

document.addEventListener('DOMContentLoaded', async () => {
    if (localStorage.getItem('theme') === 'dark') document.body.classList.add('dark-mode');

    const isAuth = await checkAuth();
    if (!isAuth) return;

    document.querySelectorAll('.sidebar-item').forEach(btn => {
        btn.addEventListener('click', () => switchPanel(btn.dataset.panel));
    });

    const hash = location.hash.replace('#', '');
    if (hash && document.getElementById(`panel-${hash}`)) switchPanel(hash);

    loadCurrentConfig();
    loadApiToken();

    document.getElementById('saveConfigBtn').addEventListener('click', handleSaveConfig);
    document.getElementById('testConnectionBtn').addEventListener('click', handleTestConnection);
    document.getElementById('toggleRawModeBtn').addEventListener('click', toggleRawMode);
    document.getElementById('toggleTokenBtn').addEventListener('click', toggleApiTokenVisibility);
    document.getElementById('copyTokenBtn').addEventListener('click', copyApiToken);
    document.getElementById('regenerateTokenBtn').addEventListener('click', regenerateApiToken);
    document.getElementById('changePasswordBtn').addEventListener('click', handleChangePassword);
});

function switchPanel(panelId) {
    document.querySelectorAll('.settings-panel').forEach(p => p.classList.remove('active'));
    document.querySelectorAll('.sidebar-item').forEach(b => b.classList.remove('active'));
    const panel = document.getElementById(`panel-${panelId}`);
    const btn = document.querySelector(`.sidebar-item[data-panel="${panelId}"]`);
    if (panel) panel.classList.add('active');
    if (btn) btn.classList.add('active');
    location.hash = panelId;
    hideMessages();
}

async function loadCurrentConfig() {
    try {
        const response = await fetch(`${API_BASE_URL}/config`);
        const data = await response.json();
        if (response.ok) {
            const hasAnyConfig = data.tenant_id || data.client_id || data.subscription_id || data.resource_group || data.dns_zone;
            isSetupMode = !hasAnyConfig;
            if (isSetupMode) {
                const back = document.getElementById('backNavigation');
                if (back) back.style.display = 'none';
                const desc = document.getElementById('settingsDescription');
                if (desc) desc.textContent = 'Welcome! Configure your Azure credentials to get started.';
            }
            document.getElementById('tenantId').value = data.tenant_id || '';
            document.getElementById('clientId').value = data.client_id || '';
            document.getElementById('clientSecret').value = data.client_secret || '';
            document.getElementById('subscriptionId').value = data.subscription_id || '';
            document.getElementById('resourceGroup').value = data.resource_group || '';
            document.getElementById('dnsZone').value = data.dns_zone || '';
            if (data.has_secret) document.getElementById('clientSecret').required = false;
        }
    } catch (e) { showError(`Failed to load configuration: ${e.message}`); }
}

function getFormData() {
    if (rawMode) {
        const parsed = parseRaw(document.getElementById('rawConfigInput').value);
        return {
            tenant_id: (parsed.tenant_id || '').trim(), client_id: (parsed.client_id || '').trim(),
            client_secret: (parsed.client_secret || '').trim(), subscription_id: (parsed.subscription_id || '').trim(),
            resource_group: (parsed.resource_group || '').trim(), dns_zone: (parsed.dns_zone || '').trim(),
        };
    }
    return {
        tenant_id: document.getElementById('tenantId').value.trim(),
        client_id: document.getElementById('clientId').value.trim(),
        client_secret: document.getElementById('clientSecret').value.trim(),
        subscription_id: document.getElementById('subscriptionId').value.trim(),
        resource_group: document.getElementById('resourceGroup').value.trim(),
        dns_zone: document.getElementById('dnsZone').value.trim(),
    };
}

function validateConfig(config) {
    return config.tenant_id && config.client_id && config.client_secret && config.subscription_id && config.resource_group && config.dns_zone;
}

async function handleTestConnection() {
    const btn = document.getElementById('testConnectionBtn');
    try {
        hideMessages(); btn.disabled = true; btn.textContent = 'Testing...';
        const config = getFormData();
        if (!validateConfig(config)) { showError('Please fill in all required fields'); return; }
        const res = await fetch(`${API_BASE_URL}/config/test`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(config) });
        const data = await res.json();
        if (res.ok) showSuccess(data.message || 'Connection successful!');
        else showError(data.error || 'Connection test failed');
    } catch (e) { showError(`Test failed: ${e.message}`); }
    finally { btn.disabled = false; btn.textContent = 'Test Connection'; }
}

async function handleSaveConfig() {
    try {
        hideMessages();
        const config = getFormData();
        if (!validateConfig(config)) { showError('Please fill in all required fields'); return; }
        const res = await fetch(`${API_BASE_URL}/config`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(config) });
        const data = await res.json();
        if (res.ok) {
            showSuccess(`Configuration saved! DNS Zone: ${data.zone}`);
            setTimeout(() => { window.location.href = '/'; }, 2000);
        } else showError(data.error || 'Failed to save configuration');
    } catch (e) { showError(`Save failed: ${e.message}`); }
}

async function loadApiToken() {
    try {
        const res = await fetch(`${API_BASE_URL}/auth/token`);
        if (!res.ok) return;
        const data = await res.json();
        document.getElementById('apiTokenInput').value = data.api_token;
    } catch {}
}

function toggleApiTokenVisibility() {
    const input = document.getElementById('apiTokenInput');
    const btn = document.getElementById('toggleTokenBtn');
    if (input.type === 'password') { input.type = 'text'; btn.textContent = 'Hide'; }
    else { input.type = 'password'; btn.textContent = 'Show'; }
}

async function copyApiToken() {
    const input = document.getElementById('apiTokenInput');
    if (!input.value) return;
    try {
        await navigator.clipboard.writeText(input.value);
        const btn = document.getElementById('copyTokenBtn');
        btn.textContent = 'Copied!';
        setTimeout(() => { btn.textContent = 'Copy'; }, 2000);
    } catch { showError('Could not copy to clipboard'); }
}

async function regenerateApiToken() {
    if (!confirm('Regenerate? Existing scripts using the old token will stop working.')) return;
    try {
        const res = await fetch(`${API_BASE_URL}/auth/token/regenerate`, { method: 'POST' });
        const data = await res.json();
        if (res.ok) {
            document.getElementById('apiTokenInput').value = data.api_token;
            document.getElementById('apiTokenInput').type = 'password';
            document.getElementById('toggleTokenBtn').textContent = 'Show';
            showSuccess('API token regenerated.');
        } else showError(data.error || 'Failed to regenerate token');
    } catch { showError('Failed to regenerate API token'); }
}

async function handleChangePassword() {
    const current = document.getElementById('currentPassword').value;
    const newPw = document.getElementById('newPassword').value;
    const confirmPw = document.getElementById('confirmPassword').value;
    hideMessages();
    if (!current || !newPw || !confirmPw) { showError('Fill in all password fields'); return; }
    if (newPw !== confirmPw) { showError('New passwords do not match'); return; }
    if (newPw.length < 8) { showError('New password must be at least 8 characters'); return; }
    try {
        const res = await fetch(`${API_BASE_URL}/auth/change-password`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ current_password: current, new_password: newPw }) });
        const data = await res.json();
        if (res.ok) {
            showSuccess('Password changed successfully');
            document.getElementById('currentPassword').value = '';
            document.getElementById('newPassword').value = '';
            document.getElementById('confirmPassword').value = '';
        } else showError(data.error || 'Failed to change password');
    } catch (e) { showError(`Failed: ${e.message}`); }
}

function showSuccess(msg) {
    successMessage.textContent = msg; successMessage.style.display = 'block';
    errorMessage.style.display = 'none';
    setTimeout(() => { successMessage.style.display = 'none'; }, 5000);
}
function showError(msg) {
    errorMessage.textContent = msg; errorMessage.style.display = 'block';
    successMessage.style.display = 'none';
}
function hideMessages() {
    successMessage.style.display = 'none';
    errorMessage.style.display = 'none';
}
