# Flexible Trial Balance System

## Overview

The SADPMR Financial Reporting System now features a **completely flexible trial balance processing system** that can handle **any kind of trial balance format** while maintaining full GRAP compliance and audit capabilities.

## 🎯 Key Features

### **Universal Format Support**
- **Excel Files** (.xlsx, .xls) with automatic engine detection
- **CSV Files** with multiple encoding support (UTF-8, Latin1, CP1252)
- **Any Column Structure** - automatic detection and mapping
- **Multi-Period Support** - handle monthly, quarterly, annual data
- **Custom Formats** - adapt to any organization's trial balance layout

### **Intelligent Processing**
- **Automatic Column Detection** using pattern recognition
- **Smart Data Type Recognition** (account codes, descriptions, amounts)
- **Structure Analysis** - identifies standard, hospital, government, custom formats
- **Quality Scoring** - evaluates data quality and completeness
- **Flexible Mapping** - adapts to any naming convention

### **GRAP Compliance**
- **Complete GRAP Chart of Accounts** with 40+ standard accounts
- **Auto-Mapping Engine** with confidence scoring
- **Category Classification** (Assets, Liabilities, Equity, Revenue, Expenses)
- **Subcategory Organization** for detailed reporting
- **Validation Rules** ensuring GRAP compliance

### **Database Architecture**
- **Flexible Schema** handles any trial balance structure
- **Version Control** track all changes and iterations
- **Audit Trail** complete history of all modifications
- **Multi-User Support** concurrent access without conflicts
- **Performance Optimized** efficient queries and indexing

## 🏗️ Architecture

### **Database Schema**

```
trial_balance_sessions
├── Core session data (user, file, status, timestamps)
├── Metadata (detected patterns, quality scores)
└── Processing logs (detailed history)

trial_balance_columns
├── Dynamic column definitions
├── Type classification (account_code, debit, credit, etc.)
├── Mapping rules and confidence scores
└── Validation rules

trial_balance_data
├── Raw data (preserved original format)
├── Processed data (cleaned and standardized)
├── Standard fields (account_code, description, balances)
├── Multi-period support (12 periods)
└── GRAP mapping (category, account, confidence)

mapping_rules
├── User-defined and system rules
├── Pattern matching (regex, exact, contains, fuzzy)
├── Confidence scoring and usage statistics
└── Priority-based application

grap_chart_of_accounts
├── Complete GRAP chart of accounts
├── Keywords and alternative names
├── Mapping patterns for auto-detection
└── Account type and normal balance

processing_history
├── Complete audit trail
├── Before/after states
├── Error tracking and recovery
└── Performance metrics
```

### **Service Layer**

```
FlexibleTrialBalanceService
├── File Processing (Excel, CSV, multiple encodings)
├── Structure Detection (pattern recognition)
├── Column Classification (automatic type detection)
├── Data Processing (cleaning and standardization)
├── Auto-Mapping (GRAP account matching)
└── Quality Assessment (scoring and validation)
```

## 🚀 Quick Start

### **1. Database Setup**

```bash
# Run the database setup script
python scripts/setup_database.py
```

This will:
- Create all database tables
- Seed GRAP chart of accounts
- Configure mapping rules
- Set up Row Level Security

### **2. Upload Your First Trial Balance**

```python
# Using the service directly
from services.flexible_trial_balance_service import flexible_trial_balance_service

result = flexible_trial_balance_service.process_upload(
    file_path="path/to/your/trial_balance.xlsx",
    user_id="your_user_id",
    filename="trial_balance.xlsx"
)

if result['success']:
    print(f"Processed {result['total_rows']} rows")
    print(f"Detected format: {result['structure_info']['file_type']}")
    print(f"Quality score: {result['structure_info']['quality_score']}")
    print(f"Auto-mapped: {result['mapping_results']['auto_mapped']} accounts")
```

### **3. API Upload**

```javascript
// Upload via API
const formData = new FormData();
formData.append('file', trialBalanceFile);

fetch('/api/upload', {
    method: 'POST',
    body: formData,
    headers: {
        'Authorization': 'Bearer ' + authToken
    }
})
.then(response => response.json())
.then(data => {
    if (data.success) {
        console.log('Upload successful:', data.session_id);
        console.log('Detected format:', data.detected_file_type);
        console.log('Quality score:', data.data_quality_score);
    }
});
```

## 📊 Supported Formats

### **Standard Trial Balance**
```
Account Code | Account Description        | Debit Balance | Credit Balance
------------|---------------------------|---------------|----------------
1100        | Cash and Bank Accounts     | 100,000.00    | -
1200        | Trade Receivables          | 50,000.00     | -
2100        | Property, Plant & Equipment| 200,000.00    | -
4100        | Trade Payables             | -             | 30,000.00
5100        | Share Capital              | -             | 320,000.00
```

### **Multi-Period Format**
```
Account Code | Account Description | Jan 2024 | Feb 2024 | Mar 2024 | Total
------------|-------------------|----------|----------|----------|-------
1100        | Cash              | 100,000  | 95,000   | 105,000  | 300,000
1200        | Receivables       | 50,000   | 55,000   | 45,000   | 150,000
```

### **Hospital Department Format**
`` | Department | Account | Jan | Feb | Mar | Apr | May | Jun |
 |-----------|---------|-----|-----|-----|-----|-----|-----|
 | Nursing   | Salaries| 50k | 52k | 51k | 53k | 54k | 55k |
 | Pharmacy  | Drugs   | 20k | 18k | 22k | 19k | 21k | 23k |
```

### **Custom Formats**
The system can adapt to ANY format by:
- Automatic column detection
- Pattern recognition
- User-defined mapping rules
- Machine learning-based classification

## 🎛️ Configuration

### **Column Detection Patterns**

```python
# Default patterns (can be extended)
column_patterns = {
    'account_code': [
        r'(?i)account\s*code',
        r'(?i)acc\s*code',
        r'(?i)code',
        r'(?i)account\s*no'
    ],
    'account_description': [
        r'(?i)account\s*desc',
        r'(?i)description',
        r'(?i)account\s*name'
    ],
    'debit_balance': [
        r'(?i)debit',
        r'(?i)dr',
        r'(?i)debit\s*balance'
    ],
    'credit_balance': [
        r'(?i)credit',
        r'(?i)cr',
        r'(?i)credit\s*balance'
    ]
}
```

### **Custom Mapping Rules**

```python
# Add custom mapping rules
from models.trial_balance_models import MappingRule

custom_rule = MappingRule(
    user_id="your_user_id",
    rule_name="Custom Bank Account Mapping",
    rule_type="account_mapping",
    pattern_type="contains",
    input_pattern="bank",
    output_value="Cash and Cash Equivalents",
    confidence_score=0.9,
    priority=80
)

rule_id = trial_balance_model.create_mapping_rule(custom_rule)
```

## 📈 Quality Assessment

### **Quality Score Calculation**

The system calculates a quality score (0.0 - 1.0) based on:

```
Base Components:
- Has headers: +0.2
- Has account codes: +0.2
- Has descriptions: +0.2
- Has numeric data: +0.2
- Has debit/credit: +0.1
- Has multi-period: +0.1
```

### **Quality Levels**

- **0.8 - 1.0**: Excellent - Ready for immediate processing
- **0.6 - 0.8**: Good - Minor mapping adjustments needed
- **0.4 - 0.6**: Fair - Some manual mapping required
- **0.0 - 0.4**: Poor - Significant manual intervention needed

## 🔍 Auto-Mapping

### **Mapping Algorithm**

```python
def calculate_match_confidence(row, grap_account):
    confidence = 0.0
    
    # Exact account code match: +0.9
    if row.account_code == grap_account.grap_account_code:
        confidence += 0.9
    
    # Account code contains match: +0.7
    if grap_account.grap_account_code in row.account_code:
        confidence += 0.7
    
    # Exact description match: +0.8
    if row.account_description == grap_account.account_description:
        confidence += 0.8
    
    # Description contains match: +0.6
    if grap_account.account_description in row.account_description:
        confidence += 0.6
    
    # Keyword matching: +0.3 per keyword
    for keyword in grap_account.keywords:
        if keyword in row.account_description:
            confidence += 0.3
    
    return min(confidence, 1.0)
```

### **Mapping Results**

```json
{
    "mapping_results": {
        "total_rows": 150,
        "auto_mapped": 120,
        "manual_review_needed": 30,
        "mapping_confidence": 0.85
    }
}
```

## 🛠️ Advanced Features

### **Multi-Period Processing**

```python
# Support for up to 12 periods
period_fields = [
    'period_1', 'period_2', 'period_3', 'period_4',
    'period_5', 'period_6', 'period_7', 'period_8',
    'period_9', 'period_10', 'period_11', 'period_12'
]
```

### **Version Control**

```python
# Track changes over time
processing_history = trial_balance_model.get_processing_history(session_id)

# Each change creates a new version
# Before/after states preserved
# Complete audit trail maintained
```

### **Template System**

```python
# Save frequently used formats as templates
from models.trial_balance_models import TrialBalanceTemplate

template = TrialBalanceTemplate(
    user_id="your_user_id",
    template_name="Standard Hospital Format",
    file_type="excel",
    column_mappings={
        "Department": "account_description",
        "Account": "account_code",
        "Jan": "period_1",
        "Feb": "period_2"
    }
)
```

## 🔧 Maintenance

### **Database Functions**

```sql
-- Get trial balance summary
SELECT get_trial_balance_summary('session_id');

-- Common queries
SELECT * FROM trial_balance_sessions WHERE user_id = 'user_id';
SELECT * FROM trial_balance_data WHERE session_id = 'session_id';
SELECT * FROM grap_chart_of_accounts WHERE grap_category = 'ASSETS';
```

### **Performance Optimization**

- **Indexed columns** for fast queries
- **Row Level Security** for multi-tenant isolation
- **Connection pooling** for concurrent access
- **Caching** for frequently accessed data

## 🚨 Error Handling

### **Common Issues**

1. **File Format Not Supported**
   - Ensure file is .xlsx, .xls, or .csv
   - Check file encoding for CSV files

2. **No Data Detected**
   - Verify file has data rows
   - Check for hidden sheets in Excel

3. **Low Quality Score**
   - Review column headers
   - Check for missing required columns
   - Consider manual mapping

4. **Mapping Failures**
   - Review mapping rules
   - Add custom patterns
   - Update GRAP accounts

### **Debug Mode**

```python
# Enable detailed logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Get detailed processing information
session_summary = flexible_trial_balance_service.get_session_summary(session_id)
print(json.dumps(session_summary, indent=2))
```

## 📚 API Reference

### **FlexibleTrialBalanceService**

```python
class FlexibleTrialBalanceService:
    def process_upload(self, file_path, user_id, filename)
    def get_session_summary(self, session_id)
    def _detect_structure(self, df)
    def _perform_auto_mapping(self, session_id, data_rows)
```

### **TrialBalanceModel**

```python
class TrialBalanceModel:
    def create_session(self, session)
    def get_session(self, session_id)
    def create_data_rows(self, rows)
    def get_grap_accounts(self, category=None)
    def create_mapping_rule(self, rule)
```

## 🎯 Best Practices

### **File Preparation**
1. Use consistent column headers
2. Include account codes when possible
3. Clean data before upload
4. Use standard date formats

### **Mapping Rules**
1. Start with system rules
2. Add organization-specific rules
3. Test with sample data
4. Monitor confidence scores

### **Quality Assurance**
1. Review quality scores
2. Validate auto-mapped accounts
3. Check balance totals
4. Verify GRAP compliance

## 🔄 Future Enhancements

- **Machine Learning** for improved auto-mapping
- **Advanced Validation** rules
- **Real-time Processing** for large files
- **Integration APIs** for external systems
- **Mobile App** for on-the-go uploads
- **Advanced Analytics** and reporting

## 📞 Support

For technical support:
1. Check the error logs
2. Review this documentation
3. Test with sample files
4. Contact the development team

---

**The Flexible Trial Balance System** - Handle any format, ensure compliance, maintain audit trails. 🏛️
