# Finance Clerk Workflow Documentation

## Overview

The SADPMR Financial Reporting System provides a comprehensive workflow designed specifically for South African finance clerks to process trial balances and generate GRAP-compliant financial statements. This workflow ensures accuracy, compliance, and proper audit trails throughout the financial reporting process.

## Primary User: Finance Clerk (The "Engine Room")

**Role**: Finance Clerk  
**Primary Goal**: Accurate data entry and mapping  
**Key Responsibilities**: 
- Upload and validate trial balances
- Map accounts to GRAP categories
- Submit completed work for management review
- Maintain data integrity and compliance

---

## Workflow Steps

### Step 1: Dashboard - Task List Overview

**Purpose**: Upon login, the finance clerk sees their current workload and open periods.

**Location**: `/dashboard`

**Key Features**:
- **Open Periods Display**: Shows which financial periods are available for trial balance uploads
- **Task List**: Visual cards displaying each period with status indicators
- **Progress Tracking**: Shows upload progress and due dates for each period
- **Quick Actions**: Direct access to upload files for open periods

**Interface Elements**:
```
Task List - Open Periods
├── Period Cards
│   ├── Period Name (e.g., "March 2026")
│   ├── Status Badge (Open/Closed/Urgent)
│   ├── Upload Progress (X/Y files uploaded)
│   ├── Due Date (with urgency indicators)
│   └── Action Buttons
│       ├── "Upload Trial Balance" (if open)
│       └── "View Reports" (if files exist)
└── Filters
    ├── Status Filter (All/Open/Closed)
    └── Urgency Filter (All/Normal/Urgent)
```

**User Actions**:
1. Log in to the system
2. Review the task list to see open periods
3. Identify urgent periods (highlighted in red)
4. Click "Upload Trial Balance" to begin work on an open period

---

### Step 2: Upload Module - Trial Balance Processing

**Purpose**: Import and validate trial balance files with automatic balance checking.

**Location**: `/upload`

**Key Features**:
- **Drag & Drop Interface**: Intuitive file upload with visual feedback
- **Format Support**: Excel (.xlsx, .xls, .xlsm, .xlsb) and CSV (.csv, .tsv)
- **Real-time Validation**: Instant file format and structure validation
- **Balance Check**: Automatic verification that debits equal credits

**Interface Elements**:
```
Upload Trial Balance
├── Requirements Section
│   ├── Required columns: Account Code, Account Description, Balance
│   ├── File formats: Excel, CSV
│   ├── Max file size: 16MB
│   └── Balance requirement: Must be balanced
├── Upload Box
│   ├── Drag & Drop Area
│   ├── Click to browse option
│   └── File input (hidden)
└── File Information Panel
    ├── Selected file details
    ├── Balance Check Results
    │   ├── Total Debits
    │   ├── Total Credits
    │   ├── Difference
    │   └── Status Indicator (✅ Balanced / ❌ Not Balanced)
    └── Process Button
```

**Balance Check Logic**:
```javascript
if (balanceData.is_balanced) {
    // Enable submit button
    processBtn.disabled = false;
    processBtn.textContent = 'Submit for Review';
    balanceDifference.classList.add('highlight-green');
} else {
    // Disable submit button and show red discrepancy
    processBtn.disabled = true;
    processBtn.textContent = 'Trial Balance Not Balanced - Cannot Process';
    balanceDifference.classList.add('highlight-red');
}
```

**User Actions**:
1. Drag and drop trial balance file or click to browse
2. System validates file format and structure
3. Automatic balance check performs:
   - Calculates total debits and credits
   - Shows difference amount
   - Highlights discrepancy in red if not balanced
4. **Submit button remains disabled** if debits ≠ credits
5. User must correct trial balance and re-upload if not balanced
6. Once balanced, click "Process Trial Balance" to continue

---

### Step 3: Mapping Interface - GRAP Categorization

**Purpose**: Map trial balance accounts to appropriate GRAP (Generally Recognised Accounting Practice) categories.

**Location**: `/mapping`

**Key Features**:
- **Unmapped Accounts List**: Clear display of accounts requiring categorization
- **GRAP Categories**: Organized target categories following South African standards
- **Drag & Drop Mapping**: Intuitive drag-and-drop interface for account assignment
- **Progress Tracking**: Real-time completion percentage and statistics
- **Auto-mapping Support**: AI-powered suggestions with confidence scores

**Interface Elements**:
```
GRAP Account Mapping
├── Unmapped Accounts Section
│   ├── Account Count (e.g., "15 accounts")
│   ├── Account List
│   │   ├── Account Code
│   │   ├── Account Description
│   │   └── Balance Amount
│   └── Search/Filter Options
├── GRAP Categories Section
│   ├── Category Count (e.g., "45 categories")
│   ├── Category Grid
│   │   ├── Assets Categories
│   │   ├── Liabilities Categories
│   │   ├── Revenue Categories
│   │   └── Expense Categories
│   └── Drop Zones with visual feedback
├── Progress Section
│   ├── Total Accounts: 50
│   ├── Mapped: 35
│   ├── Remaining: 15
│   └── Completion: 70%
└── Review Status
    ├── Mapping Quality Indicators
    ├── Confidence Scores
    └── Submit for Review Button
```

**Mapping Process**:
1. **Auto-mapping**: System automatically maps obvious accounts with high confidence
2. **Manual Mapping**: Finance clerk drags remaining unmapped accounts:
   - Drag account from "Unmapped Accounts" list
   - Drop into appropriate GRAP category
   - System validates mapping compatibility
3. **Progress Updates**: Real-time statistics update as accounts are mapped
4. **Quality Check**: System reviews mapping completeness and accuracy

**User Actions**:
1. Review auto-mapped accounts (shown with confidence scores)
2. Drag unmapped accounts to correct GRAP categories
3. Use search/filter to find specific accounts
4. Monitor progress until 100% completion
5. Review mapping summary and confidence indicators
6. Click "Submit Mapping & Continue" when complete

---

### Step 4: Submission - Review and Approval Workflow

**Purpose**: Submit completed mapping for management review and track approval status.

**Location**: `/submission-workflow`

**Key Features**:
- **Comprehensive Review**: Complete summary of trial balance and mapping
- **Status Management**: Clear workflow status tracking
- **Approval Timeline**: Visual timeline of the approval process
- **Edit Control**: Proper access control based on submission status

**Interface Elements**:
```
Submit for Review
├── File Status Section
│   ├── Status Badge (Draft/Submitted/Approved/Rejected)
│   ├── Summary Statistics
│   │   ├── Total Accounts: 50
│   │   ├── Mapped Accounts: 50
│   │   ├── Total Assets: R 5,250,000.00
│   │   └── Total Liabilities: R 2,100,000.00
│   └── File Details
│       ├── File Name, Upload Date, Period
│       └── Prepared By: [Finance Clerk Name]
├── Mapping Summary Section
│   ├── Mapping Completeness: 100%
│   ├── GRAP Categories Used: 23
│   └── Quality Indicators
├── Approval Timeline
│   ├── ✅ File Uploaded [Date]
│   ├── ✅ Mapping Complete [Date]
│   ├── ⏳ Current Status: Ready for Submission
│   └── [Future] Pending Review → Approved/Rejected
└── Action Buttons
    ├── "✓ Submit for Review" (if draft and complete)
    ├── "⏳ Pending Review" (if submitted - disabled)
    ├── "✓ Approved" (if approved - disabled)
    └── "🔄 Resubmit" (if rejected)
```

**Status Management Logic**:

| Status | Description | User Actions Available |
|--------|-------------|-----------------------|
| **Draft** | Initial state, can be edited | Submit, Edit Mapping, Delete |
| **Submitted** | Pending manager review | Withdraw Submission Only |
| **Approved** | Manager approved | Generate Final Report |
| **Rejected** | Manager rejected | Resubmit After Corrections |

**User Actions**:
1. Review comprehensive summary of trial balance and mapping
2. Verify all accounts are properly mapped (100% completion required)
3. Click "Submit for Review" to send to management
4. **Status changes to "Pending"** - clerk can no longer edit
5. Monitor approval status in dashboard
6. If rejected, receive feedback and make corrections
7. Once approved, generate final financial statements

---

## Backend API Support

### Core API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/upload` | POST | Handle trial balance file upload |
| `/api/validate-balance` | POST | Real-time balance validation |
| `/api/processing` | POST | Process uploaded files |
| `/api/save-mapping-progress` | POST | Save mapping data |
| `/api/submit-for-review` | POST | Submit for manager review |
| `/api/submission-status/<id>` | GET | Check submission status |

### Key Business Logic

1. **Balance Validation**: Enforces debits = credits before processing
2. **Submit Button Control**: Frontend and backend validation of requirements
3. **Status Management**: Complete workflow state tracking in Supabase
4. **Access Control**: Role-based permissions for different actions
5. **Audit Trail**: Complete logging of all user actions

---

## Error Handling and Validation

### File Upload Validation
- **Format Check**: Only Excel and CSV files allowed
- **Size Limit**: Maximum 16MB file size
- **Structure Validation**: Required columns must be present
- **Content Validation**: Must be trial balance, not financial analysis

### Balance Check Validation
- **Real-time Validation**: Instant feedback during upload
- **Precision Handling**: Proper decimal precision for financial amounts
- **Error Messaging**: Clear indication of balance discrepancies
- **Submit Control**: Prevents processing unbalanced trial balances

### Mapping Validation
- **Category Compatibility**: Validates account-category relationships
- **Completeness Check**: Ensures all accounts are mapped
- **Confidence Scoring**: AI-powered mapping quality assessment
- **Duplicate Prevention**: Prevents multiple mappings of same account

---

## Security and Compliance

### Access Control
- **Role-Based Authentication**: Finance clerk role with specific permissions
- **Session Management**: Secure user sessions with timeout
- **Permission Validation**: Server-side permission checks for all actions

### Data Protection
- **Secure Upload**: Encrypted file transfer and storage
- **Data Validation**: Input sanitization and validation
- **Audit Logging**: Complete audit trail of all user actions

### GRAP Compliance
- **South African Standards**: Compliance with ASB GRAP standards
- **Category Mapping**: Proper GRAP category structure
- **Audit Requirements**: Audit-ready financial statements

---

## Mobile and Accessibility Support

### Responsive Design
- **Mobile-First**: Optimized for mobile devices
- **Touch-Friendly**: 44x44px minimum touch targets
- **Fluid Scaling**: Adapts to all screen sizes
- **Cross-Browser**: Works on all modern browsers

### Accessibility Features
- **WCAG 2.1 AA**: Full accessibility compliance
- **Screen Reader**: Proper ARIA labels and semantic HTML
- **Keyboard Navigation**: Complete keyboard support
- **High Contrast**: Enhanced visibility options

---

## Integration Points

### Database Integration
- **Supabase Backend**: Modern PostgreSQL database
- **Real-time Updates**: Live status synchronization
- **Data Persistence**: Reliable data storage
- **Backup Systems**: Automated backup and recovery

### File Storage
- **Cloud Storage**: Secure file storage system
- **Version Control**: File version tracking
- **Access Control**: Secure file access management
- **Retention Policies**: Automated file cleanup

---

## Performance and Scalability

### Optimization Features
- **Lazy Loading**: Progressive content loading
- **Caching**: Intelligent caching strategies
- **Compression**: File and data compression
- **CDN Integration**: Fast content delivery

### Scalability Considerations
- **Load Balancing**: Distributed processing
- **Database Optimization**: Efficient query design
- **Memory Management**: Optimized resource usage
- **Background Processing**: Asynchronous task handling

---

## Training and Support

### User Guidance
- **On-Screen Instructions**: Clear step-by-step guidance
- **Error Messages**: Helpful error descriptions
- **Progress Indicators**: Visual feedback for long processes
- **Help Documentation**: Comprehensive user guides

### Support Features
- **Error Reporting**: Automatic error logging
- **User Feedback**: Feedback collection system
- **Help Desk**: Integrated support system
- **Training Materials**: User training resources

---

## Conclusion

The SADPMR Financial Reporting System provides a complete, professional workflow for South African finance clerks that ensures:

✅ **Accuracy**: Balance validation and mapping verification  
✅ **Compliance**: GRAP standards adherence  
✅ **Efficiency**: Streamlined workflow processes  
✅ **Security**: Role-based access control  
✅ **Audit Trail**: Complete activity logging  
✅ **User Experience**: Intuitive, responsive interface  

The workflow transforms the complex process of trial balance processing into a manageable, error-free operation that meets South African municipal financial reporting requirements while maintaining the highest standards of data integrity and compliance.

---

*Last Updated: May 2026*  
*Version: 1.0*  
*System: SADPMR Financial Reporting System*
