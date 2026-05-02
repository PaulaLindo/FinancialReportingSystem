# SADPMR Financial Reporting System

## GRAP-Compliant Financial Statement Generation & Automation

---

## 🎯 Quick Start

Complete financial reporting system for SADPMR with automated GRAP mapping and PDF generation.

### Prerequisites

- Python 3.8+
- Modern web browser
- Excel/CSV trial balance files

### Installation

1. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Start the application**
   ```bash
   python run.py
   ```

3. **Access the web interface**
   - Open: `http://localhost:5000`
   - Upload trial balance and generate GRAP-compliant statements

---

## 📁 Project Structure

```
FinancialReportingSystem/
├── app.py                      # Main application entry point
├── run.py                      # Development server runner
├── requirements.txt            # Python dependencies
├── config/                     # Application configuration
│   ├── __init__.py            # Config package init
│   └── settings.py            # Environment settings
├── controllers/                # Route handlers and API endpoints
│   ├── __init__.py            # Controllers package init
│   └── routes.py              # Flask routes and views
├── models/                     # Data models and business logic
│   ├── __init__.py            # Models package init
│   └── grap_models.py         # GRAP mapping engine
├── utils/                      # Helper functions and utilities
│   ├── __init__.py            # Utils package init
│   ├── validators.py          # Data validation functions
│   └── helpers.py             # Utility functions
├── static/                     # CSS and JavaScript
│   ├── css/style.css          # Professional styling
│   └── js/                    # Frontend functionality
├── templates/                  # HTML templates
│   ├── index.html             # Dashboard
│   ├── upload.html            # File upload interface
│   └── about.html             # System information
├── docs/                       # Static demo files (deprecated)
│   ├── index.html             # Marketing landing page
│   ├── css/style.css          # Demo styling
│   └── js/main.js             # Interactive features
│   └── README.md              # Demo documentation
├── uploads/                    # Uploaded trial balances
└── outputs/                    # Generated PDF reports
```

---

## 🚀 Core Features

### 📊 **Automated GRAP Mapping**
- **Zero Manual Intervention**: Complete automation from trial balance to GRAP statements
- **Intelligent Account Recognition**: Maps Pastel/Excel accounts to GRAP line items
- **Validation & Error Checking**: Identifies unmapped accounts automatically

### 📈 **Financial Statement Generation**
- **Statement of Financial Position**: GRAP-compliant balance sheet
- **Statement of Financial Performance**: Income statement with surplus/deficit
- **Cash Flow Statement**: Automated indirect method calculation
- **Financial Ratios**: Current ratio, debt-to-equity, operating margin, ROA

### 📄 **Professional PDF Reports**
- **SADPMR Branded Templates**: Official formatting and styling
- **GRAP Standards Compliance**: Proper line item classification
- **Color-Coded Statements**: Visual distinction between statement sections
- **Benchmark Comparisons**: Industry standard ratio benchmarks

---

## 🔧 Technical Architecture

### **Backend Stack**
- **Flask**: Lightweight web framework
- **Pandas**: Data processing and analysis
- **ReportLab**: Professional PDF generation
- **OpenPyXL**: Excel file processing

### **Frontend Stack**
- **Modern HTML5/CSS3**: Responsive design
- **Vanilla JavaScript**: Interactive file upload
- **Professional UI**: SADPMR branding and styling

### **Data Flow**
1. **Upload**: Trial balance (Excel/CSV) → Server
2. **Process**: Account mapping → GRAP classification
3. **Generate**: Financial statements → PDF report
4. **Download**: Professional GRAP-compliant report

---

## 📋 Usage Instructions

### Step 1: Upload Trial Balance
1. Navigate to `/upload`
2. Select Excel or CSV trial balance file
3. System validates and processes the file

### Step 2: Review Mapping
1. System automatically maps accounts to GRAP codes
2. Review any unmapped accounts (if present)
3. Confirm mapping accuracy

### Step 3: Generate Statements
1. Click "Generate Financial Statements"
2. System processes and creates GRAP-compliant statements
3. Review generated statements on screen

### Step 4: Download Report
1. Click "Download PDF Report"
2. Receive professional SADPMR-branded financial statements
3. Ready for submission and review

---

## 🎯 Key Differentiators

### **Zero Manual Mapping**
- Traditional systems: 40+ hours manual account mapping
- Our system: 5 minutes complete automation

### **GRAP Compliance Built-In**
- Automatic line item classification
- Proper statement formatting
- Audit trail compliance

### **Professional Output**
- SADPMR official templates
- Color-coded financial statements
- Industry benchmark comparisons

---

## 🔒 Compliance & Security

### **GRAP Standards**
- Full compliance with GRAP accounting standards
- Proper line item classification
- Standard financial statement format

### **Data Security**
- Local processing only
- No external data transmission
- Secure file handling

### **Audit Trail**
- Complete processing log
- Error tracking and reporting
- Version control support

---

## 📞 Support & Documentation

### **Technical Support**
- System requirements and setup
- Troubleshooting common issues
- Performance optimization tips

### **User Documentation**
- Step-by-step usage guides
- Video tutorials (coming soon)
- FAQ and best practices

---

## 🚀 Future Development

### **Phase 3 Enhancements**
- Multi-user support and role-based access
- Advanced ratio analysis dashboard
- Budget vs actual comparisons
- Automated audit preparation

### **Phase 4 Features**
- Real-time collaboration
- Cloud deployment options
- API integration capabilities
- Advanced reporting analytics

---

## 📄 License & Copyright

© 2026 South African Diamond and Precious Metals Regulator (SADPMR)
All rights reserved.

---

**Transform your financial reporting with automated GRAP compliance and professional statement generation.**
