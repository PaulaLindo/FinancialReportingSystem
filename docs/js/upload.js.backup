// Upload Page JavaScript - SADPMR Financial Reporting System

let uploadedFilePath = null;
let resultsFile = null;

// DOM Elements
const uploadBox = document.getElementById('uploadBox');
const fileInput = document.getElementById('fileInput');
const fileInfo = document.getElementById('fileInfo');
const fileName = document.getElementById('fileName');
const fileSize = document.getElementById('fileSize');
const fileRows = document.getElementById('fileRows');
const processBtn = document.getElementById('processBtn');
const processingLoader = document.getElementById('processingLoader');
const errorMessage = document.getElementById('errorMessage');
const resultsSection = document.getElementById('resultsSection');

// Click to browse
uploadBox.addEventListener('click', () => {
    fileInput.click();
});

// Drag and drop
uploadBox.addEventListener('dragover', (e) => {
    e.preventDefault();
    uploadBox.style.borderColor = '#3f51b5';
    uploadBox.style.background = '#f0f4ff';
});

uploadBox.addEventListener('dragleave', () => {
    uploadBox.style.borderColor = '#e0e0e0';
    uploadBox.style.background = '';
});

uploadBox.addEventListener('drop', (e) => {
    e.preventDefault();
    uploadBox.style.borderColor = '#e0e0e0';
    uploadBox.style.background = '';
    
    const file = e.dataTransfer.files[0];
    if (file) {
        handleFile(file);
    }
});

// File input change
fileInput.addEventListener('change', (e) => {
    const file = e.target.files[0];
    if (file) {
        handleFile(file);
    }
});

// Handle file upload
function handleFile(file) {
    // Hide previous results
    resultsSection.style.display = 'none';
    errorMessage.style.display = 'none';
    
    // Validate file type
    const validTypes = ['application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', 
                       'application/vnd.ms-excel', 
                       'text/csv'];
    
    if (!validTypes.includes(file.type) && !file.name.match(/\.(xlsx|xls|csv)$/i)) {
        showError('Invalid file type. Please upload Excel (.xlsx, .xls) or CSV file.');
        return;
    }
    
    // Validate file size (16MB max)
    if (file.size > 16 * 1024 * 1024) {
        showError('File too large. Maximum size is 16MB.');
        return;
    }
    
    // Upload file
    uploadFile(file);
}

// Upload file to server
function uploadFile(file) {
    const formData = new FormData();
    formData.append('file', file);
    
    uploadBox.style.display = 'none';
    processingLoader.style.display = 'block';
    processingLoader.querySelector('p').textContent = 'Uploading file...';
    
    fetch('/api/upload', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        processingLoader.style.display = 'none';
        
        if (data.success) {
            // Show file info
            fileName.textContent = file.name;
            fileSize.textContent = `Size: ${(file.size / 1024).toFixed(2)} KB`;
            fileRows.textContent = `Accounts: ${data.row_count}`;
            
            uploadedFilePath = data.filepath;
            
            fileInfo.style.display = 'block';
        } else {
            showError(data.error);
            uploadBox.style.display = 'block';
        }
    })
    .catch(error => {
        processingLoader.style.display = 'none';
        uploadBox.style.display = 'block';
        showError('Upload failed: ' + error.message);
    });
}

// Process Trial Balance
processBtn.addEventListener('click', () => {
    if (!uploadedFilePath) {
        showError('No file uploaded');
        return;
    }
    
    fileInfo.style.display = 'none';
    processingLoader.style.display = 'block';
    processingLoader.querySelector('p').textContent = 'Processing your Trial Balance...';
    processingLoader.querySelector('.loader-subtext').textContent = 'Mapping accounts to GRAP line items';
    errorMessage.style.display = 'none';
    
    fetch('/api/process', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            filepath: uploadedFilePath
        })
    })
    .then(response => response.json())
    .then(data => {
        processingLoader.style.display = 'none';
        
        if (data.success) {
            // Store results file
            resultsFile = data.results_file;
            
            // Display results
            displayResults(data.summary);
        } else {
            if (data.unmapped_accounts) {
                showError('Unmapped accounts detected. Please review the mapping configuration.');
                console.error('Unmapped accounts:', data.unmapped_accounts);
            } else {
                showError(data.error);
            }
            fileInfo.style.display = 'block';
        }
    })
    .catch(error => {
        processingLoader.style.display = 'none';
        fileInfo.style.display = 'block';
        showError('Processing failed: ' + error.message);
    });
});

// Display results
function displayResults(summary) {
    // Update summary cards
    document.getElementById('totalAssets').textContent = formatCurrency(summary.total_assets);
    document.getElementById('totalLiabilities').textContent = formatCurrency(summary.total_liabilities);
    document.getElementById('netAssets').textContent = formatCurrency(summary.net_assets);
    document.getElementById('surplus').textContent = formatCurrency(summary.surplus_deficit);
    
    // Update ratios
    document.getElementById('currentRatio').textContent = summary.ratios.current_ratio.toFixed(2);
    document.getElementById('debtToEquity').textContent = summary.ratios.debt_to_equity.toFixed(2);
    document.getElementById('operatingMargin').textContent = summary.ratios.operating_margin.toFixed(2) + '%';
    document.getElementById('returnOnAssets').textContent = summary.ratios.return_on_assets.toFixed(2) + '%';
    
    // Show results section
    resultsSection.style.display = 'block';
    
    // Scroll to results
    resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

// Generate PDF
document.getElementById('generatePdfBtn').addEventListener('click', () => {
    if (!resultsFile) {
        showError('No results available');
        return;
    }
    
    const pdfLoader = document.getElementById('pdfLoader');
    const pdfSuccess = document.getElementById('pdfSuccess');
    
    pdfLoader.style.display = 'block';
    pdfSuccess.style.display = 'none';
    
    fetch('/api/generate-pdf', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            results_file: resultsFile
        })
    })
    .then(response => response.json())
    .then(data => {
        pdfLoader.style.display = 'none';
        
        if (data.success) {
            // Update download link
            const downloadLink = document.getElementById('downloadLink');
            downloadLink.href = data.download_url;
            downloadLink.download = data.pdf_filename;
            
            pdfSuccess.style.display = 'block';
        } else {
            showError('PDF generation failed: ' + data.error);
        }
    })
    .catch(error => {
        pdfLoader.style.display = 'none';
        showError('PDF generation failed: ' + error.message);
    });
});

// Upload another button
document.getElementById('uploadAnotherBtn').addEventListener('click', () => {
    // Reset everything
    uploadedFilePath = null;
    resultsFile = null;
    
    uploadBox.style.display = 'block';
    fileInfo.style.display = 'none';
    resultsSection.style.display = 'none';
    errorMessage.style.display = 'none';
    
    fileInput.value = '';
    
    // Scroll to top
    window.scrollTo({ top: 0, behavior: 'smooth' });
});

// Helper functions
function formatCurrency(amount) {
    const sign = amount >= 0 ? '' : '-';
    const abs = Math.abs(amount);
    return sign + 'R ' + abs.toLocaleString('en-ZA', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function showError(message) {
    errorMessage.textContent = '❌ ' + message;
    errorMessage.style.display = 'block';
    
    // Scroll to error
    errorMessage.scrollIntoView({ behavior: 'smooth', block: 'center' });
}
