"""
Universal Financial Document Routes
Handles uploads for all financial document types (Balance Sheets, Income Statements, Budget Reports)
"""

from flask import jsonify, request, session
from functools import wraps
import os
import tempfile
from datetime import datetime

# Import authentication and permissions
from models.supabase_auth_models import get_current_user
from utils.constants import WorkflowErrorMessages

# Import document services
from services.financial_document_service import FinancialDocumentService
from services.income_statement_service import IncomeStatementService
from services.budget_report_service import BudgetReportService
from services.universal_workflow_service import UniversalWorkflowService

# Import existing balance sheet service for backward compatibility
from services.flexible_balance_sheet_service import FlexibleBalanceSheetService


def login_required(f):
    """Decorator to require login"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'success': False, 'error': 'Authentication required'}), 401
        return f(*args, **kwargs)
    return decorated_function


def permission_required(permission):
    """Decorator to require specific permission"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user = get_current_user()
            if not user or not user.has_permission(permission):
                return jsonify({'success': False, 'error': 'Insufficient permissions'}), 403
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def allowed_file(filename):
    """Check if file extension is allowed"""
    ALLOWED_EXTENSIONS = {'xlsx', 'xls', 'csv', 'xlsm', 'xlsb', 'tsv'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


class UniversalUploadHandler:
    """Universal handler for all financial document uploads"""
    
    def __init__(self):
        self.document_services = {
            'balance_sheet': FlexibleBalanceSheetService(),
            'income_statement': IncomeStatementService(),
            'budget_report': BudgetReportService()
        }
        self.workflow_service = UniversalWorkflowService()
    
    def get_service(self, document_type: str):
        """Get the appropriate service for a document type"""
        return self.document_services.get(document_type)
    
    def process_upload(self, document_type: str, file, user_id: str, **kwargs):
        """Process upload for any document type"""
        try:
            # Get the appropriate service
            service = self.get_service(document_type)
            if not service:
                return {
                    'success': False,
                    'error': f'Unsupported document type: {document_type}'
                }
            
            # Create temporary file for processing
            with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as temp_file:
                file.save(temp_file.name)
                temp_file_path = temp_file.name
            
            try:
                # Process the upload using the appropriate service
                result = service.process_upload(
                    file_path=temp_file_path,
                    user_id=user_id,
                    filename=file.filename,
                    **kwargs
                )
                
                return result
                
            finally:
                # Clean up temporary file
                try:
                    os.unlink(temp_file_path)
                except:
                    pass
                    
        except Exception as e:
            return {
                'success': False,
                'error': f'Error processing {document_type}: {str(e)}'
            }


# Create global upload handler
upload_handler = UniversalUploadHandler()


def register_universal_routes(app):
    """Register universal financial document routes"""
    
    def _infer_document_type_from_session(session_id):
        """Helper function to infer document type from session"""
        try:
            # Try balance sheet first
            from models.balance_sheet_models import BalanceSheetModel
            bs_model = BalanceSheetModel()
            if bs_model.get_session(session_id):
                return 'balance_sheet'
            
            # Try income statement
            from models.income_statement_models import IncomeStatementModel
            is_model = IncomeStatementModel()
            if is_model.get_session(session_id):
                return 'income_statement'
            
            # Try budget report
            from models.budget_report_models import BudgetReportModel
            br_model = BudgetReportModel()
            if br_model.get_session(session_id):
                return 'budget_report'
            
            return None
        except Exception as e:
            print(f"Error inferring document type: {e}")
            return None
    
    @app.route('/api/universal/upload', methods=['POST'])
    @login_required
    @permission_required('upload')
    def upload_financial_document():
        """
        Universal API endpoint to handle any financial document upload
        Supports: Balance Sheets, Income Statements, Budget Reports
        """
        try:
            print("🔄 Universal upload endpoint called")
            print(f"📁 Request files: {list(request.files.keys())}")
            print(f"📋 Request form: {dict(request.form)}")
            
            # Get document type from form data
            document_type = request.form.get('document_type', 'balance_sheet')
            print(f"📄 Document type: {document_type}")
            
            # Validate document type
            if document_type not in upload_handler.document_services:
                return jsonify({
                    'success': False,
                    'error': f'Unsupported document type: {document_type}'
                }), 400
            
            # Check if file is present
            if 'file' not in request.files:
                return jsonify({'success': False, 'error': 'No file uploaded'}), 400
            
            file = request.files['file']
            if file.filename == '':
                return jsonify({'success': False, 'error': 'No file selected'}), 400
            
            # Validate file type
            if not allowed_file(file.filename):
                return jsonify({
                    'success': False,
                    'error': 'File type not supported. Please use Excel (.xlsx, .xls) or CSV (.csv)'
                }), 400
            
            # Get current user
            current_user = get_current_user()
            if not current_user:
                return jsonify({'success': False, 'error': 'User not authenticated'}), 401
            
            print(f"👤 User authenticated: {current_user.username}")
            
            # Get additional parameters
            period_id = request.form.get('period_id')
            notes = request.form.get('notes', '')
            
            # Process the upload
            result = upload_handler.process_upload(
                document_type=document_type,
                file=file,
                user_id=current_user.id,
                period_id=period_id
            )
            
            if result['success']:
                print(f"✅ {document_type} uploaded successfully")
                print(f"📋 Session ID: {result['session_id']}")
                print(f"📊 Total rows: {result.get('total_rows', 0)}")
                print(f"📈 Total columns: {result.get('total_columns', 0)}")
                
                # Add document type to result
                result['document_type'] = document_type
                
                return jsonify(result)
            else:
                print(f"❌ Upload failed: {result.get('error', 'Unknown error')}")
                return jsonify(result), 400
                
        except Exception as e:
            print(f"💥 Unexpected error in universal upload: {str(e)}")
            return jsonify({
                'success': False,
                'error': f'Unexpected error during upload: {str(e)}'
            }), 500
    
    @app.route('/api/universal/submit-for-review', methods=['POST'])
    @login_required
    @permission_required('submit')
    def submit_document_for_review():
        """
        Submit any financial document for review
        """
        try:
            data = request.get_json()
            document_type = data.get('document_type')
            session_id = data.get('session_id')
            notes = data.get('notes', '')
            
            if not document_type or not session_id:
                return jsonify({
                    'success': False,
                    'error': 'Document type and session ID are required'
                }), 400
            
            # Get current user
            current_user = get_current_user()
            if not current_user:
                return jsonify({'success': False, 'error': 'User not authenticated'}), 401
            
            # Submit for review using universal workflow service
            result = upload_handler.workflow_service.submit_for_review(
                document_type=document_type,
                session_id=session_id,
                user_id=current_user.id,
                notes=notes
            )
            
            if result['success']:
                return jsonify(result)
            else:
                return jsonify(result), 400
                
        except Exception as e:
            return jsonify({
                'success': False,
                'error': f'Error submitting document for review: {str(e)}'
            }), 500
    
    @app.route('/api/universal/approve', methods=['POST'])
    @login_required
    @permission_required('approve')
    def approve_document():
        """
        Approve any financial document
        """
        try:
            data = request.get_json()
            document_type = data.get('document_type')
            session_id = data.get('session_id')
            notes = data.get('notes', '')
            
            if not document_type or not session_id:
                return jsonify({
                    'success': False,
                    'error': 'Document type and session ID are required'
                }), 400
            
            # Get current user
            current_user = get_current_user()
            if not current_user:
                return jsonify({'success': False, 'error': 'User not authenticated'}), 401
            
            # Approve document using universal workflow service
            result = upload_handler.workflow_service.approve_document(
                document_type=document_type,
                session_id=session_id,
                user_id=current_user.id,
                notes=notes
            )
            
            if result['success']:
                return jsonify(result)
            else:
                return jsonify(result), 400
                
        except Exception as e:
            return jsonify({
                'success': False,
                'error': f'Error approving document: {str(e)}'
            }), 500
    
    @app.route('/api/universal/reject', methods=['POST'])
    @login_required
    @permission_required('approve')
    def reject_document():
        """
        Reject any financial document
        """
        try:
            data = request.get_json()
            document_type = data.get('document_type')
            session_id = data.get('session_id')
            reason = data.get('reason', '')
            
            if not document_type or not session_id:
                return jsonify({
                    'success': False,
                    'error': 'Document type and session ID are required'
                }), 400
            
            if not reason:
                return jsonify({
                    'success': False,
                    'error': 'Rejection reason is required'
                }), 400
            
            # Get current user
            current_user = get_current_user()
            if not current_user:
                return jsonify({'success': False, 'error': 'User not authenticated'}), 401
            
            # Reject document using universal workflow service
            result = upload_handler.workflow_service.reject_document(
                document_type=document_type,
                session_id=session_id,
                user_id=current_user.id,
                reason=reason
            )
            
            if result['success']:
                return jsonify(result)
            else:
                return jsonify(result), 400
                
        except Exception as e:
            return jsonify({
                'success': False,
                'error': f'Error rejecting document: {str(e)}'
            }), 500
    
    @app.route('/api/universal/submissions', methods=['GET'])
    @login_required
    def get_universal_submissions():
        """
        Get all submissions for the current user across all document types
        """
        try:
            # Get current user
            current_user = get_current_user()
            if not current_user:
                return jsonify({'success': False, 'error': 'User not authenticated'}), 401
            
            # Get document type filter
            document_type = request.args.get('document_type')
            
            # Get submissions using universal workflow service
            result = upload_handler.workflow_service.get_user_submissions(
                user_id=current_user.id,
                document_type=document_type
            )
            
            return jsonify(result)
            
        except Exception as e:
            return jsonify({
                'success': False,
                'error': f'Error getting submissions: {str(e)}'
            }), 500
    
    @app.route('/api/universal/pending-approvals', methods=['GET'])
    @login_required
    @permission_required('approve')
    def get_pending_approvals():
        """
        Get all pending approvals for managers/CFOs across all document types
        """
        try:
            # Get current user
            current_user = get_current_user()
            if not current_user:
                return jsonify({'success': False, 'error': 'User not authenticated'}), 401
            
            # Get pending approvals using universal workflow service
            result = upload_handler.workflow_service.get_pending_approvals(
                user_id=current_user.id
            )
            
            return jsonify(result)
            
        except Exception as e:
            return jsonify({
                'success': False,
                'error': f'Error getting pending approvals: {str(e)}'
            }), 500
    
    @app.route('/api/universal/session/<session_id>', methods=['GET'])
    @login_required
    def get_document_session(session_id):
        """
        Get session details for any document type
        """
        try:
            document_type = request.args.get('document_type')
            
            if not document_type:
                return jsonify({
                    'success': False,
                    'error': 'Document type is required'
                }), 400
            
            # Get the appropriate service
            service = upload_handler.get_service(document_type)
            if not service:
                return jsonify({
                    'success': False,
                    'error': f'Unsupported document type: {document_type}'
                }), 400
            
            # Get session summary
            result = service.get_session_summary(session_id)
            
            return jsonify(result)
            
        except Exception as e:
            return jsonify({
                'success': False,
                'error': f'Error getting session: {str(e)}'
            }), 500
    
    @app.route('/api/submit-mapping', methods=['POST'])
    @login_required
    @permission_required('process')
    def submit_universal_mapping():
        """
        Universal API endpoint to submit mapped financial data for review
        Handles all document types: Balance Sheets, Income Statements, Budget Reports
        """
        try:
            data = request.get_json()
            mapped_data = data.get('mapped_data')
            session_id = data.get('session_id')
            document_type = data.get('document_type')
            
            if not mapped_data:
                return jsonify({'success': False, 'error': 'No mapped data provided'}), 400
            
            if not session_id:
                return jsonify({'success': False, 'error': 'No session ID provided'}), 400
            
            # If document_type not provided, try to infer it from session
            if not document_type:
                document_type = _infer_document_type_from_session(session_id)
                if not document_type:
                    return jsonify({'success': False, 'error': 'Document type is required and could not be inferred'}), 400
            
            # Get current user
            current_user = get_current_user()
            if not current_user:
                return jsonify({'success': False, 'error': 'User not authenticated'}), 401
            
            # Submit mapping using universal workflow service
            result = upload_handler.workflow_service.submit_for_review(
                document_type=document_type,
                session_id=session_id,
                user_id=current_user.id,
                notes=f"Submitted {len(mapped_data)} mapped accounts for review",
                mapped_data=mapped_data
            )
            
            if result['success']:
                return jsonify(result)
            else:
                return jsonify(result), 400
                
        except Exception as e:
            return jsonify({
                'success': False,
                'error': f'Error submitting mapping: {str(e)}'
            }), 500
    
    @app.route('/api/universal/validate-balance', methods=['POST'])
    @login_required
    def validate_universal_balance():
        """
        Universal API endpoint to validate balance for all document types
        Returns balance check results for Balance Sheets, Income Statements, and Budget Reports
        """
        try:
            data = request.get_json()
            session_id = data.get('session_id')
            document_type = data.get('document_type')
            
            if not session_id:
                return jsonify({'success': False, 'error': 'No session ID provided'}), 400
            
            # If document_type not provided, try to infer it from session
            if not document_type:
                document_type = _infer_document_type_from_session(session_id)
                if not document_type:
                    return jsonify({'success': False, 'error': 'Document type is required and could not be inferred'}), 400
            
            print(f"🔍 Universal balance check request - Session ID: {session_id}, Document Type: {document_type}")
            
            # Get the appropriate service for document type
            service = upload_handler.get_service(document_type)
            if not service:
                return jsonify({'success': False, 'error': f'Invalid document type: {document_type}'}), 400
            
            # Get the model from the service and retrieve data
            try:
                model = service.get_model()
                if not model:
                    return jsonify({'success': False, 'error': f'Unable to get model for document type: {document_type}'}), 500
                
                # Get session and data from database
                session_data = model.get_session(session_id)
                if not session_data:
                    return jsonify({'success': False, 'error': f'Session not found for document type: {document_type}'}), 404
                
                # Get document data from database (handle different method names)
                try:
                    data_rows = model.get_data_rows(session_id)
                except AttributeError:
                    try:
                        data_rows = model.get_session_data(session_id)
                    except AttributeError:
                        return jsonify({'success': False, 'error': f'Model does not have data retrieval methods for document type: {document_type}'}), 500
                if not data_rows:
                    return jsonify({'success': False, 'error': f'Document data not found for session_id: {session_id}'}), 404
                    
            except Exception as e:
                print(f"❌ Error accessing model data: {str(e)}")
                return jsonify({'success': False, 'error': f'Unable to access data for document type: {document_type}: {str(e)}'}), 500
            
            # Calculate balance based on document type
            balance_results = _calculate_balance_for_document_type(document_type, data_rows)
            
            # Debug logging for budget reports
            if document_type == 'budget_report':
                print(f"🔍 Budget Report Balance Calculation:")
                print(f"   Total Budget: {balance_results.get('total_budget', 0)}")
                print(f"   Total Actual: {balance_results.get('total_actual', 0)}")
                print(f"   Variance: {balance_results.get('variance', 0)}")
                print(f"   is_balanced: {balance_results.get('is_balanced', False)}")
                print(f"   Tolerance Check: abs({balance_results.get('variance', 0)}) < 0.01 = {abs(balance_results.get('variance', 0)) < 0.01}")
            
            return jsonify({
                'success': True,
                'document_type': document_type,
                'balance_check': balance_results
            })
            
        except Exception as e:
            print(f"❌ Universal balance check error: {str(e)}")
            return jsonify({
                'success': False,
                'error': f'Balance check error: {str(e)}'
            }), 500

def _calculate_balance_for_document_type(document_type, data_rows):
    """Calculate balance based on document type"""
    print(f"🔍 Calculating balance for document type: {document_type}")
    print(f"🔍 Number of data rows: {len(data_rows)}")
    print(f"🔍 First few rows: {data_rows[:3] if data_rows else 'No data'}")
    
    total_debits = 0.0
    total_credits = 0.0
    total_revenue = 0.0
    total_expenses = 0.0
    total_budget = 0.0
    total_actual = 0.0
    
    for row in data_rows:
        if document_type == 'balance_sheet':
            # Balance sheet: check debits vs credits
            debit_val = getattr(row, 'debit_balance', None) or getattr(row, 'debit', None)
            credit_val = getattr(row, 'credit_balance', None) or getattr(row, 'credit', None)
            
            total_debits += float(debit_val) if debit_val is not None else 0.0
            total_credits += float(credit_val) if credit_val is not None else 0.0
            
        elif document_type == 'income_statement':
            # Income statement: check revenue vs expenses
            # Income statements use debit/credit balance format where:
            # - Revenue = credit_balance
            # - Expenses = debit_balance
            category_val = getattr(row, 'category', None) or getattr(row, 'Category', None)
            credit_balance_val = getattr(row, 'credit_balance', None)
            debit_balance_val = getattr(row, 'debit_balance', None)
            
            # Debug logging for income statements
            print(f"🔍 Income Statement Row Processing:")
            print(f"   Category: {category_val}")
            print(f"   Credit Balance: {credit_balance_val}")
            print(f"   Debit Balance: {debit_balance_val}")
            
            if category_val:
                category = str(category_val).lower()
                
                if 'revenue' in category and credit_balance_val is not None:
                    revenue_amount = float(credit_balance_val)
                    total_revenue += revenue_amount
                    print(f"   Added to revenue: {revenue_amount}, Total revenue: {total_revenue}")
                    
                elif ('expense' in category or 'cost' in category) and debit_balance_val is not None:
                    expense_amount = float(debit_balance_val)
                    total_expenses += expense_amount
                    print(f"   Added to expenses: {expense_amount}, Total expenses: {total_expenses}")
                    
                # Skip summary rows (TOTAL_REVENUE, TOTAL_EXPENSES, NET_INCOME)
                elif 'summary' in category:
                    print(f"   Skipping summary row: {category_val}")
            else:
                print(f"   No category found, skipping row")
            
        elif document_type == 'budget_report':
            # Budget report: check budget vs actual
            budget_val = getattr(row, 'budget_amount', None) or getattr(row, 'budget', None)
            actual_val = getattr(row, 'actual_amount', None) or getattr(row, 'actual', None)
            
            # For budget reports, we'll treat budget as "debits" and actual as "credits" for consistency
            total_budget += float(budget_val) if budget_val is not None else 0.0
            total_actual += float(actual_val) if actual_val is not None else 0.0
    
    # Return appropriate balance results based on document type
    if document_type == 'balance_sheet':
        difference = total_debits - total_credits
        return {
            'total_debits': total_debits,
            'total_credits': total_credits,
            'difference': difference,
            'is_balanced': abs(difference) < 0.01,  # Allow for rounding differences
            'balance_type': 'debits_vs_credits'
        }
    elif document_type == 'income_statement':
        net_income = total_revenue - total_expenses
        return {
            'total_revenue': total_revenue,
            'total_expenses': total_expenses,
            'net_income': net_income,
            'is_balanced': True,  # Income statements don't need to balance in the same way
            'balance_type': 'revenue_vs_expenses'
        }
    elif document_type == 'budget_report':
        variance = total_budget - total_actual  # Use actual amounts instead of expenses
        return {
                'total_budget': total_budget,
                'total_actual': total_actual,  # Use actual amounts from budget report
                'variance': variance,
                'is_balanced': abs(variance) < 0.01,  # Allow for rounding differences
                'balance_type': 'budget_vs_actual'
            }
    
    return {'is_balanced': True, 'balance_type': 'unknown'}
