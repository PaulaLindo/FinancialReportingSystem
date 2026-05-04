/**



 * Varydian Financial Reporting System - Upload Functionality



 * Refactored upload service with better error handling and state management



 */







class UploadService {



    constructor() {



        this.state = {



            uploadedFilePath: null,



            resultsFile: null,



            isProcessing: false,



            currentStep: null,



            sessionId: null



        };



        



        this.elements = {};



        this.boundMethods = {};



        this.init();



    }







    /**



     * Initialize upload service



     */



    init() {



        this.cacheElements();



        this.validateElements();



        this.bindMethods();



        this.setupEventListeners();



        this.initializeUI();



    }







    /**



     * Cache DOM elements



     */



    cacheElements() {



        this.elements = {



            uploadBox: document.getElementById('uploadBox'),



            fileInput: document.getElementById('fileInput'),



            fileInfo: document.getElementById('fileInfo'),



            fileName: document.getElementById('fileName'),



            fileSize: document.getElementById('fileSize'),



            fileRows: document.getElementById('fileRows'),



            processBtn: document.getElementById('processBtn'),

            closeBtn: document.getElementById('closeBtn'),



            processingLoader: document.getElementById('processingLoader'),



            errorMessage: document.getElementById('errorMessage'),



            resultsSection: document.getElementById('resultsSection'),



            generatePdfBtn: document.getElementById('generatePdfBtn'),



            removeFileBtn: document.getElementById('removeFileBtn'),



            uploadAnotherBtn: document.getElementById('uploadAnotherBtn'),



            pdfLoader: document.getElementById('pdfLoader'),



            pdfSuccess: document.getElementById('pdfSuccess'),



            downloadLink: document.getElementById('downloadLink'),



            // Balance check elements

            balanceCheckSection: document.getElementById('balanceCheckSection'),

            balanceIndicator: document.getElementById('balanceIndicator'),

            balanceHeader: document.querySelector('.balance-header h4'),

            totalDebits: document.getElementById('totalDebits'),

            totalCredits: document.getElementById('totalCredits'),

            balanceDifference: document.getElementById('balanceDifference'),

            balanceStatus: document.getElementById('balanceStatus'),

            balanceMessage: document.getElementById('balanceMessage'),

            statusIcon: document.querySelector('.status-icon'),

            statusText: document.querySelector('.status-text'),



            // Modal elements

            confirmModal: document.getElementById('confirmModal'),

            confirmCancel: document.getElementById('confirmCancel'),

            confirmRemove: document.getElementById('confirmRemove')



        };



        

        // Log missing elements for debugging



        const missingElements = Object.keys(this.elements)



            .filter(key => !this.elements[key])



            .map(key => key);



            



        if (missingElements.length > 0) {

            // Missing elements logged for debugging

        }



    }







    /**



     * Validate required elements



     */



    validateElements() {



        const required = ['uploadBox', 'fileInput', 'processBtn'];



        const missing = required.filter(id => !this.elements[id]);



        



        if (missing.length > 0) {

            return false;

        }



        return true;



    }







    /**



     * Bind methods to maintain context



     */



    bindMethods() {



        this.boundMethods = {



            handleFile: this.handleFile.bind(this),



            handleDragOver: this.handleDragOver.bind(this),



            handleDragLeave: this.handleDragLeave.bind(this),



            handleDrop: this.handleDrop.bind(this),



            handleFileInput: this.handleFileInput.bind(this),



            processFileWithBalanceCheck: this.processFileWithBalanceCheck.bind(this),



            closeUpload: this.closeUpload.bind(this),



            generatePDF: this.generatePDF.bind(this),



            uploadAnother: this.uploadAnother.bind(this)



        };



    }







    /**



     * Setup event listeners



     */



    setupEventListeners() {



        const { uploadBox, fileInput, processBtn, generatePdfBtn, uploadAnotherBtn } = this.elements;



        



        // Upload box events



        uploadBox.addEventListener('click', () => {

            if (typeof debugLog === 'function') {

                debugLog('🖱️ Upload box clicked', 'info');

                

                // Check upload box state

                const computedStyle = window.getComputedStyle(uploadBox);

                const pointerEvents = computedStyle.pointerEvents;

                const opacity = computedStyle.opacity;

                const disabled = uploadBox.classList.contains('upload-disabled') || pointerEvents === 'none';

                

                debugLog(`🔍 Upload box state: pointer-events=${pointerEvents}, opacity=${opacity}, disabled=${disabled}`, disabled ? 'warning' : 'info');

                

                if (disabled) {

                    debugLog('🚫 Upload box is disabled - file input will not trigger', 'error');

                    return; // Don't trigger file input if disabled

                }

            }

            fileInput.click();

        });



        uploadBox.addEventListener('dragover', this.boundMethods.handleDragOver);



        uploadBox.addEventListener('dragleave', this.boundMethods.handleDragLeave);



        uploadBox.addEventListener('drop', this.boundMethods.handleDrop);



        



        // File input events



        fileInput.addEventListener('change', this.boundMethods.handleFileInput);



        



        // Button events



        processBtn.addEventListener('click', (e) => {

            this.boundMethods.processFileWithBalanceCheck(e);

        });



        if (closeBtn) {

            closeBtn.addEventListener('click', (e) => {

                this.boundMethods.closeUpload(e);

            });

        }



        if (generatePdfBtn) {

            

            generatePdfBtn.addEventListener('click', (e) => {

                e.preventDefault();

                e.stopPropagation();

                this.generatePDF();



            });



        }



        if (this.elements.removeFileBtn) {



            this.elements.removeFileBtn.addEventListener('click', (e) => {



                

                e.preventDefault();



                e.stopPropagation();



                this.removeUploadedFile();



            });



        }



        if (uploadAnotherBtn) {



            uploadAnotherBtn.addEventListener('click', this.boundMethods.uploadAnother);



        }



        



        // Modal event listeners



        if (this.elements.confirmCancel) {



            this.elements.confirmCancel.addEventListener('click', () => {



                this.hideConfirmModal();



            });



        }



        



        if (this.elements.confirmModal) {



            this.elements.confirmModal.addEventListener('click', (e) => {



                if (e.target === this.elements.confirmModal) {



                    this.hideConfirmModal();



                }



            });



        }



        



        if (this.elements.confirmRemove) {



            this.elements.confirmRemove.addEventListener('click', () => {



                this.executeFileRemoval();



            });



        }



    }







    /**



     * Initialize UI state



     */



    initializeUI() {



        this.hideError();



        this.hideResults();



        this.hideFileInfo();



        this.setProcessingState(false);



    }







    /**



     * Handle drag over event



     */



    handleDragOver(event) {



        event.preventDefault();



        if (typeof debugLog === 'function') {

            debugLog('🎯 Drag over event detected', 'info');

        }



        // Check if upload box is disabled

        const computedStyle = window.getComputedStyle(this.elements.uploadBox);

        const disabled = this.elements.uploadBox.classList.contains('upload-disabled') || computedStyle.pointerEvents === 'none';

        

        if (disabled && typeof debugLog === 'function') {

            debugLog('🚫 Drag over blocked - upload box is disabled', 'warning');

            return;

        }



        if (this.elements.uploadBox) {

            this.elements.uploadBox.classList.add('upload-zone--hover');

        }



        if (this.elements.uploadBox) {

            this.elements.uploadBox.classList.remove('upload-zone--idle', 'upload-zone--active');

        }



    }







    /**



     * Handle drag leave event



     */



    handleDragLeave(event) {



        event.preventDefault();



        if (this.elements.uploadBox) {

            this.elements.uploadBox.classList.add('upload-zone--idle');

        }



        if (this.elements.uploadBox) {

            this.elements.uploadBox.classList.remove('upload-zone--hover', 'upload-zone--active');

        }



    }







    /**



     * Handle drop event



     */



    handleDrop(event) {



        event.preventDefault();



        if (typeof debugLog === 'function') {

            debugLog('📂 Drop event detected', 'info');

        }



        // Check if upload box is disabled

        const computedStyle = window.getComputedStyle(this.elements.uploadBox);

        const disabled = this.elements.uploadBox.classList.contains('upload-disabled') || computedStyle.pointerEvents === 'none';

        

        if (disabled && typeof debugLog === 'function') {

            debugLog('🚫 Drop blocked - upload box is disabled', 'warning');

            return;

        }



        if (this.elements.uploadBox) {

            this.elements.uploadBox.classList.add('upload-zone--idle');

        }



        if (this.elements.uploadBox) {

            this.elements.uploadBox.classList.remove('upload-zone--hover', 'upload-zone--active');

        }



        



        const file = event.dataTransfer.files[0];



        if (typeof debugLog === 'function') {

            debugLog(`📄 File dropped: ${file ? file.name : 'None'}`, 'info');

        }



        if (file) {



            this.handleFile(file);



        } else {



            if (typeof debugLog === 'function') {

                debugLog('⚠️ No file in drop event', 'warning');

            }



        }



    }







    /**



     * Handle file input change



     */



    handleFileInput(event) {



        const file = event.target.files[0];



        if (typeof debugLog === 'function') {

            debugLog(`📁 File input triggered. File selected: ${file ? file.name : 'None'}`, 'info');

        }



        if (file) {



            if (typeof debugLog === 'function') {

                debugLog(`📄 Processing file: ${file.name} (${(file.size / 1024 / 1024).toFixed(2)} MB)`, 'info');

            }



            this.handleFile(file);



        } else {



            if (typeof debugLog === 'function') {

                debugLog('⚠️ No file selected in file input', 'warning');

            }



        }



    }







    /**



     * Handle file processing



     */



    async handleFile(file) {



        try {



            if (typeof debugLog === 'function') {

                debugLog(`🔄 Starting file processing for: ${file.name}`, 'info');

            }



            this.hideResults();



            this.hideError();



            



            // Validate file



            const validation = VarydianUtils.validateFile(file);



            if (typeof debugLog === 'function') {

                debugLog(`🔍 File validation result: ${validation.valid ? 'VALID' : 'INVALID'}`, validation.valid ? 'success' : 'error');

                if (!validation.valid) {

                    debugLog(`❌ Validation error: ${validation.error}`, 'error');

                }

            }



            if (!validation.valid) {



                this.showError(validation.error);



                return;



            }



            // Client-side file type validation

            const allowedExtensions = ['xlsx', 'xls', 'csv', 'xlsm', 'xlsb', 'tsv'];

            const fileExtension = file.name.split('.').pop().toLowerCase();

            

            if (!allowedExtensions.includes(fileExtension)) {

                const errorMessage = '❌ Invalid file type: .' + fileExtension + '\n\n' +

                                '📋 **Allowed file types**: .xlsx, .xls, .csv, .xlsm, .xlsb, .tsv\n' +

                                '💡 **Solution**: Please upload a balance sheet file in one of the supported formats\n\n' +

                                '📊 **Common formats**:\n' +

                                '• Excel files (.xlsx, .xls) - Recommended\n' +

                                '• CSV files (.csv) - Universal format\n' +

                                '• Other Excel formats (.xlsm, .xlsb, .tsv) - Also supported';

                

                this.showError(errorMessage);

                return;

            }



            // Upload file

            await this.uploadFile(file);



            



        } catch (error) {



            // Don't show error message here - let uploadFile handle user-friendly messages

            // Error is properly logged in uploadFile method



        }



    }







    /**



     * Upload file to server



     */



    async uploadFile(file) {



        this.setProcessingState(true, 'Uploading file...');



        



        const formData = new FormData();



        formData.append('file', file);



        // Get selected document type

        const documentType = window.documentTypeSelector ? window.documentTypeSelector.getSelectedType() : 'balance_sheet';

        console.log('🔍 Detected document type:', documentType);

        console.log('🔍 Document type selector available:', !!window.documentTypeSelector);

        formData.append('document_type', documentType);



        try {



            const data = await VarydianUtils.safeFetch('/api/universal/upload', {



                method: 'POST',



                body: formData



            });



            



            if (data.success) {



                this.showFileInfo(file, data);



                // Store file path for local files or record ID for Supabase files



                this.state.uploadedFilePath = data.filepath || data.storage_path;



                this.state.uploadedFileRecordId = data.record_id || null;



                // File uploaded successfully



                // Add delay to ensure database transaction is complete
                await new Promise(resolve => setTimeout(resolve, 2000));

                // Process all document types through balance checking first
                const documentType = window.documentTypeSelector ? window.documentTypeSelector.getSelectedType() : 'balance_sheet';
                await this.performBalanceCheck();



            } else {

                throw new Error(data.error || 'Upload failed');



            }



            



        } catch (error) {



            // Provide more user-friendly error messages for upload

            let errorMessage = error.message || 'Upload failed';

            

            // Handle specific error messages from our enhanced backend

            if (errorMessage.includes('HTTP error! status: 500')) {

                errorMessage = '❌ Server error during upload. Please try again or contact support if the problem persists.';

            } else if (errorMessage.includes('HTTP error! status: 400')) {

                // Try to extract the actual error message from the response

                try {

                    const errorData = JSON.parse(errorMessage.split('HTTP error! status: 400 - ')[1]);

                    const backendError = errorData.error;

                    

                    // Handle specific backend error messages

                    if (backendError.includes('financial analysis, not a balance sheet')) {

                        errorMessage = '📊 This appears to be a financial analysis template, not a balance sheet.\n\n' +

                                        '❌ **Required**: Balance sheet with Account Code, Account Description, and Balance columns\n' +

                                        '📋 **Current**: Financial analysis with benefits, costs, cash flow data\n\n' +

                                        '💡 **Solution**: Please export a balance sheet from your accounting system (Pastel, SAP, QuickBooks, etc.)';

                    } else if (backendError.includes('Missing required columns:')) {

                        const missingCols = backendError.match(/Missing required columns: ([^,]+)\./);

                        if (missingCols) {

                            errorMessage = '❌ Missing required columns in your file.\n\n' +

                                        '❌ **Missing**: ' + missingCols[1] + '\n' +

                                        '📋 **Required**: Account Code, Account Description\n' +

                                        '💡 **Solution**: Ensure your balance sheet has these exact column names';

                        } else {

                            // Fallback for any missing columns error

                            errorMessage = '❌ Missing required columns in your file.\n\n' +

                                        '📋 **Required**: Account Code, Account Description\n' +

                                        '💡 **Solution**: Ensure your balance sheet has these exact column names (case-sensitive)';

                        }

                    } else if (backendError.includes('Missing balance columns')) {

                        errorMessage = '❌ Missing balance columns in your balance sheet.\n\n' +

                                        '❌ **Required**: Debit Balance and Credit Balance columns (or Net Balance)\n' +

                                        '📋 **Current**: File has no balance data\n' +

                                        '💡 **Solution**: Add balance columns or use Net Balance column instead';

                    } else if (backendError.includes('Invalid Excel file format')) {

                        errorMessage = '❌ Unable to read the Excel file.\n\n' +

                                        '📋 **Issue**: File may be corrupted or saved in an incompatible format\n' +

                                        '💡 **Solution**: Try saving the file as a new Excel file or export as CSV';

                    } else if (backendError.includes('Invalid CSV file format')) {

                        errorMessage = '❌ Unable to read the CSV file.\n\n' +

                                        '📋 **Issue**: File encoding problem or format issues\n' +

                                        '💡 **Solution**: Save the CSV as UTF-8 encoding or try a different file format';

                    } else if (backendError.includes('file is empty')) {

                        errorMessage = '❌ The uploaded file is empty.\n\n' +

                                        '📋 **Issue**: No data found in the file\n' +

                                        '💡 **Solution**: Ensure your balance sheet contains account data';

                    } else if (backendError.includes('Invalid file type:')) {

                        // Extract the file type from the error message

                        const fileTypeMatch = backendError.match(/Invalid file type: \.([^\s]+)/);

                        const invalidType = fileTypeMatch ? fileTypeMatch[1] : 'unknown';

                        

                        errorMessage = '❌ Invalid file type: .' + invalidType + '\n\n' +

                                        '📋 **Allowed file types**: .xlsx, .xls, .csv, .xlsm, .xlsb, .tsv\n' +

                                        '💡 **Solution**: Please upload a balance sheet file in one of the supported formats\n\n' +

                                        '📊 **Common formats**:\n' +

                                        '• Excel files (.xlsx, .xls) - Recommended\n' +

                                        '• CSV files (.csv) - Universal format\n' +

                                        '• Other Excel formats (.xlsm, .xlsb, .tsv) - Also supported';

                    } else {

                        errorMessage = '❌ Invalid file format. Please check your file and try again.';

                    }

                } catch (parseError) {

                    // If JSON parsing fails, try to extract the error message directly

                    if (errorMessage.includes('Missing required columns:')) {

                        errorMessage = '❌ Missing required columns in your file.\n\n' +

                                    '📋 **Required**: Account Code, Account Description\n' +

                                    '💡 **Solution**: Ensure your balance sheet has these exact column names (case-sensitive)';

                    } else if (errorMessage.includes('Missing balance columns')) {

                        errorMessage = '❌ Missing balance columns in your balance sheet.\n\n' +

                                    '📋 **Required**: Debit Balance and Credit Balance columns (or Net Balance)\n' +

                                    '💡 **Solution**: Add balance columns or use Net Balance column instead';

                    } else if (errorMessage.includes('Invalid file type:')) {

                        // Handle file type errors when JSON parsing fails

                        const fileTypeMatch = errorMessage.match(/Invalid file type: \.([^\s]+)/);

                        const invalidType = fileTypeMatch ? fileTypeMatch[1] : 'unknown';

                        

                        errorMessage = '❌ Invalid file type: .' + invalidType + '\n\n' +

                                    '📋 **Allowed file types**: .xlsx, .xls, .csv, .xlsm, .xlsb, .tsv\n' +

                                    '💡 **Solution**: Please upload a balance sheet file in one of the supported formats';

                    } else {

                        errorMessage = '❌ Invalid file upload. Please check your file format and try again.';

                    }

                }

            } else if (errorMessage.includes('HTTP error! status: 413')) {

                errorMessage = '❌ File too large. Please upload a smaller file (maximum 16MB).';

            } else if (errorMessage.includes('Failed to fetch')) {

                errorMessage = '❌ Network error during upload. Please check your internet connection and try again.';

            }



            // Log technical error for debugging (only in development)

            if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {

                // Technical details logged in development mode

            }



            this.showError(errorMessage);



            throw error;



        } finally {



            this.setProcessingState(false);



        }



    }







    /**



     * Show file information



     */



    showFileInfo(file, data) {



        const { fileName, fileSize, fileRows, fileInfo, uploadBox, processBtn } = this.elements;



        console.log('🔍 showFileInfo called:', { file: file.name, data: data });

        console.log('🔍 uploadBox before:', uploadBox ? uploadBox.className : 'not found');

        console.log('🔍 fileInfo before:', fileInfo ? fileInfo.className : 'not found');



        



        fileName.textContent = file.name;



        fileSize.textContent = `Size: ${VarydianUtils.formatFileSize(file.size)}`;



        fileRows.textContent = `Accounts: ${data.total_rows || data.row_count || 'undefined'}`;



        



        // Hide upload box and show file info using centralized visibility management

        this.manageUploadBoxVisibility(false);



        // Only show file info if there's actual data

        if (fileInfo && file.name && (data.total_rows || data.row_count)) {

            console.log('🔍 Adding file-info--visible, removing file-info--hidden');

            fileInfo.classList.add('file-info--visible');

            fileInfo.classList.remove('file-info--hidden');

            console.log('🔍 fileInfo after changes:', fileInfo.className);

            

            // Show close button when file info is displayed

            if (this.elements.closeBtn) {

                this.elements.closeBtn.style.display = 'inline-block';

            }

        } else {

            console.log('🔍 Condition not met for showing file info:', { 

                fileInfo: !!fileInfo, 

                fileName: file.name, 

                totalRows: data.total_rows || data.row_count 

            });

            

            // Hide close button when file info is not displayed

            if (this.elements.closeBtn) {

                this.elements.closeBtn.style.display = 'none';

            }

        }



        



        // Store session ID for balance check

        this.state.sessionId = data.session_id;



        // Store file path for local files or record ID for Supabase files



        this.state.uploadedFilePath = data.filepath || data.storage_path;



        this.state.uploadedFileRecordId = data.record_id || null;



        



        // Disable process button until balance check is complete



        if (processBtn) {



            processBtn.disabled = true;



            processBtn.classList.add('balance-disabled');



            processBtn.textContent = 'Checking Balance...';



            // Process button disabled until balance check complete



        }



        



        // Hide balance check section initially



        if (this.elements.balanceCheckSection) {

            this.elements.balanceCheckSection.classList.add('balance-check-hidden');

        }



    }







    /**



     * Perform balance check on uploaded file



     */

    async performBalanceCheck() {

        try {

            if (!this.state.sessionId) {

                console.error('No session ID available for balance check');

                return;

            }



            // Get current document type for universal balance validation

            const documentType = window.documentTypeSelector ? window.documentTypeSelector.getSelectedType() : 'balance_sheet';



            const data = await VarydianUtils.safeFetch('/api/universal/validate-balance', {

                method: 'POST',

                headers: {

                    'Content-Type': 'application/json'

                },

                body: JSON.stringify({

                    session_id: this.state.sessionId,

                    document_type: documentType

                })

            });



            if (data.success) {

                // Balance validation response received
                
                console.log('🔍 API Response:', data);
                console.log('🔍 balance_check:', data.balance_check);

                const balanceData = data.balance_check || data;

                console.log('🔍 Final balanceData:', balanceData);

                this.displayBalanceCheck(balanceData);

            } else {

                this.showError('Balance check failed: ' + data.error);

            }



        } catch (error) {

            console.error('Balance check error:', error);

            // Don't show error to user for balance check failure, just log it

        }



    }



    



    /**



     * Show balance checking state



     */



    showBalanceChecking() {



        const { 



            balanceCheckSection, 



            balanceIndicator, 



            indicatorIcon,



            totalDebits, 



            totalCredits, 



            balanceDifference, 



            balanceMessage,



            statusIcon,



            statusText



        } = this.elements;



        



        if (balanceCheckSection) {

            balanceCheckSection.classList.remove('balance-check-hidden');

            balanceCheckSection.className = 'balance-check-section checking';

        }



        



        if (balanceIndicator) {



            balanceIndicator.className = 'balance-indicator checking';



        }



        



        if (indicatorIcon) indicatorIcon.textContent = '⏳';



        if (statusIcon) statusIcon.textContent = '⏳';



        if (statusText) statusText.textContent = 'Checking balance...';



        if (totalDebits) totalDebits.textContent = 'R 0.00';



        if (totalCredits) totalCredits.textContent = 'R 0.00';



        if (balanceDifference) balanceDifference.textContent = 'R 0.00';



        if (balanceMessage) balanceMessage.className = 'status-message';



    }



    



    /**



     * Display balance check results



     */



    displayBalanceCheck(balanceData) {



        const { 



            balanceCheckSection, 



            balanceIndicator, 



            indicatorIcon,



            totalDebits, 



            totalCredits, 



            balanceDifference, 



            balanceMessage,



            statusIcon,



            statusText



        } = this.elements;



        



        if (!balanceCheckSection) {
            return;
        }

        // Get current document type
        const documentType = window.documentTypeSelector ? window.documentTypeSelector.getSelectedType() : 'balance_sheet';

        // Show balance check section
        balanceCheckSection.classList.add('visible');

        // Update field labels based on document type
        const debitsLabel = document.getElementById('debitsLabel');
        const creditsLabel = document.getElementById('creditsLabel');
        const differenceLabel = document.getElementById('differenceLabel');

        if (documentType === 'income_statement') {
            totalDebits.textContent = `R ${(balanceData.total_revenue || 0).toLocaleString('en-ZA', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
            totalCredits.textContent = `R ${(balanceData.total_expenses || 0).toLocaleString('en-ZA', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
            balanceDifference.textContent = `R ${(balanceData.net_income || 0).toLocaleString('en-ZA', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
            
            if (debitsLabel) debitsLabel.textContent = 'Total Revenue:';
            if (creditsLabel) creditsLabel.textContent = 'Total Expenses:';
            if (differenceLabel) differenceLabel.textContent = 'Net Income:';
        } else if (documentType === 'balance_sheet') {
            totalDebits.textContent = `R ${(balanceData.total_debits || 0).toLocaleString('en-ZA', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
            totalCredits.textContent = `R ${(balanceData.total_credits || 0).toLocaleString('en-ZA', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
            balanceDifference.textContent = `R ${(balanceData.balance_difference || 0).toLocaleString('en-ZA', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
            
            if (debitsLabel) debitsLabel.textContent = 'Total Debits:';
            if (creditsLabel) creditsLabel.textContent = 'Total Credits:';
            if (differenceLabel) differenceLabel.textContent = 'Difference:';
        } else if (documentType === 'budget_report') {
            const budgetText = `R ${(balanceData.total_budget || 0).toLocaleString('en-ZA', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
            const actualText = `R ${(balanceData.total_actual || 0).toLocaleString('en-ZA', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
            const varianceText = `R ${(balanceData.variance || 0).toLocaleString('en-ZA', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
            
                        
            totalDebits.textContent = budgetText;
            totalCredits.textContent = actualText;
            balanceDifference.textContent = varianceText;
            
            if (debitsLabel) debitsLabel.textContent = 'Total Budget:';
            if (creditsLabel) creditsLabel.textContent = 'Total Actual:';
            if (differenceLabel) differenceLabel.textContent = 'Variance:';
        }

        



        // Update visual indicators based on balance status



        balanceCheckSection.className = 'balance-check-section';



        balanceIndicator.className = 'balance-indicator';



        balanceMessage.className = 'status-message';



        



                
        if (balanceData.is_balanced) {



            // Balanced state



            balanceCheckSection.classList.add('balanced');



            balanceIndicator.classList.add('balanced');



            balanceMessage.classList.add('balanced');



            balanceDifference.classList.add('highlight-green');



            balanceDifference.classList.remove('highlight-red');



            



            if (indicatorIcon) indicatorIcon.textContent = '✅';



            if (statusIcon) statusIcon.textContent = '✅';



            if (statusText) {
                if (documentType === 'balance_sheet') {
                    statusText.textContent = 'Balance sheet is balanced';
                } else if (documentType === 'income_statement') {
                    statusText.textContent = 'Income statement validated';
                } else if (documentType === 'budget_report') {
                    statusText.textContent = balanceData.is_balanced ? 'Budget report is balanced' : 'Budget variance detected';
                } else {
                    statusText.textContent = 'Document validated';
                }
            }



        } else {



            // Not balanced state



            balanceCheckSection.classList.add('not-balanced');



            balanceIndicator.classList.add('not-balanced');



            balanceMessage.classList.add('not-balanced');



            balanceDifference.classList.add('highlight-red');



            balanceDifference.classList.remove('highlight-green');



            



            if (indicatorIcon) indicatorIcon.textContent = '❌';



            if (statusIcon) statusIcon.textContent = '❌';



            if (statusText) {
                if (documentType === 'balance_sheet') {
                    statusText.textContent = `Not balanced: Difference R ${balanceData.balance_difference.toLocaleString('en-ZA', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
                } else if (documentType === 'income_statement') {
                    statusText.textContent = 'Income statement requires review';
                } else if (documentType === 'budget_report') {
                    // For budget reports, check if variance is within acceptable tolerance (0.01)
                    const variance = balanceData.variance || 0;
                    if (Math.abs(variance) < 0.01) {
                        statusText.textContent = 'Budget report is balanced';
                    } else {
                        statusText.textContent = `Budget variance detected: R ${Math.abs(variance).toLocaleString('en-ZA', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
                    }
                } else {
                    statusText.textContent = 'Document requires review';
                }
            }



        }





        // Update process button state and show options for unbalanced balances

        const processBtn = this.elements.processBtn;

        // Check if process button exists
        if (processBtn) {
            // Check if the document can be submitted based on balance status
            const canSubmit = balanceData.is_balanced || (documentType === 'income_statement'); // Income statements are always submittable

            if (canSubmit) {

                processBtn.disabled = false;

                processBtn.classList.remove('balance-disabled');

                processBtn.textContent = 'Submit for Review';
                    

                // Ensure the process button is visible

                processBtn.style.display = 'inline-block';
                    

                // Hide warning options

                this.hideUnbalancedOptions();

                    

            } else {

                processBtn.disabled = true;

                processBtn.classList.add('balance-disabled');

                // Update button text based on document type
                if (documentType === 'budget_report') {
                    processBtn.textContent = 'Budget Variance Detected - Cannot Process';
                } else {
                    processBtn.textContent = 'Balance Sheet Not Balanced - Cannot Process';
                }

                // Show options for unbalanced balance sheet
                this.showUnbalancedOptions(balanceData);
            }
        } else {
            this.showError('Process button not found');
        }


    }






    async processFileWithBalanceCheck() {
        console.log('🔍 Session ID:', this.state.sessionId);

        if (!this.state.sessionId) {
            console.log('❌ No session ID available');
            this.showError('No file uploaded');
            return;
        }

        console.log('✅ Session ID validated, proceeding with processing');

        // Get document type to determine processing flow
        const documentType = window.documentTypeSelector ? window.documentTypeSelector.getSelectedType() : 'balance_sheet';
        console.log('🔍 Processing document type:', documentType);

        // Balance check for all document types (balance sheets, income statements, budget reports)
        try {
            const requestBody = {
                session_id: this.state.sessionId,
                document_type: documentType
            };
            
            console.log('🔍 Validating balance for session:', this.state.sessionId, 'Type:', documentType);
            
            const balanceData = await VarydianUtils.safeFetch('/api/universal/validate-balance', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(requestBody)
            });
                
            console.log('🔍 Balance validation result:', balanceData);

            if (!balanceData.success) {
                console.log('❌ Balance validation failed:', balanceData);
                this.showError('Cannot process: Balance validation failed. Please try again.');
                return;
            }

            // Handle different document types for balance check results
            const balanceCheck = balanceData.balance_check;
            let canProceed = true;
            let errorMessage = '';

            if (documentType === 'balance_sheet') {
                if (!balanceCheck.is_balanced) {
                    canProceed = false;
                    errorMessage = `Balance sheet is not balanced. Difference: R ${Math.abs(balanceCheck.difference).toLocaleString('en-ZA', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
                }
            } else if (documentType === 'income_statement') {
                // Income statements are always valid for processing
                console.log('✅ Income statement validation passed');
            } else if (documentType === 'budget_report') {
                if (!balanceCheck.is_balanced) {
                    canProceed = false;
                    errorMessage = `Budget report variance detected: R ${Math.abs(balanceCheck.variance).toLocaleString('en-ZA', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
                }
            }

            if (!canProceed) {
                this.showError(errorMessage);
                return;
            }

            // Display balance check results in UI for all document types
            this.displayBalanceCheck(balanceCheck);

        } catch (error) {
            console.error('Balance validation error:', error);
            this.showError('Balance validation failed. Please try again.');
            return;
        }

        try {

            if (this.elements.fileInfo) {

            this.elements.fileInfo.classList.add('file-info--hidden');

            if (this.elements.fileInfo) {

            this.elements.fileInfo.classList.remove('file-info--visible');

        }

        }



            const documentTypeName = documentType.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase());

            this.setProcessingState(true, `Processing your ${documentTypeName}...`, 'Mapping accounts to GRAP line items');



            this.hideError();



            



            const requestBody = {

                session_id: this.state.sessionId

            };

            

            console.log('🔍 Starting GRAP processing for session:', this.state.sessionId);

            

            const data = await VarydianUtils.safeFetch('/api/processing', {



                method: 'POST',



                headers: {



                    'Content-Type': 'application/json'



                },



                body: JSON.stringify(requestBody)



            });

            

            console.log('🔍 Processing result:', data);



            



            if (data.success) {



                // Always redirect to mapping interface for review, even if auto-mapping succeeded

                this.showInfo('Processing complete. Redirecting to mapping review interface...');

                

                // Prepare mapping data including auto-mapped accounts

                const mappingData = {

                    session_id: this.state.sessionId,

                    mapped_accounts: data.mapped_accounts || [],

                    unmapped_accounts: data.unmapped_accounts || [],

                    total_accounts: data.total_accounts || 0,

                    mapping_confidence: data.mapping_confidence || 0,

                    detected_structure: data.detected_structure || {}

                };

                

                this.redirectToMappingReview(mappingData);



            } else {



                if (data.unmapped_accounts) {



                    // Redirect to mapping interface when unmapped accounts are detected

                    this.redirectToMapping(data.unmapped_accounts, data.detected_structure);



                } else {



                    // Provide more user-friendly error messages

                    let errorMessage = data.error || 'Processing failed';

                    

                    // Check for specific error patterns and provide better messages

                    if (errorMessage.includes('Required columns') && errorMessage.includes('Debit Balance') && errorMessage.includes('Credit Balance')) {

                        errorMessage = 'Invalid file format. Your file must contain "Debit Balance" and "Credit Balance" columns. Please check your balance sheet format and try again.';

                    } else if (errorMessage.includes('not found') && errorMessage.includes('Available columns')) {

                        errorMessage = 'Column mismatch. The required columns for processing were not found. Please ensure your balance sheet has the correct column headers: "Account Code", "Account Description", "Debit Balance", "Credit Balance".';

                    } else if (errorMessage.includes('Processing error')) {

                        errorMessage = 'File processing error. The uploaded file could not be processed correctly. Please verify it\'s a valid balance sheet file.';

                    } else if (errorMessage.includes('File not found')) {

                        errorMessage = 'File not found. Please upload the file again.';

                    }

                    

                    this.showError(errorMessage);



                }



                // Only show file info if there's actual data

                if (this.hasFileInfoData()) {

                    this.elements.fileInfo.classList.add('file-info--visible');

                    this.elements.fileInfo.classList.remove('file-info--hidden');

                }



            }



            



        } catch (error) {



            // Check if this is actually a valid unmapped accounts response that got caught as an error

            if (error.message && error.message.includes('HTTP error! status: 400')) {

                try {

                    // Try to extract JSON from the error message

                    // The error message format is: "HTTP error! status: 400 - {json_data}"

                    const jsonMatch = error.message.match(/\{[\s\S]*\}/);

                    

                    if (jsonMatch) {

                        const errorData = JSON.parse(jsonMatch[0]);

                        

                        if (errorData.unmapped_accounts && errorData.unmapped_accounts.length > 0) {

                            

                            // This is actually a valid workflow step - redirect to mapping

                            this.redirectToMapping(errorData.unmapped_accounts, errorData.detected_structure);

                            return;

                        }

                    }

                } catch (parseError) {

                    // If we can't parse the error, fall through to normal error handling

                }

            }



            // Provide more user-friendly error messages for network/server errors

            let errorMessage = error.message || 'Processing failed';

            

            if (errorMessage.includes('HTTP error! status: 500')) {

                errorMessage = 'Server error occurred. The system encountered an error while processing your file. Please try again or contact support if the problem persists.';

            } else if (errorMessage.includes('HTTP error! status: 400')) {

                errorMessage = 'Bad request. The file format or data may be invalid. Please check your balance sheet format and try again.';

            } else if (errorMessage.includes('HTTP error! status: 404')) {

                errorMessage = 'File not found on server. Please upload your file again.';

            } else if (errorMessage.includes('Failed to fetch')) {

                errorMessage = 'Network error. Unable to connect to the server. Please check your internet connection and try again.';

            } else if (errorMessage.includes('AbortError')) {

                errorMessage = 'Request timeout. The processing took too long. Please try with a smaller file or contact support.';

            }



            this.showError(errorMessage);



            // Only show file info if there's actual data

            if (this.hasFileInfoData()) {

                this.elements.fileInfo.classList.add('file-info--visible');

                this.elements.fileInfo.classList.remove('file-info--hidden');

            }

        } finally {



            this.setProcessingState(false);



        }



    }



    /**

     * Close upload and remove uploaded file (works like reupload)

     */

    async closeUpload() {

        // Check if there's a file to remove

        if (!this.state.sessionId) {

            this.showError('No file uploaded to remove');

            return;

        }



        // Show loading state on close button

        const closeBtn = this.elements.closeBtn;

        if (closeBtn) {

            closeBtn.disabled = true;

            closeBtn.textContent = 'Closing...';

            closeBtn.classList.add('btn-loading');

        }



        try {

            console.log('🗑️ Removing uploaded file - Session ID:', this.state.sessionId);

            

            const requestBody = {

                session_id: this.state.sessionId

            };



            const data = await VarydianUtils.safeFetch('/api/remove-upload', {

                method: 'POST',

                headers: {

                    'Content-Type': 'application/json'

                },

                body: JSON.stringify(requestBody)

            });



            if (data.success) {

                console.log('✅ File successfully removed');

                

                // Reset the interface for new upload (use existing resetUploadState method)

                this.resetUploadState();

                

            } else {

                console.log('❌ Failed to remove file:', data.error);

                this.showError('Failed to remove uploaded file: ' + (data.error || 'Unknown error'));

            }



        } catch (error) {

            console.error('Error removing uploaded file:', error);

            this.showError('Failed to remove uploaded file. Please try again.');

        } finally {

            // Reset close button state

            if (closeBtn) {

                closeBtn.disabled = false;

                closeBtn.textContent = 'Close & Remove File';

                closeBtn.classList.remove('btn-loading');

            }

        }

    }



    /**

     * Show confirmation modal

     */

    showConfirmationModal(title, message, confirmText, cancelText) {

        return new Promise((resolve) => {

            // Create modal if it doesn't exist

            let modal = document.getElementById('confirmModal');

            if (!modal) {

                modal = this.createConfirmationModal();

                document.body.appendChild(modal);

            }



            // Update modal content

            const modalTitle = modal.querySelector('.modal-header h3');

            const modalMessage = modal.querySelector('.modal-body p');

            const confirmBtn = modal.querySelector('#confirmRemove');

            const cancelBtn = modal.querySelector('#confirmCancel');



            if (modalTitle) modalTitle.textContent = title;

            if (modalMessage) modalMessage.textContent = message;

            if (confirmBtn) confirmBtn.textContent = confirmText;

            if (cancelBtn) cancelBtn.textContent = cancelText;



            // Show modal

            modal.classList.remove('modal-overlay--hidden');



            // Handle button clicks

            const handleConfirm = () => {

                cleanup();

                resolve(true);

            };



            const handleCancel = () => {

                cleanup();

                resolve(false);

            };



            const cleanup = () => {

                modal.classList.add('modal-overlay--hidden');

                confirmBtn.removeEventListener('click', handleConfirm);

                cancelBtn.removeEventListener('click', handleCancel);

            };



            confirmBtn.addEventListener('click', handleConfirm);

            cancelBtn.addEventListener('click', handleCancel);



            // Also close on escape key

            const handleEscape = (e) => {

                if (e.key === 'Escape') {

                    cleanup();

                    resolve(false);

                    document.removeEventListener('keydown', handleEscape);

                }

            };

            document.addEventListener('keydown', handleEscape);

        });

    }



    /**

     * Create confirmation modal

     */

    createConfirmationModal() {

        const modal = document.createElement('div');

        modal.id = 'confirmModal';

        modal.className = 'modal-overlay modal-overlay--hidden';

        modal.innerHTML = `

            <div class="modal-container">

                <div class="modal-header">

                    <h3>Confirm File Removal</h3>

                </div>

                <div class="modal-body">

                    <p>Are you sure you want to remove this uploaded file? This action cannot be undone.</p>

                </div>

                <div class="modal-footer">

                    <button id="confirmCancel" class="btn btn-secondary" type="button">Cancel</button>

                    <button id="confirmRemove" class="btn btn-danger" type="button">Remove File</button>

                </div>

            </div>

        `;

        return modal;

    }



    /**

     * Reset upload interface to initial state

     */

    resetUploadInterface() {

        // Clear session ID

        this.state.sessionId = null;

        

        // Hide file info and balance check sections

        this.elements.fileInfo.classList.add('file-info--hidden');

        this.elements.fileInfo.classList.remove('file-info--visible');

        

        const balanceCheckSection = document.getElementById('balanceCheckSection');

        if (balanceCheckSection) {

            balanceCheckSection.classList.add('display-none');

        }

        

        // Hide buttons

        this.elements.processBtn.style.display = 'none';

        if (this.elements.closeBtn) {

            this.elements.closeBtn.style.display = 'none';

        }

        

        // Reset file input

        const fileInput = this.elements.fileInput;

        if (fileInput) {

            fileInput.value = '';

        }

        

        // Show upload box again

        const uploadBox = document.getElementById('uploadBox');

        if (uploadBox) {

            uploadBox.style.display = 'block';

        }

        

        // Clear any messages

        this.clearMessages();

    }



    /**

     * Show options for unbalanced balance sheet

     */

    showUnbalancedOptions(balanceData) {

        // Create or update unbalanced options section

        let optionsSection = document.getElementById('unbalancedOptions');

        

        if (!optionsSection) {

            optionsSection = document.createElement('div');

            optionsSection.id = 'unbalancedOptions';

            optionsSection.className = 'unbalanced-options-section';

            

            // Insert after balance check section

            const balanceSection = document.querySelector('.balance-check-section');

            if (balanceSection && balanceSection.parentNode) {

                balanceSection.parentNode.insertBefore(optionsSection, balanceSection.nextSibling);

            }

        }

        

        const canProceedWithWarning = balanceData.allow_proceed_with_warning;

        // Get the correct difference value based on document type
        const documentType = window.documentTypeSelector ? window.documentTypeSelector.getSelectedType() : 'balance_sheet';
        let difference = 0;
        
        if (documentType === 'budget_report') {
            difference = balanceData.variance || 0;
        } else {
            difference = balanceData.balance_difference || 0;
        }
        
        
        

        // Set appropriate title based on document type
        const sectionTitle = documentType === 'budget_report' ? 'Budget Report Options' : 'Balance Sheet Options';
        
        optionsSection.innerHTML = `

            <div class="unbalanced-options-container">

                <h4>${sectionTitle}</h4>

                <p class="unbalanced-message">

                    <strong>${documentType === 'budget_report' ? 'Budget Variance:' : 'Balance Difference:'}</strong> R ${difference.toLocaleString('en-ZA', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}

                </p>

                <p class="recommendation">${balanceData.recommendation || 'Please check your balance sheet and try again.'}</p>

                

                <div class="unbalanced-actions">

                    <button type="button" class="btn btn-secondary" onclick="uploadService.reuploadFile()">

                        Correct & Re-upload

                    </button>

                    

                    ${canProceedWithWarning ? `

                        <button type="button" class="btn btn-warning" onclick="uploadService.proceedWithWarning()">

                            Proceed with Warning

                        </button>

                    ` : `

                        <button type="button" class="btn btn-outline" onclick="uploadService.saveForLater()" disabled>

                            Save for Later (Coming Soon)

                        </button>

                    `}

                    

                    <button type="button" class="btn btn-outline" onclick="uploadService.viewBalanceDetails()">

                        View Balance Details

                    </button>

                </div>

                

                ${canProceedWithWarning ? `

                    <div class="warning-notice">

                        <p><strong>Warning:</strong> Proceeding with an unbalanced balance sheet may result in inaccurate financial statements. This should only be done if you understand the reason for the discrepancy and can correct it later.</p>

                    </div>

                ` : ''}

            </div>

        `;

        

        optionsSection.classList.remove('options-hidden');

    }



    /**

     * Hide unbalanced options section

     */

    hideUnbalancedOptions() {

        const optionsSection = document.getElementById('unbalancedOptions');

        if (optionsSection) {

            optionsSection.classList.add('options-hidden');

        }

    }



    /**

     * Proceed with unbalanced balance sheet (with warning)

     */

    async proceedWithWarning() {

        if (!this.state.uploadedFilePath) {

            this.showError('No file uploaded');

            return;

        }



        try {

            this.setProcessingState(true, 'Proceeding with warning...', 'Acknowledging balance discrepancy');



            const requestBody = {

                filepath: this.state.uploadedFilePath,

                proceed_with_warning: true

            };



            if (this.state.uploadedFileRecordId) {

                requestBody.record_id = this.state.uploadedFileRecordId;

                requestBody.storage_type = 'supabase';

            }



            const data = await VarydianUtils.safeFetch('/api/proceed-unbalanced', {

                method: 'POST',

                headers: {

                    'Content-Type': 'application/json'

                },

                body: JSON.stringify(requestBody)

            });



            if (data.success) {

                // Enable the process button and proceed to normal processing

                const processBtn = this.elements.processBtn;

                if (processBtn) {

                    processBtn.disabled = false;

                    processBtn.classList.remove('balance-disabled');

                    processBtn.textContent = 'Process Balance Sheet (With Warning)';

                }



                // Hide warning options

                this.hideUnbalancedOptions();



                // Show success message

                this.showSuccess('Proceeding with unbalanced balance sheet. Financial statements may not be accurate.');



                // Continue with normal processing

                await this.processFileWithBalanceCheck();



            } else {

                this.showError('Failed to proceed with warning: ' + data.error);

            }



        } catch (error) {

            this.showError('Error proceeding with warning. Please try again.');

        } finally {

            this.setProcessingState(false);

        }

    }



    /**

     * Re-upload file to correct balance

     */

    reuploadFile() {

        console.log('🧹 Re-upload clicked - cleaning up session');

        

        // Clean up the current session before re-uploading

        if (this.state.sessionId) {

            this.cleanupSession(this.state.sessionId);

        }

        

        // Reset file input and state

        const fileInput = document.getElementById('fileInput');

        if (fileInput) {

            fileInput.value = '';

        }



        // Reset state

        this.state.uploadedFilePath = null;

        this.state.uploadedFileRecordId = null;

        this.state.resultsFile = null;

        this.state.sessionId = null; // Reset session ID



        // Hide balance check and options

        const balanceSection = document.querySelector('.balance-check-section');

        if (balanceSection) {

            balanceSection.classList.add('balance-check-hidden');

        }



        this.hideUnbalancedOptions();



        // Reset file info

        if (this.elements.fileInfo) {

            this.elements.fileInfo.classList.add('file-info--hidden');

            if (this.elements.fileInfo) {

            this.elements.fileInfo.classList.remove('file-info--visible');

        }

        }



        // Reset process button

        const processBtn = this.elements.processBtn;

        if (processBtn) {

            processBtn.disabled = true;

            processBtn.classList.add('balance-disabled');

            processBtn.textContent = 'Process Balance Sheet';

        }



        // Show upload box again (reset to initial state)

        this.manageUploadBoxVisibility(true);

        const uploadBox = this.elements.uploadBox;

        if (uploadBox) {

            uploadBox.classList.remove('upload-zone--success', 'upload-zone--error');

            uploadBox.classList.add('upload-zone--idle');

        }



        // Hide any error messages

        this.hideError();



        // Reset upload zone text to initial state

        const uploadIcon = uploadBox.querySelector('.upload-icon');

        const uploadTitle = uploadBox.querySelector('h3');

        const uploadText = uploadBox.querySelector('p');



        if (uploadIcon) uploadIcon.textContent = '';

        if (uploadTitle) uploadTitle.textContent = 'Drag & Drop Your File Here';

        if (uploadText) uploadText.textContent = 'or click to browse';



        // Don't automatically open file browser - let user click when ready

    }



    /**

     * View balance details (show detailed breakdown)

     */

    viewBalanceDetails() {

        // This could open a modal with detailed balance information

        alert('Balance details feature coming soon! This will show a detailed breakdown of the balance sheet accounts and their balances.');

    }



    /**

     * Save for later (placeholder for future implementation)

     */

    saveForLater() {

        this.showInfo('Save for later feature coming soon! This will allow you to save the unbalanced balance sheet and continue later.');

    }



    /**



     * Display processing results



     */



    displayResults(summary) {



        // Update summary cards with safety checks



        this.updateElement('totalAssets', VarydianUtils.formatCurrency(summary.total_assets || 0));



        this.updateElement('totalLiabilities', VarydianUtils.formatCurrency(summary.total_liabilities || 0));



        this.updateElement('netAssets', VarydianUtils.formatCurrency(summary.net_assets || 0));



        this.updateElement('surplus', VarydianUtils.formatCurrency(summary.surplus_deficit || 0));



        



        // Update ratios with safety checks



        if (summary.ratios) {



            this.updateElement('currentRatio', (summary.ratios.current_ratio || 0).toFixed(2));



            this.updateElement('debtToEquity', (summary.ratios.debt_to_equity || 0).toFixed(2));



            this.updateElement('operatingMargin', (summary.ratios.operating_margin || 0).toFixed(2) + '%');



            this.updateElement('returnOnAssets', (summary.ratios.return_on_assets || 0).toFixed(2) + '%');



        }



        



        // Show results section



        if (this.elements.resultsSection) {

            this.elements.resultsSection.classList.add('results-section--visible');

            this.elements.resultsSection.classList.remove('results-section--hidden');

            VarydianUtils.scrollToElement(this.elements.resultsSection);

        }



    }







    /**



     * Generate PDF report



     */



    async generatePDF() {



        if (!this.state.resultsFile) {



            this.showError('No results available');



            return;



        }



        



        const { pdfLoader, pdfSuccess } = this.elements;



        



        pdfLoader.classList.add('pdf-loader--visible');



        pdfLoader.classList.remove('pdf-loader--hidden');



        pdfSuccess.classList.add('pdf-success--hidden');



        pdfSuccess.classList.remove('pdf-success--visible');



        



        try {



            const requestBody = {

                results_file: this.state.resultsFile

            };

            const requestBodyString = JSON.stringify(requestBody);



            const data = await VarydianUtils.safeFetch('/api/generate-pdf', {



                method: 'POST',



                headers: {



                    'Content-Type': 'application/json'



                },



                body: requestBodyString



            });



            if (data.success) {



                // Update download link



                const downloadLink = this.elements.downloadLink;



                if (downloadLink) {



                    downloadLink.href = data.download_url;



                    downloadLink.download = data.pdf_filename;



                    // Make the download link visible and functional

                    downloadLink.classList.remove('element--hidden');

                    downloadLink.classList.add('element--visible');



                    // Trigger automatic download



                    this.triggerDownload(data.download_url, data.pdf_filename);



                }



                



                pdfSuccess.classList.add('pdf-success--visible');



                pdfSuccess.classList.remove('pdf-success--hidden');



                // Show success message with more details



                const successHeading = pdfSuccess.querySelector('h3');



                if (successHeading) {



                    successHeading.innerHTML = `PDF Generated Successfully!<br><small>${data.pdf_filename}</small>`;



                }



            } else {



                // Provide more user-friendly PDF generation error messages

                let pdfErrorMessage = data.error || 'Unknown error';

                

                // Check for specific error patterns and provide better messages

                if (pdfErrorMessage.includes('Results file not found')) {

                    pdfErrorMessage = 'Results file not found. Please process the balance sheet again before generating PDF.';

                } else if (pdfErrorMessage.includes('No results file specified')) {

                    pdfErrorMessage = 'No results available. Please process a balance sheet first.';

                } else if (pdfErrorMessage.includes('PDF generation error')) {

                    pdfErrorMessage = 'PDF generation failed. There was an error creating your financial statements PDF. Please try again.';

                }



                this.showError(pdfErrorMessage);



            }



            



        } catch (error) {



            // Provide more user-friendly error messages for PDF generation

            let errorMessage = error.message || 'PDF generation failed';

            

            if (errorMessage.includes('HTTP error! status: 500')) {

                errorMessage = 'Server error during PDF generation. Please try again or contact support if the problem persists.';

            } else if (errorMessage.includes('HTTP error! status: 400')) {

                errorMessage = 'Invalid request for PDF generation. Please process the balance sheet first.';

            } else if (errorMessage.includes('Failed to fetch')) {

                errorMessage = 'Network error during PDF generation. Please check your internet connection and try again.';

            }



            this.showError(errorMessage);

        } finally {



            pdfLoader.classList.add('pdf-loader--hidden');



            pdfLoader.classList.remove('pdf-loader--visible');



        }



    }







    /**



     * Trigger file download



     */



    triggerDownload(downloadUrl, filename) {



        try {



            // Create a temporary anchor element for download



            const link = document.createElement('a');



            link.href = downloadUrl;



            link.download = filename;



            link.classList.add('element--hidden');



            document.body.appendChild(link);



            link.click();



            document.body.removeChild(link);



        } catch (error) {



            // Fallback: open in new window



            window.open(downloadUrl, '_blank');



        }



    }







    /**



     * Remove uploaded file



     */



    async removeUploadedFile() {



        if (!this.state.uploadedFileRecordId && !this.state.uploadedFilePath) {



            this.showError('No uploaded file available to remove');



            return;



        }





        // Show custom confirmation modal



        this.showConfirmModal();



    }







    /**



     * Show confirmation modal



     */



    showConfirmModal() {



        if (this.elements.confirmModal) {



            this.elements.confirmModal.classList.remove('modal-overlay--hidden');



            this.elements.confirmModal.classList.add('modal-overlay--visible');



            // Focus on confirm button for accessibility



            if (this.elements.confirmRemove) {



                this.elements.confirmRemove.focus();



            }



        }



    }







    /**



     * Hide confirmation modal



     */



    hideConfirmModal() {



        if (this.elements.confirmModal) {



            this.elements.confirmModal.classList.remove('modal-overlay--visible');



            this.elements.confirmModal.classList.add('modal-overlay--hidden');



        }



    }







    /**



     * Execute file removal after confirmation



     */



    async executeFileRemoval() {



        try {



            // For Supabase files, use the delete API



            if (this.state.uploadedFileRecordId) {



                const response = await fetch(`/api/delete-balance-sheet/${this.state.uploadedFileRecordId}?user_id=demo_user`, {



                    method: 'DELETE'



                });



                if (!response.ok) {



                    throw new Error(`Failed to remove file: ${response.statusText}`);



                }



                const result = await response.json();



                if (!result.success) {



                    throw new Error(result.error || 'Failed to remove file');



                }



                // Hide modal first



                this.hideConfirmModal();



                // Reset the upload state



                this.resetUploadState();



            } else {



                // For local files (if any), we would need a different approach



                this.hideConfirmModal();



                this.showError('Cannot remove local files through this interface');



                return;



            }



        } catch (error) {



            this.hideConfirmModal();



            this.showError('Failed to remove file: ' + error.message);

        }



    }







    /**



     * Reset upload state after file removal



     */



    resetUploadState() {
        
        console.log('🔍 resetUploadState() called - this will overwrite balance display!');
        
        this.state.uploadedFilePath = null;



        this.state.uploadedFileRecordId = null;



        this.state.resultsFile = null;



        



        // Reset UI elements

        this.manageUploadBoxVisibility(true);



        if (this.elements.fileInfo) {

            this.elements.fileInfo.classList.add('file-info--hidden');

        }



        if (this.elements.fileInfo) {

            this.elements.fileInfo.classList.remove('file-info--visible');

        }



        this.hideResults();



        this.hideError();



        this.elements.fileInput.value = '';



        



        // Disable the process button when file is removed



        if (this.elements.processBtn) {



            this.elements.processBtn.disabled = true;



            this.elements.processBtn.classList.remove('balance-disabled');



            this.elements.processBtn.textContent = 'Process Balance Sheet';

            

            // Ensure process button is visible for new uploads

            this.elements.processBtn.style.display = 'inline-block';

        }



        



        // Hide and reset balance check section



        if (this.elements.balanceCheckSection) {

            this.elements.balanceCheckSection.classList.add('balance-check-hidden');

            this.elements.balanceCheckSection.className = 'balance-check-section';

        }



        



        // Reset balance indicator



        if (this.elements.balanceIndicator) {



            this.elements.balanceIndicator.className = 'balance-indicator';



        }



        



        if (this.elements.indicatorIcon) {



            this.elements.indicatorIcon.textContent = '';



        }



        



        // Reset status message



        if (this.elements.balanceMessage) {



            this.elements.balanceMessage.className = 'status-message';



        }



        



        if (this.elements.statusIcon) {



            this.elements.statusIcon.textContent = '';



        }



        



        if (this.elements.statusText) {



            this.elements.statusText.textContent = 'Checking balance...';



        }



        



        // Reset balance check values



        if (this.elements.totalDebits) {



            this.elements.totalDebits.textContent = 'R 0.00';



        }



        if (this.elements.totalCredits) {



            this.elements.totalCredits.textContent = 'R 0.00';



        }



        if (this.elements.balanceDifference) {



            console.log('🔍 Overwriting balance difference with R 0.00 in resetUploadState!');
            this.elements.balanceDifference.textContent = 'R 0.00';

            this.elements.balanceDifference.classList.remove('highlight-red', 'highlight-green');



        }



        



        // Hide PDF related elements



        if (this.elements.pdfLoader) {



            this.elements.pdfLoader.classList.add('pdf-loader--hidden');



            this.elements.pdfLoader.classList.remove('pdf-loader--visible');



        }



        if (this.elements.pdfSuccess) {



            this.elements.pdfSuccess.classList.add('pdf-success--hidden');



            this.elements.pdfSuccess.classList.remove('pdf-success--visible');



        }



        



        // Clear financial statement data



        this.updateElement('totalAssets', 'R 0.00');



        this.updateElement('totalLiabilities', 'R 0.00');



        this.updateElement('netAssets', 'R 0.00');



        this.updateElement('surplus', 'R 0.00');



        this.updateElement('currentRatio', '0.00');



        this.updateElement('debtToEquity', '0.00');



        this.updateElement('operatingMargin', '0.00%');



        this.updateElement('returnOnAssets', '0.00%');



        



        // Scroll to upload area



        const uploadSection = this.elements.uploadBox.closest('.upload-section');



        if (uploadSection) {



            VarydianUtils.scrollToElement(uploadSection, { top: 100 });



        }



    }







    /**



     * Upload another file



     */



    uploadAnother() {



        // Reset state



        this.state.uploadedFilePath = null;



        this.state.resultsFile = null;



        



        // Reset UI

        this.manageUploadBoxVisibility(true);



        if (this.elements.fileInfo) {

            this.elements.fileInfo.classList.add('file-info--hidden');

        }



        if (this.elements.fileInfo) {

            this.elements.fileInfo.classList.remove('file-info--visible');

        }



        this.hideResults();



        this.hideError();



        this.elements.fileInput.value = '';



        



        // Disable the process button when uploading another file



        if (this.elements.processBtn) {



            this.elements.processBtn.disabled = true;



        }



        // Clear file details text content

        if (this.elements.fileName) {

            this.elements.fileName.textContent = '';

        }

        if (this.elements.fileSize) {

            this.elements.fileSize.textContent = '';

        }

        if (this.elements.fileRows) {

            this.elements.fileRows.textContent = '';

        }



        // Hide PDF related elements



        if (this.elements.pdfLoader) {



            this.elements.pdfLoader.classList.add('pdf-loader--hidden');



            this.elements.pdfLoader.classList.remove('pdf-loader--visible');



        }



        if (this.elements.pdfSuccess) {



            this.elements.pdfSuccess.classList.add('pdf-success--hidden');



            this.elements.pdfSuccess.classList.remove('pdf-success--visible');



        }



        // Clear financial statement data (close current statement)

        this.updateElement('totalAssets', 'R 0.00');

        this.updateElement('totalLiabilities', 'R 0.00');

        this.updateElement('netAssets', 'R 0.00');

        this.updateElement('surplus', 'R 0.00');

        this.updateElement('currentRatio', '0.00');

        this.updateElement('debtToEquity', '0.00');

        this.updateElement('operatingMargin', '0.00%');

        this.updateElement('returnOnAssets', '0.00%');



        // Scroll to upload area



        const uploadSection = this.elements.uploadBox.closest('.upload-section');



        if (uploadSection) {



            VarydianUtils.scrollToElement(uploadSection, { top: 100 });



        } else {



            VarydianUtils.scrollToElement(this.elements.uploadBox, { top: 100 });



        }



        



        // Focus on upload box for better UX



        this.elements.uploadBox.focus();



    }



/**





 * Update element content safely





 */



setProcessingState(isProcessing, message = '', subtext = '') {

    this.state.isProcessing = isProcessing;

    

    const { uploadBox, processingLoader } = this.elements;

    

    if (isProcessing) {

        uploadBox.classList.add('upload-box--hidden');

        uploadBox.classList.remove('upload-box--visible');

        processingLoader.classList.add('processing-loader--visible');

        processingLoader.classList.remove('processing-loader--hidden');

        

        if (message) {

            processingLoader.querySelector('p').textContent = message;

        }



        if (subtext) {

            const subtextEl = processingLoader.querySelector('.loader-subtext');

            if (subtextEl) {

                subtextEl.textContent = subtext;

            }

        }

    } else {

        processingLoader.classList.add('processing-loader--hidden');

        processingLoader.classList.remove('processing-loader--visible');



        if (this.state.uploadedFilePath) {

            // Only show file info if there's actual data

            if (this.hasFileInfoData()) {

                this.elements.fileInfo.classList.add('file-info--visible');

                this.elements.fileInfo.classList.remove('file-info--hidden');

            }

        }

        // Note: Don't show upload box here - let manageUploadBoxVisibility handle it

        // This prevents conflicts with showFileInfo which explicitly hides the upload box

    }

}



updateElement(id, content) {

    const element = document.getElementById(id);

    if (element) {

        element.textContent = content;

    }

}



/**

 * Show error message

 */

showError(message) {

    VarydianUtils.showError(message, this.elements.errorMessage);

}



/**

 * Show an informational message

 */

showInfo(message) {

    if (this.elements.errorMessage) {

        this.elements.errorMessage.textContent = message;

        this.elements.errorMessage.className = 'message message--info message--visible';

        

        // Auto-hide after 3 seconds

        setTimeout(() => {

            if (this.elements.errorMessage) {

                this.elements.errorMessage.classList.remove('message--visible');

            }

        }, 3000);

    }

}



/**

 * Hide error message

 */

hideError() {

    VarydianUtils.hideError(this.elements.errorMessage);

}







    /**

 * Show success message

 */

showSuccess(message) {

    // Use the same error element but with success styling

    const errorElement = this.elements.errorMessage;

    

    if (errorElement) {

        errorElement.textContent = message;

        errorElement.className = 'error-box error-box--success error-box--visible';

        

        // Auto-hide after 5 seconds

        setTimeout(() => {

            this.hideError();

        }, 5000);

    }

}







    /**

 * Hide results section

 */

hideResults() {

    if (this.elements.resultsSection) {

        this.elements.resultsSection.classList.add('results-section--hidden');

        this.elements.resultsSection.classList.remove('results-section--visible');

    }

}







    /**

 * Hide file information

 */

hideFileInfo() {

    if (this.elements.fileInfo) {

        this.elements.fileInfo.classList.add('file-info--hidden');

        this.elements.fileInfo.classList.remove('file-info--visible');

    }

}







    /**

 * Check if file info has actual data

 */

hasFileInfoData() {

    return this.elements.fileName && 

           this.elements.fileName.textContent && 

           this.elements.fileName.textContent.trim() !== '';

}







    /**

 * Get current state

 */

getState() {

    return { ...this.state };

}







    /**



     * Cleanup method



     */



    /**

     * Unified cleanup method for both close and re-upload actions

     */

    async cleanupSession(sessionId) {

        // Use the working remove-upload endpoint for all cleanup operations

        try {

            console.log('🧹 Cleaning up session:', sessionId);

            

            const response = await VarydianUtils.safeFetch('/api/remove-upload', {

                method: 'POST',

                headers: {

                    'Content-Type': 'application/json'

                },

                body: JSON.stringify({

                    session_id: sessionId

                })

            });

            

            if (response.success) {

                console.log('✅ Cleanup successful:', response.message);

                return { success: true, message: response.message };

            } else {

                console.error('❌ Cleanup failed:', response.error);

                return { success: false, error: response.error };

            }

        } catch (error) {

            console.error('❌ Error during cleanup:', error);

            return { success: false, error: error.message };

        }

    }



    async cleanupUnbalancedBalanceSheet(sessionId) {

        // Legacy method - use unified cleanup method

        return await this.cleanupSession(sessionId);

    }



    destroy() {

        // Remove event listeners

        const { uploadBox, fileInput, processBtn, generatePdfBtn, uploadAnotherBtn } = this.elements;

        

        uploadBox.removeEventListener('click', () => fileInput.click());

        uploadBox.removeEventListener('dragover', this.boundMethods.handleDragOver);

        uploadBox.removeEventListener('dragleave', this.boundMethods.handleDragLeave);

        uploadBox.removeEventListener('drop', this.boundMethods.handleDrop);

        

        fileInput.removeEventListener('change', this.boundMethods.handleFileInput);

        processBtn.removeEventListener('click', this.boundMethods.processFileWithBalanceCheck);

        

        if (this.elements.closeBtn) {

            this.elements.closeBtn.removeEventListener('click', this.boundMethods.closeUpload);

        }

        

        if (generatePdfBtn) {

            generatePdfBtn.removeEventListener('click', this.boundMethods.generatePDF);

        }

        

        if (uploadAnotherBtn) {

            uploadAnotherBtn.removeEventListener('click', this.boundMethods.uploadAnother);

        }

        

        // Reset state

        this.state = {

            uploadedFilePath: null,

            resultsFile: null,

            isProcessing: false,

            currentStep: null

        };

    }



    redirectToMappingReview(mappingData) {

        try {

            // Store mapping data in sessionStorage for the mapping interface

            sessionStorage.setItem('mappingReviewData', JSON.stringify(mappingData));

            

            // Show user-friendly message about redirect

            this.showInfo('Redirecting to mapping review interface...');

            

            // Redirect to mapping interface with review parameter

            window.location.href = `/mapping?review=true&session_id=${mappingData.session_id}`;

            

        } catch (error) {

            this.showError('Unable to redirect to mapping interface. Please try again.');

        }

    }



    redirectToMapping(unmappedAccounts, detectedStructure) {

        /**

         * Redirect to mapping interface when unmapped accounts are detected

         */

        try {

            // Show user-friendly message about redirect

            this.showInfo('Redirecting to mapping interface...');

            

            // Store unmapped accounts data for mapping interface

            const mappingData = {

                unmapped_accounts: unmappedAccounts,

                detected_structure: detectedStructure,

                session_id: this.state.sessionId

            };

            sessionStorage.setItem('mappingData', JSON.stringify(mappingData));

            

            // Redirect to mapping page with session ID

            window.location.href = `/mapping?session_id=${this.state.sessionId}`;

            

        } catch (error) {

            this.showError('Unable to redirect to mapping interface. Please try again.');

        }

    }



    /**

     * Manages the visibility of the upload box and file info sections

     * @param {boolean} showUploadBox - Whether to show the upload box (true) or hide it (false)

     */

    manageUploadBoxVisibility(showUploadBox = true) {

        const { uploadBox, fileInfo } = this.elements;

        

        if (showUploadBox) {

            // Show upload box, hide file info

            uploadBox.classList.remove('upload-box--hidden');

            uploadBox.classList.add('upload-box--visible');

            if (fileInfo) {

                fileInfo.classList.add('file-info--hidden');

                fileInfo.classList.remove('file-info--visible');

            }

        } else {

            // Hide upload box, show file info

            uploadBox.classList.add('upload-box--hidden');

            uploadBox.classList.remove('upload-box--visible');

            if (fileInfo) {

                fileInfo.classList.remove('file-info--hidden');

                fileInfo.classList.add('file-info--visible');

            }

        }

    }



}







// Check submission status on page load

async function checkSubmissionStatus() {

    try {

        // Add debug logging if available

        if (typeof debugLog === 'function') {

            debugLog('🔍 Checking submission status...', 'info');

        }

        

        // Check if there's a session ID in the URL (viewing a specific submitted file)

        const urlParams = new URLSearchParams(window.location.search);

        const sessionId = urlParams.get('session_id');

        

        if (typeof debugLog === 'function') {

            debugLog(`📍 Session ID in URL: ${sessionId ? sessionId.substring(0, 8) + '...' : 'None'}`, 'info');

        }

        

        // Only lock if we're viewing a specific submitted file (session_id in URL)

        // This allows users to upload new files even if they have pending submissions

        if (sessionId) {

            if (typeof debugLog === 'function') {

                debugLog('📡 Fetching user submissions for specific session...', 'info');

            }

            

            const response = await fetch(`/api/submissions/user`);

            const result = await response.json();

            

            if (result.success) {

                if (typeof debugLog === 'function') {

                    debugLog(`📊 Found ${result.submissions.length} submissions`, 'info');

                }

                

                // Check if this session has a submission

                const submission = result.submissions.find(sub => 

                    sub.filepath && sub.filepath.includes(sessionId)

                );

                

                if (submission) {

                    if (typeof debugLog === 'function') {

                        debugLog(`🎯 Found submission for session: ${submission.status}`, 'info');

                    }

                    

                    // Only lock if the submission is pending or approved

                    if (submission.status === 'pending' || submission.status === 'approved') {

                        // File is locked, show message and disable editing

                        const uploadBox = document.getElementById('uploadBox');

                        const processBtn = document.getElementById('processBtn');

                        const fileInfo = document.getElementById('fileInfo');

                        

                        if (typeof debugLog === 'function') {

                            debugLog(`🔒 Applying lock for submission status: ${submission.status}`, 'lock');

                            debugLog(`📅 Submission timestamp: ${new Date(submission.submission_timestamp).toLocaleString()}`, 'info');

                            if (submission.review_notes) {

                                debugLog(`📝 Review notes: ${submission.review_notes}`, 'info');

                            }

                        }

                        

                        if (uploadBox) {

                            if (typeof debugLog === 'function') {

                                debugLog('🔧 Modifying upload box HTML to show locked state', 'lock');

                            }

                            

                            uploadBox.innerHTML = `

                                <div class="locked-message">

                                    <div class="locked-icon">🔒</div>

                                    <h3>File Under Review</h3>

                                    <p>This balance sheet has been submitted for review and cannot be edited.</p>

                                    <div class="status-info">

                                        <strong>Status:</strong> ${submission.status}<br>

                                        <strong>Submitted:</strong> ${new Date(submission.submission_timestamp).toLocaleString()}<br>

                                        ${submission.review_notes ? `<strong>Notes:</strong> ${submission.review_notes}` : ''}

                                    </div>

                                    <div class="locked-actions">

                                        <button onclick="window.location.href='/dashboard'" class="btn btn-primary">

                                            Back to Dashboard

                                        </button>

                                        <button onclick="clearUploadLock()" class="btn btn-secondary">

                                            Upload New Balance Sheet

                                        </button>

                                    </div>

                                </div>

                            `;

                            

                            if (typeof debugLog === 'function') {

                                debugLog('🚫 Applying pointer-events: none and opacity: 0.7 to upload box', 'lock');

                            }

                            

                            uploadBox.classList.add('upload-locked');

                        }

                        

                        if (processBtn) {

                            if (typeof debugLog === 'function') {

                                debugLog('🔒 Disabling process button and setting text', 'lock');

                            }

                            processBtn.disabled = true;

                            processBtn.textContent = 'Locked - Under Review';

                        }

                        

                        if (fileInfo) {

                            if (typeof debugLog === 'function') {

                                debugLog('🔒 Setting file info opacity to 0.7', 'lock');

                            }

                            fileInfo.classList.add('file-info-locked');

                        }

                        

                        // File is locked due to submission status

                        if (typeof debugLog === 'function') {

                            debugLog('✅ Lock application complete - returning true (file is locked)', 'lock');

                        }

                        return true; // File is locked

                    }

                }

            }

        } else {

            if (typeof debugLog === 'function') {

                debugLog('✅ No session ID in URL - allowing new uploads even with pending submissions', 'success');

            }

        }

    } catch (error) {

        if (typeof debugLog === 'function') {

            debugLog(`❌ Error checking submission status: ${error.message}`, 'error');

        }

    }

    

    if (typeof debugLog === 'function') {

        debugLog('✅ Submission status check complete - returning false (file is not locked)', 'success');

    }

    return false; // File is not locked

}



// Clear upload lock and reset interface

async function clearUploadLock() {

    

    // Add debug logging if available

    if (typeof debugLog === 'function') {

        debugLog('🔓 User requested to clear upload lock', 'lock');

    }

    

    try {

        // Session storage cleared - using Supabase for state management

        

        // Clear URL parameters

        const url = new URL(window.location);

        url.searchParams.delete('session_id');

        window.history.replaceState({}, '', url);

        

        if (typeof debugLog === 'function') {

            debugLog('🗑️ Cleared local session data', 'info');

        }

        

        // Try to clear server-side submission data

        const response = await fetch('/api/clear-submission-lock', {

            method: 'POST',

            headers: {

                'Content-Type': 'application/json'

            }

        });

        

        if (response.ok) {

            const result = await response.json();

            if (typeof debugLog === 'function') {

                debugLog(`✅ Server-side response: ${result.message}`, 'success');

                if (result.restriction_applied) {

                    debugLog('🚫 Upload restriction was applied', 'warning');

                }

            }

        } else {

            const errorData = await response.json();

            if (typeof debugLog === 'function') {

                debugLog(`🚫 RESTRICTION: ${errorData.error}`, 'error');

                if (errorData.restriction_type === 'pending_reviews') {

                    debugLog(`📊 Pending submissions from other users: ${errorData.pending_count || 'unknown'}`, 'warning');

                }

            }

            

            // Show restriction message to user

            alert(`Upload Restriction: ${errorData.error}`);

            return; // Don't proceed with page reload

        }

    } catch (error) {

        if (typeof debugLog === 'function') {

            debugLog(`❌ Error clearing server-side lock: ${error.message}`, 'error');

        }

    }

    

    // Reload the page to reset the interface

    if (typeof debugLog === 'function') {

        debugLog('🔄 Reloading page to reset interface', 'info');

    }

    window.location.reload();

}



// Initialize upload service when DOM is ready



document.addEventListener('DOMContentLoaded', async () => {

    

    // Add debug logging if available

    if (typeof debugLog === 'function') {

        debugLog('🚀 DOM loaded, checking submission status...', 'info');

    }

    

    // Check if file is locked before initializing

    const isLocked = await checkSubmissionStatus();

    

    if (typeof debugLog === 'function') {

        debugLog(`🔒 Submission status check result: ${isLocked ? 'LOCKED' : 'UNLOCKED'}`, isLocked ? 'lock' : 'success');

    }

    

    if (!isLocked) {

        window.uploadService = new UploadService();

        if (typeof debugLog === 'function') {

            debugLog('✅ UploadService initialized successfully', 'success');

        }

    } else {

        if (typeof debugLog === 'function') {

            debugLog('⏸️ UploadService initialization skipped due to lock', 'lock');

        }

    }



});







// Handle page unload for cleanup



window.addEventListener('beforeunload', () => {



    if (window.uploadService) {



        window.uploadService.destroy();



    }



});



