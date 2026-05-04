# Multi-Document System Testing Guide

## Test Files Created

I've created sample test files for both budget reports and income statements to test the new multi-document system.

## 📊 Budget Reports

### 1. Balanced Budget Report
**Files:**
- `financial_documents/budget_reports/budget_report_balanced_excel.xlsx`
- `financial_documents/budget_reports/budget_report_balanced_proper.csv`

**Characteristics:**
- Total Budget: R 1,500,000
- Total Actual: R 1,485,000
- Variance: -R 15,000 (-1.0%)
- **Status: Under Budget** ✅

**Key Features:**
- 20 departments with realistic budget data
- Mixed positive and negative variances
- Departmental categorization (Finance, Marketing, Operations, etc.)
- Percentage variance calculations

### 2. Unbalanced Budget Report
**Files:**
- `financial_documents/budget_reports/budget_report_unbalanced_excel.xlsx`
- `financial_documents/budget_reports/budget_report_unbalanced_proper.csv`

**Characteristics:**
- Total Budget: R 1,500,000
- Total Actual: R 1,595,000
- Variance: +R 95,000 (+6.3%)
- **Status: Over Budget** ⚠️

**Key Features:**
- Same departments as balanced version
- Higher actual expenses across most categories
- Significant overages in consulting and IT
- Multiple variance percentages above 10%

## 📈 Income Statements

### 1. Balanced Income Statement
**Files:**
- `financial_documents/income_statements/income_statement_balanced_excel.xlsx`
- `financial_documents/income_statements/income_statement_balanced_proper.csv`

**Characteristics:**
- Total Revenue: R 980,000
- Total Expenses: R 760,000
- Net Income: R 220,000
- **Status: Profitable** ✅

**Key Features:**
- 6 revenue streams (consulting, training, software, etc.)
- 12 expense categories (salaries, rent, utilities, etc.)
- Realistic profit margin (22.4%)
- Quarterly period (2025-Q1)

### 2. Unbalanced Income Statement
**Files:**
- `financial_documents/income_statements/income_statement_unbalanced_excel.xlsx`
- `financial_documents/income_statements/income_statement_unbalanced_proper.csv`

**Characteristics:**
- Total Revenue: R 980,000
- Total Expenses: R 1,015,000
- Net Loss: -R 35,000
- **Status: Loss** ❌

**Key Features:**
- Same revenue as balanced version
- Higher expenses across all categories
- 22% increase in total expenses
- Net loss situation

## 🧪 Testing Scenarios

### Scenario 1: Budget Report Testing
1. **Upload Balanced Budget**
   - Select "Budget Report" document type
   - Upload `budget_report_balanced.xlsx` or `.csv`
   - Verify variance calculation: -1.0%
   - Check performance rating: "Excellent"

2. **Upload Unbalanced Budget**
   - Select "Budget Report" document type
   - Upload `budget_report_unbalanced.xlsx` or `.csv`
   - Verify variance calculation: +6.3%
   - Check performance rating: "Needs Attention"

### Scenario 2: Income Statement Testing
1. **Upload Balanced Income Statement**
   - Select "Income Statement" document type
   - Upload `income_statement_balanced.xlsx` or `.csv`
   - Verify net income: R 220,000
   - Check revenue vs expense categorization

2. **Upload Unbalanced Income Statement**
   - Select "Income Statement" document type
   - Upload `income_statement_unbalanced.xlsx` or `.csv`
   - Verify net loss: -R 35,000
   - Check loss identification and reporting

### Scenario 3: Format Detection Testing
1. **Excel Files (.xlsx)**
   - Test both balanced and unbalanced versions
   - Verify automatic column detection
   - Check data type recognition

2. **CSV Files (.csv)**
   - Test both balanced and unbalanced versions
   - Verify comma-separated parsing
   - Check proper data import

### Scenario 4: Workflow Testing
1. **Submission Process**
   - Upload any test file
   - Complete document processing
   - Submit for review
   - Verify status changes

2. **Approval Process**
   - Login as Finance Manager/CFO
   - Review submitted documents
   - Approve or reject with reasons
   - Check workflow history

## 🔍 Expected Results

### Budget Reports
- **Column Detection**: Account Code, Account Description, Department, Budget Amount, Actual Amount, Variance, Variance %
- **Variance Calculation**: (Actual - Budget) / Budget * 100
- **Performance Rating**: Based on variance percentage
- **Department Analysis**: Proper categorization

### Income Statements
- **Column Detection**: Account Code, Account Description, Category, Amount, Period
- **Revenue/Expense Classification**: Automatic categorization
- **Net Income Calculation**: Revenue - Expenses
- **Period Detection**: Quarterly (2025-Q1)

## 🚀 Testing Steps

### 1. Start the Application
```bash
python run.py
```

### 2. Access Upload Interface
- Navigate to `http://localhost:5000/upload`
- Select document type (Budget Report or Income Statement)

### 3. Upload Test Files
- Choose balanced version first
- Verify processing and validation
- Try unbalanced version
- Compare results

### 4. Test Workflow
- Submit documents for review
- Test approval/rejection process
- Check submission history

### 5. Verify Integration
- Check that existing balance sheets still work
- Test mixed document type submissions
- Verify universal workflow functionality

## 📋 Validation Checklist

### ✅ Budget Report Validation
- [ ] File uploads successfully
- [ ] Columns detected correctly
- [ ] Variance calculations accurate
- [ ] Performance ratings appropriate
- [ ] Department categorization works
- [ ] Both balanced/unbalanced handled

### ✅ Income Statement Validation
- [ ] File uploads successfully
- [ ] Revenue/expense classification works
- [ ] Net income/loss calculated correctly
- [ ] Period information extracted
- [ ] Both profitable/loss scenarios handled

### ✅ System Integration
- [ ] Document type selection works
- [ ] Dynamic requirements display
- [ ] Universal workflow processes all types
- [ ] Existing balance sheet functionality preserved
- [ ] Mixed document type submissions work

## 🐛 Troubleshooting

### Common Issues
1. **File Format Errors**: Ensure files are .xlsx or .csv format
2. **Column Detection**: Check that headers match expected patterns
3. **Validation Failures**: Verify data format and types
4. **Workflow Issues**: Check user permissions and roles

### Debug Information
- Check browser console for JavaScript errors
- Review server logs for processing errors
- Verify file format compatibility
- Test with both Excel and CSV versions

## 📊 Test Data Summary

| Document Type | Balanced | Unbalanced | File Formats |
|---------------|-----------|-------------|--------------|
| Budget Report | ✅ -1.0% variance | ⚠️ +6.3% variance | .xlsx, .csv |
| Income Statement | ✅ R 220,000 profit | ❌ R 35,000 loss | .xlsx, .csv |

These test files provide comprehensive coverage of the new multi-document system and will help validate all the implemented features! 🎯
