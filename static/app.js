const API_BASE_URL = 'http://localhost:5000/api';

// DOM Elements
const zoneName = document.getElementById('zoneName');
const recordsTableBody = document.getElementById('recordsTableBody');
const loadingIndicator = document.getElementById('loadingIndicator');
const errorMessage = document.getElementById('errorMessage');
const addRecordForm = document.getElementById('addRecordForm');
const refreshBtn = document.getElementById('refreshBtn');
const editModal = document.getElementById('editModal');
const editRecordForm = document.getElementById('editRecordForm');
const closeModal = document.querySelector('.close');
const cancelEditBtn = document.getElementById('cancelEditBtn');

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    loadRecords();
    
    // Event listeners
    addRecordForm.addEventListener('submit', handleAddRecord);
    editRecordForm.addEventListener('submit', handleEditRecord);
    refreshBtn.addEventListener('click', loadRecords);
    closeModal.addEventListener('click', hideEditModal);
    cancelEditBtn.addEventListener('click', hideEditModal);
    
    // Close modal when clicking outside
    window.addEventListener('click', (e) => {
        if (e.target === editModal) {
            hideEditModal();
        }
    });
});

// Load all DNS records
async function loadRecords() {
    try {
        showLoading(true);
        hideError();
        
        const response = await fetch(`${API_BASE_URL}/records`);
        const data = await response.json();
        
        if (!response.ok) {
            console.error('Error response:', data);
            throw new Error(data.error || `HTTP error! status: ${response.status}`);
        }
        
        zoneName.textContent = data.zone;
        displayRecords(data.records);
        
        showLoading(false);
    } catch (error) {
        console.error('Failed to load records:', error);
        showError(`Failed to load records: ${error.message}`);
        showLoading(false);
    }
}

// Display records in table
function displayRecords(records) {
    recordsTableBody.innerHTML = '';
    
    if (records.length === 0) {
        recordsTableBody.innerHTML = '<tr><td colspan="5" style="text-align: center;">No records found</td></tr>';
        return;
    }
    
    records.forEach(record => {
        const row = document.createElement('tr');
        
        // Format values
        const valuesHtml = record.values.map(val => `<div class="value-item">${escapeHtml(val)}</div>`).join('');
        
        row.innerHTML = `
            <td><strong>${escapeHtml(record.name)}</strong><br><small>${escapeHtml(record.fqdn)}</small></td>
            <td><span class="badge badge-${record.type.toLowerCase()}">${escapeHtml(record.type)}</span></td>
            <td>${record.ttl}s</td>
            <td class="values-cell">${valuesHtml}</td>
            <td class="actions-cell">
                <button class="btn btn-small btn-primary" onclick="editRecord('${escapeHtml(record.name)}', '${escapeHtml(record.type)}', ${record.ttl}, ${JSON.stringify(record.values).replace(/"/g, '&quot;')})">
                    ✏️ Edit
                </button>
                <button class="btn btn-small btn-danger" onclick="deleteRecord('${escapeHtml(record.name)}', '${escapeHtml(record.type)}')">
                    🗑️ Delete
                </button>
            </td>
        `;
        
        recordsTableBody.appendChild(row);
    });
}

// Add new record
async function handleAddRecord(e) {
    e.preventDefault();
    
    const name = document.getElementById('recordName').value.trim();
    const type = document.getElementById('recordType').value;
    const ttl = parseInt(document.getElementById('recordTTL').value);
    const valuesText = document.getElementById('recordValues').value.trim();
    
    // Parse values (one per line)
    const values = valuesText.split('\n').map(v => v.trim()).filter(v => v.length > 0);
    
    if (values.length === 0) {
        showError('Please enter at least one value');
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE_URL}/records`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ name, type, ttl, values }),
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || 'Failed to create record');
        }
        
        showSuccess('Record created successfully!');
        addRecordForm.reset();
        loadRecords();
    } catch (error) {
        showError(`Failed to create record: ${error.message}`);
    }
}

// Edit record - show modal
function editRecord(name, type, ttl, values) {
    document.getElementById('editRecordName').value = name;
    document.getElementById('editRecordType').value = type;
    document.getElementById('editRecordNameDisplay').value = name;
    document.getElementById('editRecordTypeDisplay').value = type;
    document.getElementById('editRecordTTL').value = ttl;
    document.getElementById('editRecordValues').value = values.join('\n');
    
    editModal.style.display = 'block';
}

// Handle edit form submission
async function handleEditRecord(e) {
    e.preventDefault();
    
    const name = document.getElementById('editRecordName').value;
    const type = document.getElementById('editRecordType').value;
    const ttl = parseInt(document.getElementById('editRecordTTL').value);
    const valuesText = document.getElementById('editRecordValues').value.trim();
    
    const values = valuesText.split('\n').map(v => v.trim()).filter(v => v.length > 0);
    
    if (values.length === 0) {
        showError('Please enter at least one value');
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE_URL}/records/${type}/${name}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ ttl, values }),
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || 'Failed to update record');
        }
        
        showSuccess('Record updated successfully!');
        hideEditModal();
        loadRecords();
    } catch (error) {
        showError(`Failed to update record: ${error.message}`);
    }
}

// Delete record
async function deleteRecord(name, type) {
    if (!confirm(`Are you sure you want to delete the ${type} record "${name}"?`)) {
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE_URL}/records/${type}/${name}`, {
            method: 'DELETE',
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || 'Failed to delete record');
        }
        
        showSuccess('Record deleted successfully!');
        loadRecords();
    } catch (error) {
        showError(`Failed to delete record: ${error.message}`);
    }
}

// Modal functions
function hideEditModal() {
    editModal.style.display = 'none';
}

// UI Helper functions
function showLoading(show) {
    loadingIndicator.style.display = show ? 'block' : 'none';
}

function showError(message) {
    errorMessage.textContent = message;
    errorMessage.style.display = 'block';
    setTimeout(() => {
        errorMessage.style.display = 'none';
    }, 5000);
}

function hideError() {
    errorMessage.style.display = 'none';
}

function showSuccess(message) {
    // Create temporary success message
    const successDiv = document.createElement('div');
    successDiv.className = 'success';
    successDiv.textContent = message;
    document.querySelector('.container').insertBefore(successDiv, document.querySelector('.main-content'));
    
    setTimeout(() => {
        successDiv.remove();
    }, 3000);
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
