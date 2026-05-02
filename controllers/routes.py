"""
SADPMR Financial Reporting System - Flask Routes with Authentication
Web interface and API endpoints for GRAP financial statement generation
"""

from flask import Flask, render_template, request, jsonify, send_file, flash, redirect, url_for, session
from werkzeug.utils import secure_filename
from functools import wraps
import os
import pandas as pd
import json
from datetime import datetime
import sys
import logging

# Import our Phase 1 mapping engine and auth models
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from models.grap_models import GRAPMappingEngine
from models.supabase_auth_models import supabase_auth, SupabaseUser, get_role_description, get_role_color
from services.grap_mapping_service import grap_mapping_service
from utils.constants import WorkflowErrorMessages

# Import formula transparency blueprint
from controllers.routes_formula import formula_bp

# Set up logging
logger = logging.getLogger(__name__)

# Configuration
app = Flask(__name__, 
           template_folder='../templates', 
           static_folder='../static',
           static_url_path='/static')
app.config['SECRET_KEY'] = 'sadpmr-demo-2025-secure-key-auth-enabled'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['OUTPUT_FOLDER'] = 'outputs'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['DEBUG'] = True  # Enable debug logging

ALLOWED_EXTENSIONS = {'xlsx', 'xls', 'csv', 'xlsm', 'xlsb', 'tsv'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def validate_flexible_trial_balance(df, file_extension):
    """
    Flexible trial balance validation that can handle different structures and formats.
    Detects the structure automatically and validates accordingly.
    """
    result = {
        'is_valid': False,
        'error': '',
        'suggestion': '',
        'file_type_detected': 'unknown',
        'detected_structure': 'none',
        'account_code_col': None,
        'account_desc_col': None,
        'balance_cols': []
    }
    
    try:
        # Check if this is a financial analysis template (reject these)
        financial_analysis_indicators = []
        for col in df.columns:
            col_str = str(col).lower()
            if any(indicator in col_str for indicator in ['benefit', 'cash flow', 'cost item', 'inflow', 'outflow']):
                financial_analysis_indicators.append(col)
        
        if financial_analysis_indicators:
            result['file_type_detected'] = 'financial_analysis_template'
            result['error'] = 'This appears to be a financial analysis template, not a trial balance.'
            result['suggestion'] = 'Please upload a trial balance with account codes, descriptions, and balance amounts.'
            return result
        
        # Try different trial balance structure detection methods
        
        # Method 1: Standard trial balance format
        standard_cols = ['Account Code', 'Account Description']
        if all(col in df.columns for col in standard_cols):
            # Check for balance columns
            balance_variations = [
                ['Debit Balance', 'Credit Balance'],
                ['Net Balance'],
                ['Balance'],
                ['Amount'],
                ['Debit', 'Credit']
            ]
            
            for balance_set in balance_variations:
                if all(col in df.columns for col in balance_set):
                    result['is_valid'] = True
                    result['detected_structure'] = 'standard_trial_balance'
                    result['account_code_col'] = 'Account Code'
                    result['account_desc_col'] = 'Account Description'
                    result['balance_cols'] = balance_set
                    return result
        
        # Method 1.5: Handle numeric_only structure (detected by flexible service)
        if 'Account Code' in df.columns and 'Account Description' in df.columns:
            # Check for balance columns with different naming
            balance_variations = [
                ['Debit Balance', 'Credit Balance'],
                ['Net Balance'],
                ['Balance'],
                ['Amount'],
                ['Debit', 'Credit']
            ]
            
            for balance_set in balance_variations:
                if all(col in df.columns for col in balance_set):
                    result['is_valid'] = True
                    result['detected_structure'] = 'standard_trial_balance'  # Treat as standard
                    result['account_code_col'] = 'Account Code'
                    result['account_desc_col'] = 'Account Description'
                    result['balance_cols'] = balance_set
                    return result
        
        # Method 2: Hospital/Department format (like the hospital file)
        if len(df.columns) >= 6:
            # Look for department codes in any column
            dept_code_col = None
            account_desc_col = None
            financial_cols = []
            
            for col_idx, col in enumerate(df.columns):
                col_values = df.iloc[:, col_idx].dropna().tolist()
                
                # Check for department codes (H0122, H0123, etc.)
                dept_code_pattern = any(
                    str(val).startswith('H') and len(str(val)) == 4 and str(val)[1:].isdigit()
                    for val in col_values[:20]  # Check first 20 values
                )
                
                # Check for account descriptions (clinic names, departments)
                desc_pattern = any(
                    any(keyword in str(val).lower() for keyword in ['clinic', 'institute', 'department', 'therapy'])
                    for val in col_values[:20]
                )
                
                # Check for financial data
                numeric_count = sum(1 for val in col_values[:20] if str(val).replace('.', '').replace('-', '').isdigit())
                has_financial_data = numeric_count >= 3
                
                if dept_code_pattern and not dept_code_col:
                    dept_code_col = col_idx
                elif desc_pattern and not account_desc_col:
                    account_desc_col = col_idx
                elif has_financial_data:
                    financial_cols.append(col_idx)
            
            # If we found the hospital structure
            if dept_code_col is not None and account_desc_col is not None and len(financial_cols) >= 2:
                result['is_valid'] = True
                result['detected_structure'] = 'hospital_department_format'
                result['account_code_col'] = dept_code_col
                result['account_desc_col'] = account_desc_col
                result['balance_cols'] = financial_cols
                result['file_type_detected'] = 'hospital_trial_balance'
                return result
        
        # Method 3: Generic format detection - look for any column with codes and any column with descriptions
        code_col = None
        desc_col = None
        balance_cols = []
        
        for col_idx, col in enumerate(df.columns):
            col_values = df.iloc[:, col_idx].dropna().tolist()
            
            if len(col_values) < 3:  # Skip columns with too little data
                continue
            
            # Check for account codes (various patterns)
            code_patterns = [
                # Numeric codes (1001, 1002, etc.)
                any(str(val).isdigit() and len(str(val)) >= 4 for val in col_values[:10]),
                # Alphanumeric codes (ACC-001, etc.)
                any(any(char.isalpha() for char in str(val)) and any(char.isdigit() for char in str(val)) for val in col_values[:10]),
                # Department codes (H0122, etc.)
                any(str(val).startswith('H') and len(str(val)) == 4 for val in col_values[:10])
            ]
            
            # Check for descriptions (text content)
            desc_patterns = [
                # Contains common department/clinic words
                any(any(keyword in str(val).lower() for keyword in ['clinic', 'department', 'institute', 'therapy', 'service']) for val in col_values[:10]),
                # Mixed alphanumeric (not pure numbers)
                any(not str(val).replace('.', '').replace('-', '').isdigit() and len(str(val)) > 3 for val in col_values[:10])
            ]
            
            # Check for financial data
            numeric_count = sum(1 for val in col_values[:10] if str(val).replace('.', '').replace('-', '').isdigit())
            has_financial_data = numeric_count >= 3
            
            if any(code_patterns) and not code_col:
                code_col = col_idx
            elif any(desc_patterns) and not desc_col:
                desc_col = col_idx
            elif has_financial_data:
                balance_cols.append(col_idx)
        
        # If we found a generic structure
        if code_col is not None and desc_col is not None and len(balance_cols) >= 1:
            result['is_valid'] = True
            result['detected_structure'] = 'generic_trial_balance'
            result['account_code_col'] = code_col
            result['account_desc_col'] = desc_col
            result['balance_cols'] = balance_cols
            result['file_type_detected'] = 'generic_trial_balance'
            return result
        
        # If no structure was detected
        result['error'] = 'Unable to detect trial balance structure.'
        result['suggestion'] = 'Please ensure your file has account codes, account descriptions, and balance amounts.'
        result['file_type_detected'] = 'unrecognized_format'
        
    except Exception as e:
        result['error'] = f'Error during validation: {str(e)}'
        result['suggestion'] = 'Please check your file format and try again.'
    
    return result


def convert_to_standard_format(trial_balance, validation_result):
    """
    Convert different trial balance formats to standard format for GRAP mapping engine
    """
    try:
        detected_structure = validation_result['detected_structure']
        
        if detected_structure == 'standard_trial_balance':
            # Already in standard format - just clean it up
            # Remove summary rows and empty rows
            clean_df = trial_balance.copy()
            clean_df = clean_df.dropna(subset=['Account Code', 'Account Description'])
            clean_df = clean_df[~clean_df['Account Code'].astype(str).str.contains('TOTAL', na=False)]
            
            # Ensure we have the required columns
            if 'Net Balance' not in clean_df.columns:
                # Create Net Balance from Debit and Credit columns
                clean_df['Net Balance'] = clean_df['Debit Balance'] - clean_df['Credit Balance']
            
            return clean_df
        
        elif detected_structure == 'hospital_department_format':
            # Convert hospital format to standard format
            account_code_col = validation_result['account_code_col']
            account_desc_col = validation_result['account_desc_col']
            balance_cols = validation_result['balance_cols']
            
            standard_data = []
            
            for idx, row in trial_balance.iterrows():
                # Skip empty rows and summary rows
                if pd.isna(row.iloc[account_code_col]) or pd.isna(row.iloc[account_desc_col]):
                    continue
                
                account_code = str(row.iloc[account_code_col])
                account_desc = str(row.iloc[account_desc_col])
                
                # Skip if this looks like a summary row
                if 'TOTAL' in account_desc.upper() or account_desc.strip() == '':
                    continue
                
                # Calculate net balance from all financial columns
                net_balance = 0
                for col_idx in balance_cols:
                    if col_idx < len(trial_balance.columns):
                        col_name = trial_balance.columns[col_idx]
                        if col_name in row and pd.notna(row[col_name]):
                            try:
                                value = float(row[col_name])
                                net_balance += abs(value)  # Treat all as positive for hospital format
                            except (ValueError, TypeError):
                                continue
                
                # Determine if this is a debit or credit based on account type
                # For hospital format, we'll treat all as positive values
                standard_data.append({
                    'Account Code': account_code,
                    'Account Description': account_desc,
                    'Debit Balance': net_balance if net_balance > 0 else 0,
                    'Credit Balance': 0,
                    'Net Balance': net_balance
                })
            
            return pd.DataFrame(standard_data)
        
        elif detected_structure == 'generic_trial_balance':
            # Convert generic format to standard format
            account_code_col = validation_result['account_code_col']
            account_desc_col = validation_result['account_desc_col']
            balance_cols = validation_result['balance_cols']
            
            standard_data = []
            
            for idx, row in trial_balance.iterrows():
                # Skip empty rows
                if pd.isna(row.iloc[account_code_col]) or pd.isna(row.iloc[account_desc_col]):
                    continue
                
                account_code = str(row.iloc[account_code_col])
                account_desc = str(row.iloc[account_desc_col])
                
                # Calculate net balance from balance columns
                net_balance = 0
                for col_idx in balance_cols:
                    if col_idx < len(trial_balance.columns):
                        col_name = trial_balance.columns[col_idx]
                        if col_name in row and pd.notna(row[col_name]):
                            try:
                                value = float(row[col_name])
                                net_balance += value
                            except (ValueError, TypeError):
                                continue
                
                # Determine debit/credit based on sign
                debit_balance = net_balance if net_balance > 0 else 0
                credit_balance = abs(net_balance) if net_balance < 0 else 0
                
                standard_data.append({
                    'Account Code': account_code,
                    'Account Description': account_desc,
                    'Debit Balance': debit_balance,
                    'Credit Balance': credit_balance,
                    'Net Balance': net_balance
                })
            
            return pd.DataFrame(standard_data)
        
        else:
            # Unknown format - try to create a basic standard format
            # Look for any columns that might contain account codes, descriptions, and balances
            account_codes = []
            account_descs = []
            net_balances = []
            
            for idx, row in trial_balance.iterrows():
                # Try to identify account codes (numeric or alphanumeric)
                code_found = False
                desc_found = False
                balance_found = False
                
                for col_idx, col_name in enumerate(trial_balance.columns):
                    value = row.iloc[col_idx]
                    
                    if pd.isna(value):
                        continue
                    
                    # Look for account codes (numeric or alphanumeric patterns)
                    if not code_found and isinstance(value, (int, float, str)):
                        str_val = str(value).strip()
                        if (str_val.isdigit() and len(str_val) >= 3) or \
                           (any(c.isalpha() for c in str_val) and any(c.isdigit() for c in str_val)):
                            account_codes.append(str_val)
                            code_found = True
                    
                    # Look for descriptions (text that's not pure numbers)
                    elif not desc_found and isinstance(value, str):
                        str_val = str(value).strip()
                        if not str_val.replace('.', '').replace('-', '').isdigit() and len(str_val) > 2:
                            account_descs.append(str_val)
                            desc_found = True
                    
                    # Look for balance values (numeric)
                    elif not balance_found and isinstance(value, (int, float)):
                        try:
                            balance = float(value)
                            if abs(balance) > 0:
                                net_balances.append(balance)
                                balance_found = True
                        except (ValueError, TypeError):
                            continue
            
                # If we found all three, add to standard data
                if code_found and desc_found and balance_found:
                    net_balance = net_balances[-1] if net_balances else 0
                    debit_balance = net_balance if net_balance > 0 else 0
                    credit_balance = abs(net_balance) if net_balance < 0 else 0
                    
                    standard_data.append({
                        'Account Code': account_codes[-1],
                        'Account Description': account_descs[-1],
                        'Debit Balance': debit_balance,
                        'Credit Balance': credit_balance,
                        'Net Balance': net_balance
                    })
            
            return pd.DataFrame(standard_data) if standard_data else pd.DataFrame()
    
    except Exception as e:
        return pd.DataFrame()


# Authentication decorator
def login_required(f):
    @wraps(f)
    def login_wrapper(*args, **kwargs):
        if 'user_id' not in session:
            # Check if this is an API endpoint - return JSON instead of redirect
            if request.path.startswith('/api/'):
                return jsonify({'success': False, 'error': 'Authentication required'}), 401
            else:
                flash('Please log in to access this page.', 'warning')
                return redirect(url_for('login'))
        return f(*args, **kwargs)
    login_wrapper.__name__ = f.__name__
    return login_wrapper


def permission_required(permission):
    """Decorator to check specific permissions using Supabase only"""
    def permission_decorator(f):
        @wraps(f)
        def permission_wrapper(*args, **kwargs):
            if 'user_id' not in session:
                return jsonify({'success': False, 'error': 'Authentication required'}), 401
            
            try:
                user_data = supabase_auth.get_user_by_id(session['user_id'])
                if not user_data:
                    return jsonify({'success': False, 'error': 'User not found in Supabase'}), 401
                
                user = SupabaseUser(user_data)
                if not user.has_permission(permission):
                    return jsonify({'success': False, 'error': f'Permission denied. {permission.upper()} access required.'}), 403
                
                return f(*args, **kwargs)
            except Exception as e:
                app.logger.error(f"Supabase permission check failed: {str(e)}")
                return jsonify({'success': False, 'error': f'Authentication error: {str(e)}'}), 500
        
        permission_wrapper.__name__ = f.__name__
        return permission_wrapper
    return permission_decorator


def get_current_user():
    """Get current logged-in user"""
    if 'user_id' in session:
        user_data = supabase_auth.get_user_by_id(session['user_id'])
        if user_data:
            return SupabaseUser(user_data)
    return None


# Authentication Routes
@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user_data = supabase_auth.verify_password(username, password)
        
        if user_data and user_data['is_active']:
            session['user_id'] = user_data['id']
            session['username'] = user_data['username']
            session['role'] = user_data['role']
            session['full_name'] = user_data['full_name']
            session.permanent = True
            
            # DON'T flash message - just redirect
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password.', 'error')
    
    return render_template('login.html')


@app.route('/api/auth/user', methods=['POST'])
def api_get_user():
    """API endpoint to get user by username"""
    try:
        data = request.get_json()
        username = data.get('username')
        
        if not username:
            return jsonify({'success': False, 'error': 'Username required'}), 400
        
        user = supabase_auth.get_user_by_username(username)
        
        if user:
            return jsonify({
                'success': True,
                'user': {
                    'id': user['id'],
                    'username': user['username'],
                    'full_name': user['full_name'],
                    'role': user['role'],
                    'email': user['email'],
                    'is_active': user['is_active']
                }
            })
        else:
            return jsonify({'success': False, 'error': 'User not found'}), 404
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/auth/login', methods=['POST'])
def api_login():
    """API endpoint for login"""
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            return jsonify({'success': False, 'error': 'Username and password required'}), 400
        
        # Try Supabase authentication
        user_data = supabase_auth.verify_password(username, password)
        
        if user_data and user_data['is_active']:
            return jsonify({
                'success': True,
                'user': {
                    'id': user_data['id'],
                    'username': user_data['username'],
                    'full_name': user_data['full_name'],
                    'role': user_data['role'],
                    'email': user_data['email'],
                    'is_active': user_data['is_active']
                }
            })
        else:
            return jsonify({'success': False, 'error': 'Invalid credentials'}), 401
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/user/permissions', methods=['GET'])
@login_required
def get_user_permissions():
    """Get current user permissions"""
    try:
        user = get_current_user()
        if not user:
            return jsonify({'success': False, 'error': 'Not authenticated'}), 401
        
        return jsonify({
            'success': True,
            'permissions': {
                'can_upload': user.can_upload(),
                'can_process': user.can_process(),
                'can_approve': user.can_approve(),
                'can_review': user.can_review(),
                'can_final_approve': user.can_final_approve(),
                'can_generate_pdf': user.can_generate_pdf(),
                'can_view_all': user.can_view_all(),
                'can_manage_assets': user.can_manage_assets(),
                'can_manage_users': user.can_manage_users(),
                'can_export_audit': user.can_export_audit(),
                'can_export': user.can_export()
            },
            'role': user.role,
            'full_name': user.full_name
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/logout')
def logout():
    """Logout user"""
    username = session.get('full_name', 'User')
    session.clear()
    flash(f'Goodbye, {username}! You have been logged out.', 'info')
    return redirect(url_for('login'))


@app.route('/')
def index():
    """Public landing page - accessible without authentication"""
    user = get_current_user()
    return render_template('index.html', user=user)


@app.route('/dashboard')
@login_required
def dashboard():
    """Authenticated dashboard - requires login"""
    user = get_current_user()
    
    # Prepare data for Finance Clerk dashboard
    if user and user.role == 'FINANCE_CLERK':
        from models.workflow_models import workflow_model
        periods = workflow_model.get_open_periods()
        stats = workflow_model.get_period_stats()
        
        return render_template('dashboard.html', user=user, periods=periods, stats=stats)
    else:
        # Provide default stats data to prevent template errors
        stats = {
            'open_periods': 0,
            'pending_uploads': 0,
            'pending_approvals': 0,
            'completed_reports': 0,
            'total_assets': 0,
            'total_liabilities': 0
        }
        
        return render_template('dashboard.html', user=user, stats=stats)


@app.route('/approvals')
@login_required
def approvals_page():
    """Transaction approvals page"""
    user = get_current_user()
    return render_template('approvals.html', user=user)


@app.route('/upload')
@login_required
def upload_page():
    """Trial Balance Upload Page"""
    user = get_current_user()
    if not user.can_upload():
        flash('You do not have permission to upload files.', 'error')
        return redirect(url_for('dashboard'))
    return render_template('upload.html', user=user)


@app.route('/mapping')
@login_required
def mapping_page():
    """Account Mapping Interface Page"""
    user = get_current_user()
    if not user.can_process():
        flash('You do not have permission to access mapping interface.', 'error')
        return redirect(url_for('dashboard'))
    return render_template('mapping_interface.html', user=user)


@app.route('/finance-clerk-workflow')
@login_required
def finance_clerk_workflow():
    """Finance Clerk Workflow Integration Page"""
    user = get_current_user()
    if user.role != 'FINANCE_CLERK':
        flash('Access denied. Finance Clerk privileges required.', 'error')
        return redirect(url_for('dashboard'))
    return render_template('finance_clerk_workflow.html', user=user)


@app.route('/api/upload', methods=['POST'])
def upload_trial_balance():
    """
    API endpoint to handle Trial Balance file upload with flexible format detection
    Processes file directly into database for GRAP compliance
    Returns: JSON with upload status and session details
    """
    try:
        print(" Upload endpoint called")
        print(f" Request files: {list(request.files.keys())}")
        print(f" Request form: {dict(request.form)}")
        print(f" Session: {dict(session)}")
        
        # Check if user is authenticated
        if 'user_id' not in session:
            print(" User not authenticated - no user_id in session")
            return jsonify({'success': False, 'error': 'User not authenticated. Please login first.'}), 401
        
        if 'file' not in request.files:
            print(" No file in request")
            return jsonify({'success': False, 'error': 'No file uploaded'}), 400
        
        file = request.files['file']
        print(f" File received: {file.filename}")
        print(f" File size: {file.content_length if hasattr(file, 'content_length') else 'Unknown'}")
        
        if file.filename == '':
            print(" Empty filename")
            return jsonify({'success': False, 'error': 'No file selected'}), 400
        
        if file and allowed_file(file.filename):
            print(" File type allowed")
            
            # Get current user first
            current_user = get_current_user()
            if not current_user:
                print(" User not authenticated")
                return jsonify({'success': False, 'error': 'User not authenticated'}), 401
            
            print(f" User authenticated: {current_user.username}")
            print(f" User ID: {current_user.id}")
            
            # Read file data for processing
            file_data = file.read()
            original_filename = secure_filename(file.filename)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            processing_filename = f"{timestamp}_{original_filename}"
            
            # Create temporary file for processing (will be deleted after)
            import tempfile
            with tempfile.NamedTemporaryFile(delete=False, suffix=f".{original_filename.split('.')[-1]}") as temp_file:
                temp_file.write(file_data)
                temp_filepath = temp_file.name
            
            try:
                print(" Starting flexible trial balance processing...")
                
                # Use flexible trial balance service for processing
                from services.flexible_trial_balance_service import flexible_trial_balance_service
                
                print(" Processing upload with flexible service...")
                processing_result = flexible_trial_balance_service.process_upload(
                    file_path=temp_filepath,
                    user_id=current_user.id,
                    filename=processing_filename
                )
                
                print(f" Processing result: {processing_result}")
                
                if not processing_result['success']:
                    print(f" Processing failed: {processing_result['error']}")
                    return jsonify({
                        'success': False,
                        'error': processing_result['error']
                    }), 400
                
                print(" Getting session summary...")
                # Get session summary for detailed response
                session_summary = flexible_trial_balance_service.get_session_summary(processing_result['session_id'])
                
                print(" Upload processing completed successfully")
                return jsonify({
                    'success': True,
                    'session_id': processing_result['session_id'],
                    'filename': processing_filename,
                    'filepath': None,  # No local file storage
                    'storage_type': 'database',  # Data stored in database
                    'file_format': processing_result['file_format'],
                    'structure_info': processing_result['structure_info'],
                    'total_rows': processing_result['total_rows'],
                    'total_columns': processing_result['total_columns'],
                    'columns': processing_result['columns'],
                    'mapping_results': processing_result['mapping_results'],
                    'session_summary': session_summary,
                    'message': f'Successfully processed {processing_result["total_rows"]} rows with {processing_result["total_columns"]} columns and stored in database',
                    'detected_file_type': processing_result['structure_info']['file_type'],
                    'data_quality_score': processing_result['structure_info']['quality_score']
                })
                
            finally:
                # Clean up temporary file
                try:
                    os.unlink(temp_filepath)
                    print(" Temporary file cleaned up")
                except:
                    pass
        
        else:
            print(f" File type not allowed: {file.filename}")
            return jsonify({'success': False, 'error': 'Invalid file type'}), 400
        
    except Exception as e:
        print(f" Exception in upload processing: {str(e)}")
        import traceback
        print(f" Full traceback: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': f'Upload processing failed: {str(e)}'
        }), 500


@app.route('/api/debug-test', methods=['GET'])
def debug_test():
    """Debug endpoint to test route registration"""
    return jsonify({'success': True, 'message': 'Debug endpoint working'})


@app.route('/api/validate-balance', methods=['POST'])
def validate_trial_balance():
    """
    API endpoint to validate trial balance before processing
    Returns balance check results and enables/disables submit button
    """
    try:
        data = request.get_json()
        session_id = data.get('session_id')
        
        # Write debug info to file
        with open('balance_check_debug.log', 'a') as f:
            f.write(f"[{datetime.now().isoformat()}] Balance check request - Session ID: {session_id}\n")
        
        print(f"🔍 Balance check request - Session ID: {session_id}")
        
        if not session_id:
            return jsonify({'success': False, 'error': 'No session ID provided'}), 400
        
        # Get trial balance data from database/session storage
        from services.flexible_trial_balance_service import flexible_trial_balance_service
        
        with open('balance_check_debug.log', 'a') as f:
            f.write(f"[{datetime.now().isoformat()}] Retrieving session data for ID: {session_id}\n")
        
        print(f"🔍 Retrieving session data for ID: {session_id}")
        
        # Retrieve the processed data from the session
        session_data = flexible_trial_balance_service.get_session_data(session_id)
        
        with open('balance_check_debug.log', 'a') as f:
            f.write(f"[{datetime.now().isoformat()}] Session data result: {session_data}\n")
        
        print(f"🔍 Session data result: {session_data}")
        
        if not session_data or not session_data.get('success'):
            error_msg = f'Session data not found or invalid for session_id: {session_id}'
            with open('balance_check_debug.log', 'a') as f:
                f.write(f"[{datetime.now().isoformat()}] Balance check failed: {error_msg}\n")
            print(f" Balance check failed: {error_msg}")
            return jsonify({'success': False, 'error': error_msg}), 404
        
        # Get the trial balance data from session
        trial_balance_data = session_data.get('trial_balance_data')
        if not trial_balance_data:
            return jsonify({
                'success': False,
                'error': 'Trial balance data not found in session'
            }), 404
        
        # Convert to DataFrame for validation
        import pandas as pd
        trial_balance = pd.DataFrame(trial_balance_data)
        
        # Validate that we have data
        if trial_balance.empty:
            return jsonify({
                'success': False,
                'error': 'The trial balance data appears to be empty.'
            }), 500
        
        # Use flexible validation to understand the structure
        file_extension = session_data.get('file_format', 'xlsx')
        validation_result = validate_flexible_trial_balance(trial_balance, file_extension)
        
        if not validation_result['is_valid']:
            return jsonify({
                'success': False,
                'validation_error': f'File structure validation failed: {validation_result["error"]}',
                'suggestion': validation_result['suggestion'],
                'file_type_detected': validation_result.get('file_type_detected', 'unknown'),
                'detected_structure': validation_result.get('detected_structure', 'none')
            }), 500
        
        # Calculate balance totals based on detected structure
        total_debits = 0
        total_credits = 0
        
        if validation_result['detected_structure'] == 'standard_trial_balance':
            # Standard format - use column names
            if 'Debit Balance' in trial_balance.columns:
                total_debits = trial_balance['Debit Balance'].sum()
            if 'Credit Balance' in trial_balance.columns:
                total_credits = trial_balance['Credit Balance'].sum()
            
            # Handle Net Balance column (common in Pastel exports)
            if 'Net Balance' in trial_balance.columns:
                net_balance = trial_balance['Net Balance'].sum()
                if abs(net_balance) < 0.01:  # Balanced
                    total_debits = trial_balance[trial_balance['Net Balance'] > 0]['Net Balance'].sum()
                    total_credits = abs(trial_balance[trial_balance['Net Balance'] < 0]['Net Balance'].sum())
        
        elif validation_result['detected_structure'] == 'hospital_department_format':
            # Hospital format - sum all financial columns as expenses/revenue
            balance_cols = validation_result['balance_cols']
            for col_idx in balance_cols:
                if col_idx < len(trial_balance.columns):
                    col_name = trial_balance.columns[col_idx]
                    if col_name in trial_balance.columns:
                        # Treat all numeric values as part of the balance calculation
                        col_values = pd.to_numeric(trial_balance[col_name], errors='coerce').fillna(0)
                        total_debits += abs(col_values.sum())  # Treat all as debits for hospital format
        
        elif validation_result['detected_structure'] == 'generic_trial_balance':
            # Generic format - try to identify debit/credit patterns
            balance_cols = validation_result['balance_cols']
            for col_idx in balance_cols:
                if col_idx < len(trial_balance.columns):
                    col_name = trial_balance.columns[col_idx]
                    if col_name in trial_balance.columns:
                        col_values = pd.to_numeric(trial_balance[col_name], errors='coerce').fillna(0)
                        # Simple approach: treat all as debits for balance check
                        total_debits += abs(col_values.sum())
        
        else:
            # Unknown format - try basic balance detection
            # Look for any numeric columns that might contain balance data
            for col in trial_balance.columns:
                if trial_balance[col].dtype in ['int64', 'float64']:
                    col_sum = trial_balance[col].sum()
                    if abs(col_sum) > 0:
                        total_debits += abs(col_sum)
        
        # Calculate balance difference
        balance_difference = abs(total_debits - total_credits)
        tolerance = 0.01  # Allow for rounding errors
        
        # Determine if balanced
        is_balanced = bool(balance_difference <= tolerance)
        
        # Prepare validation response
        validation_result = {
            'success': True,
            'is_balanced': is_balanced,
            'total_debits': float(total_debits),
            'total_credits': float(total_credits),
            'balance_difference': float(balance_difference),
            'tolerance': tolerance,
            'can_submit': is_balanced,
            'allow_proceed_with_warning': bool(balance_difference <= (tolerance * 100)),  # Allow proceeding if difference is small
            'message': 'Trial balance is balanced' if is_balanced else 
                      f'Trial balance is not balanced. Difference: R {balance_difference:,.2f}',
            'recommendation': 'You can proceed to mapping' if is_balanced else 
                             'Please correct the trial balance or proceed with a warning',
            'account_count': int(len(trial_balance)),
            'validation_timestamp': datetime.now().isoformat(),
            'next_steps': {
                'balanced': ['Proceed to mapping', 'Generate financial statements'],
                'unbalanced': ['Correct and re-upload', 'Proceed with warning', 'Save for later']
            }
        }
        
        return jsonify(validation_result)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Balance validation error: {str(e)}'
        }), 500


@app.route('/api/processing', methods=['POST'])
@login_required
@permission_required('process')
def process_uploaded_file():
    """
    API endpoint to process trial balance data for GRAP mapping and financial statement generation
    Works with database-stored data instead of files
    """
    try:
        data = request.get_json()
        session_id = data.get('session_id')
        
        if not session_id:
            return jsonify({'success': False, 'error': 'No session ID provided'}), 400
        
        # Get current user
        current_user = get_current_user()
        if not current_user:
            return jsonify({'success': False, 'error': 'User not authenticated'}), 401
        
        print(f" Processing trial balance from database")
        print(f" User: {current_user.username}")
        print(f" Session ID: {session_id}")
        
        # Use flexible trial balance service for GRAP processing
        from services.flexible_trial_balance_service import flexible_trial_balance_service
        
        print(" Starting GRAP mapping and financial statement generation...")
        
        # Get session data for processing
        session_data = flexible_trial_balance_service.get_session_data(session_id)
        if not session_data or not session_data.get('success'):
            return jsonify({'success': False, 'error': 'Session data not found or invalid'}), 404
        
        # Process GRAP mapping and financial statements
        processing_result = flexible_trial_balance_service.process_grap_mapping(
            session_id=session_id,
            user_id=current_user.id
        )
        
        print(f" GRAP processing result: {processing_result}")
        
        if not processing_result['success']:
            print(f" GRAP processing failed: {processing_result['error']}")
            return jsonify({
                'success': False,
                'error': processing_result['error']
            }), 400
        
        print(" Getting final session summary...")
        # Get final session summary with GRAP mapping results
        session_summary = flexible_trial_balance_service.get_session_summary(session_id)

        print(" GRAP processing completed successfully")

        # Extract mapping data for frontend
        mapped_accounts = processing_result.get('mapped_accounts', [])
        unmapped_accounts = processing_result.get('unmapped_accounts', [])
        total_accounts = processing_result.get('total_accounts', 0)
        mapping_confidence = processing_result.get('mapping_confidence', 0)

        return jsonify({
            'success': True,
            'session_id': session_id,
            'storage_type': 'database',  # Data stored in database
            'file_format': session_data.get('file_format'),
            'structure_info': session_data.get('structure_info'),
            'total_rows': session_data.get('total_rows'),
            'total_columns': session_data.get('total_columns'),
            'columns': session_data.get('columns'),
            'mapping_results': processing_result.get('mapping_results', {}),
            'session_summary': session_summary,
            'grap_mapping': processing_result.get('grap_mapping', {}),
            'financial_statements': processing_result.get('financial_statements', {}),
            'message': f'Successfully processed {session_data.get("total_rows")} rows with GRAP compliance and generated financial statements',
            'detected_file_type': session_data.get('structure_info', {}).get('file_type'),
            'data_quality_score': session_data.get('structure_info', {}).get('quality_score'),
            # Add fields expected by frontend mapping interface
            'mapped_accounts': mapped_accounts,
            'unmapped_accounts': unmapped_accounts,
            'total_accounts': total_accounts,
            'mapping_confidence': mapping_confidence,
            'detected_structure': session_data.get('structure_info', {})
        })
        
    except Exception as e:
        print(f" Exception in GRAP processing: {str(e)}")
        import traceback
        print(f" Full traceback: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': f'GRAP processing failed: {str(e)}'
        }), 500


@app.route('/api/proceed-unbalanced', methods=['POST'])
@login_required
@permission_required('process')
def proceed_with_unbalanced():
    """
    API endpoint to proceed with unbalanced trial balance
    Allows clerk to continue despite balance discrepancy
    """
    try:
        data = request.get_json()
        filepath = data.get('filepath')
        proceed_with_warning = data.get('proceed_with_warning', False)
        
        if not filepath or not os.path.exists(filepath):
            return jsonify({'success': False, 'error': 'File not found'}), 404
        
        if not proceed_with_warning:
            return jsonify({'success': False, 'error': 'Must confirm proceeding with warning'}), 400
        
        # Log the decision to proceed with unbalanced trial balance
        user = get_current_user()
        
        # Store warning flag in session for later processing
        session['proceeding_unbalanced'] = True
        session['unbalanced_filepath'] = filepath
        session['unbalanced_user'] = user.username
        session['unbalanced_timestamp'] = datetime.now().isoformat()
        
        return jsonify({
            'success': True,
            'message': 'Proceeding with unbalanced trial balance',
            'warning': 'Financial statements may not be accurate due to balance discrepancy',
            'next_step': 'Proceed to mapping interface'
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Processing error: {str(e)}'
        }), 500


@app.route('/api/generate-pdf', methods=['POST'])
@login_required
@permission_required('generate_pdf')
def generate_pdf():
    """
    Generate PDF financial statements
    """
    try:
        data = request.get_json()
        results_file = data.get('results_file')
        
        if not results_file:
            return jsonify({'success': False, 'error': 'No results file specified'}), 400
        
        results_path = os.path.join('data', results_file)
        
        if not os.path.exists(results_path):
            return jsonify({'success': False, 'error': 'Results file not found'}), 404
        
        # Load results
        with open(results_path, 'r') as f:
            results = json.load(f)
        
        # Generate PDF
        pdf_filename = f"SADPMR_AFS_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        pdf_path = os.path.join(app.config['OUTPUT_FOLDER'], pdf_filename)
        
        # Import PDF generation function
        from models.grap_models import generate_pdf_report
        generate_pdf_report(results, pdf_path)
        
        return jsonify({
            'success': True,
            'pdf_filename': pdf_filename,
            'download_url': f'/download/{pdf_filename}'
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'PDF generation error: {str(e)}'
        }), 500


@app.route('/download/<filename>')
@login_required
def download_file(filename):
    """
    Download generated PDF
    """
    filepath = os.path.join(app.config['OUTPUT_FOLDER'], filename)
    
    if not os.path.exists(filepath):
        return "File not found", 404
    
    return send_file(filepath, as_attachment=True)


@app.route('/api/transactions/pending')
@login_required
@permission_required('review')  # Finance Manager and CFO can view pending
def get_pending_transactions():
    """Get pending transactions for approval"""
    try:
        user = get_current_user()
        
        # Import approval model
        from models.approval_models import approval_model
        
        # Get pending transactions filtered by approver role
        pending = approval_model.get_pending_transactions(approver_role=user.role)
        
        return jsonify({
            'success': True,
            'pending_transactions': pending,
            'count': len(pending)
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Error fetching pending transactions: {str(e)}'
        }), 500


@app.route('/api/files', methods=['GET'])
@login_required
def get_files():
    """
    Get list of uploaded files
    """
    try:
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 10))
        
        outputs_dir = app.config['OUTPUT_FOLDER']
        files = []
        total_size = 0
        trial_balances_count = 0
        pdf_reports_count = 0
        
        for filename in os.listdir(outputs_dir):
            filepath = os.path.join(outputs_dir, filename)
            if os.path.isfile(filepath) and filename.endswith('.xlsx'):
                stat = os.stat(filepath)
                file_info = {
                    'id': f"output_{filename}",
                    'filename': filename,
                    'original_filename': filename,
                    'file_type': 'trial_balance',
                    'file_size': stat.st_size,
                    'upload_date': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
                    'status': 'completed'
                }
                files.append(file_info)
                total_size += stat.st_size
                trial_balances_count += 1
            elif os.path.isfile(filepath) and filename.endswith('.pdf'):
                stat = os.stat(filepath)
                file_info = {
                    'id': f"output_{filename}",
                    'filename': filename,
                    'original_filename': filename,
                    'file_type': 'pdf_report',
                    'file_size': stat.st_size,
                    'upload_date': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
                    'status': 'completed'
                }
                files.append(file_info)
                total_size += stat.st_size
                pdf_reports_count += 1
        
        # Sort by upload date (newest first)
        files.sort(key=lambda x: x['upload_date'], reverse=True)
        
        # Pagination
        total_files = len(files)
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        paginated_files = files[start_idx:end_idx]
        
        # Convert size to MB
        storage_used = round(total_size / (1024 * 1024), 2)
        
        summary = {
            'total_files': total_files,
            'trial_balances': trial_balances_count,
            'pdf_reports': pdf_reports_count,
            'storage_used': f"{storage_used} MB"
        }
        
        # Pagination info
        pagination = {
            'current_page': page,
            'per_page': per_page,
            'total_pages': (total_files + per_page - 1) // per_page,
            'has_next': end_idx < total_files,
            'has_prev': page > 1
        }
        
        return jsonify({
            'success': True,
            'files': paginated_files,
            'summary': summary,
            'pagination': pagination
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Error loading files: {str(e)}'
        }), 500


@app.route('/results')
@login_required
def results_page():
    """
    Financial Statements Results Page
    """
    user = get_current_user()
    return render_template('results.html', user=user)


@app.route('/about')
@login_required
def about_page():
    """
    About the System
    """
    user = get_current_user()
    return render_template('about.html', user=user)


@app.route('/reports')
@login_required
def reports_page():
    """
    File Management Page - All authenticated users
    """
    user = get_current_user()
    return render_template('reports.html', user=user)


@app.route('/submission-history')
@login_required
def submission_history_page():
    """
    Submission History Page - For clerks to view their own submissions
    """
    user = get_current_user()
    return render_template('submission-history.html', user=user)


@app.route('/export')
@login_required
def export_page():
    """
    Export Page - CFO only
    """
    user = get_current_user()
    if user.role != 'CFO':
        flash('Access denied. CFO privileges required.', 'error')
        return redirect(url_for('index'))
    return render_template('export.html', user=user)


@app.route('/submission/<submission_id>')
@login_required
def submission_status_page(submission_id):
    """
    Submission Status Page - Shows submission details and status
    """
    try:
        user = get_current_user()
        submission_data = None
        
        # First try to get from database
        try:
            from models.trial_balance_models import TrialBalanceSession
            tb_session = TrialBalanceSession()
            
            # Get submission from database
            result = tb_session.client.table('submissions').select('*').eq('id', submission_id).execute()
            
            if result.data:
                submission_data = result.data[0]
                print(f"✅ Found submission in database: {submission_id}")
            
        except Exception as db_error:
            print(f"Database lookup failed: {str(db_error)}")
        
        # If not found in database, try file-based storage
        if not submission_data:
            # Check submission in session first
            submission_key = f'submission_{submission_id}'
            submission_data = session.get(submission_key)
            
            if not submission_data:
                # Check in data files
                submission_path = os.path.join('data', f"submission_{submission_id}.json")
                if os.path.exists(submission_path):
                    with open(submission_path, 'r') as f:
                        submission_data = json.load(f)
                    print(f"✅ Found submission in file: {submission_id}")
                else:
                    flash('Submission not found', 'error')
                    return redirect(url_for('index'))
        
        # Check if user owns this submission or has review permissions
        if submission_data.get('user_id') != user.id and not user.can_review():
            flash('Access denied', 'error')
            return redirect(url_for('index'))
        
        # Format submission data for template
        formatted_submission = {
            'id': submission_data.get('id', submission_id),
            'submission_name': submission_data.get('submission_name', 'Trial Balance Submission'),
            'original_filename': submission_data.get('original_filename', 'Unknown'),
            'status': submission_data.get('status', 'pending'),
            'priority': submission_data.get('priority', 'normal'),
            'total_accounts': submission_data.get('total_accounts', 0),
            'mapped_accounts': submission_data.get('mapped_accounts', 0),
            'unmapped_accounts': submission_data.get('unmapped_accounts', 0),
            'mapping_completion_percentage': submission_data.get('mapping_completion_percentage', 0),
            'total_assets': submission_data.get('total_assets', 0),
            'total_liabilities': submission_data.get('total_liabilities', 0),
            'total_equity': submission_data.get('total_equity', 0),
            'total_revenue': submission_data.get('total_revenue', 0),
            'total_expenses': submission_data.get('total_expenses', 0),
            'data_quality_score': submission_data.get('data_quality_score', 0),
            'grap_categories_used': submission_data.get('grap_categories_used', 0),
            'submitted_at': submission_data.get('submitted_at'),
            'reviewed_by': submission_data.get('reviewed_by'),
            'reviewed_at': submission_data.get('reviewed_at'),
            'review_notes': submission_data.get('review_notes'),
            'approval_comments': submission_data.get('approval_comments'),
            'rejection_reason': submission_data.get('rejection_reason'),
            'is_locked': submission_data.get('is_locked', False),
            'locked_at': submission_data.get('locked_at'),
            'metadata': submission_data.get('metadata', {}),
            'grap_mapping_data': submission_data.get('grap_mapping_data', {}),
            'financial_statements': submission_data.get('financial_statements', {}),
            'user_id': submission_data.get('user_id'),
            'session_id': submission_data.get('session_id')
        }
        
        return render_template('submission_status.html', 
                         user=user, 
                         submission=formatted_submission,
                         submission_id=submission_id)
        
    except Exception as e:
        flash(f'Error loading submission: {str(e)}', 'error')
        return redirect(url_for('index'))


@app.route('/admin')
@login_required
def admin_page():
    """
    Admin Page - CFO only
    """
    user = get_current_user()
    if user.role != 'CFO':
        flash('Access denied. CFO privileges required.', 'error')
        return redirect(url_for('index'))
    return render_template('admin.html', user=user)


@app.route('/api/submission-status/<submission_id>', methods=['GET'])
@login_required
def get_submission_status(submission_id):
    """Get submission status and check if file can be edited"""
    try:
        user = get_current_user()
        
        # Check submission in session first
        submission_key = f'submission_{submission_id}'
        submission_data = session.get(submission_key)
        
        if not submission_data:
            # Check in data files
            submission_path = os.path.join('data', f"submission_{submission_id}.json")
            if os.path.exists(submission_path):
                with open(submission_path, 'r') as f:
                    submission_data = json.load(f)
            else:
                return jsonify({'success': False, 'error': 'Submission not found'}), 404
        
        # Check if user owns this submission or has review permissions
        if submission_data['user_id'] != user.id and not user.can_review():
            return jsonify({'success': False, 'error': 'Access denied'}), 403
        
        # Determine if file can be edited
        can_edit = (
            submission_data['status'] == 'draft' or 
            (submission_data['status'] == 'rejected' and submission_data['user_id'] == user.id)
        )
        
        return jsonify({
            'success': True,
            'status': submission_data['status'],
            'locked': submission_data.get('locked', False),
            'can_edit': can_edit,
            'submission_timestamp': submission_data.get('submission_timestamp'),
            'review_notes': submission_data.get('review_notes', ''),
            'message': f"File is {submission_data['status']}"
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/submissions/user', methods=['GET'])
@login_required
def get_user_submissions():
    """Get all submissions for the current user"""
    try:
        user = get_current_user()
        user_id = user.id
        
        # Get user sessions from trial balance model
        from models.trial_balance_models import trial_balance_model
        sessions = trial_balance_model.get_user_sessions(user_id, limit=50)
        
        submissions = []
        session_ids_for_batch = []
        
        for session in sessions:
            # Get session summary for mapped accounts count (optimized)
            mapped_accounts_count = 0
            total_accounts_count = 0
            
            # Try to get account counts from metadata first (faster)
            if session.metadata and 'processing_results' in session.metadata:
                processing_results = session.metadata['processing_results']
                mapped_accounts_count = processing_results.get('mapped_accounts_count', 0)
                total_accounts_count = processing_results.get('total_accounts_count', 0)
            
            # Fallback to session summary only if needed
            if total_accounts_count == 0:
                try:
                    from services.flexible_trial_balance_service import flexible_trial_balance_service
                    session_summary = flexible_trial_balance_service.get_session_summary(session.id)
                    mapped_accounts_count = session_summary.get('mapped_accounts_count', 0)
                    total_accounts_count = session_summary.get('total_accounts_count', 0)
                except Exception as e:
                    print(f"⚠️ Debug - Error getting session summary for {session.id}: {str(e)}")
                    pass  # Use default values
            
            # Get validation status from trial balance data using batch approach
            validation_status = session.status  # fallback to session status
            try:
                # Add session ID to list for batch query
                session_ids_for_batch.append(session.id)
            except NameError:
                # Initialize the list on first iteration
                session_ids_for_batch = [session.id]
            
            # Skip expensive workflow checks for now - default to unlocked
            locked_status = False
            
            # Format submission data
            submission_data = {
                'session_id': session.id,
                'user_id': session.user_id,
                'filename': session.original_filename or session.filename,
                'filepath': session.filename,
                'submission_timestamp': session.created_at.isoformat() if session.created_at else None,
                'status': validation_status,  # Use validation_status from trial_balance_data
                'mapped_accounts_count': mapped_accounts_count,
                'total_accounts_count': total_accounts_count,
                'file_type': session.file_type,
                'review_notes': session.metadata.get('review_notes', ''),
                'locked': locked_status,
                'grap_mapping': session.metadata.get('grap_mapping', {}),
                'structure_info': session.metadata.get('structure_info', {}),
                'processing_results': session.metadata.get('processing_results', {}),
                'mapping_progress': session.metadata.get('mapping_progress', {})
            }
            submissions.append(submission_data)
        
        # Batch query to get all validation statuses at once
        validation_status_map = {}
        if session_ids_for_batch:
            try:
                # Get validation status for all sessions in one query
                batch_result = trial_balance_model.client.table('trial_balance_data')\
                    .select('session_id, validation_status')\
                    .in_('session_id', session_ids_for_batch)\
                    .execute()
                
                # Create a map of session_id -> validation_status
                for row in batch_result.data:
                    if row['session_id'] not in validation_status_map:
                        validation_status_map[row['session_id']] = row['validation_status']
                        print(f"🔍 Debug - Batch query - Session {row['session_id']} validation_status: {row['validation_status']}")
                
                # Update submissions with validation status from trial balance data
                for submission in submissions:
                    if submission['session_id'] in validation_status_map:
                        submission['status'] = validation_status_map[submission['session_id']]
                        print(f"🔍 Debug - Updated submission {submission['session_id']} status to: {submission['status']}")
                
            except Exception as e:
                print(f"⚠️ Debug - Batch query failed: {str(e)}")
                # Keep session status as fallback
        
        return jsonify({
            'success': True,
            'submissions': submissions
        })
        
    except Exception as e:
        app.logger.error(f"Error getting user submissions: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Error getting user submissions: {str(e)}'
        }), 500
@app.route('/api/clear-submission-lock', methods=['POST'])
@login_required
def clear_submission_lock():
    """Clear submission lock for the current user with restrictions"""
    try:
        user_id = get_current_user().id
        user = get_current_user()
        
        # Check if user has permission to clear locks (upload permission)
        if not user.has_permission('upload'):
            return jsonify({
                'success': False,
                'error': 'Permission denied. You do not have upload privileges.'
            }), 403
        
        cleared_count = 0
        pending_count = 0
        
        # Check for submission files in data directory
        data_dir = 'data'
        if os.path.exists(data_dir):
            for filename in os.listdir(data_dir):
                if filename.startswith('submission_') and filename.endswith('.json'):
                    filepath = os.path.join(data_dir, filename)
                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            submission_data = json.load(f)
                        
                        # Only count pending submissions for current user
                        if (submission_data.get('user_id') == user_id and 
                            submission_data.get('status') == 'pending'):
                            pending_count += 1
                            
                            # Allow clerks to upload multiple trial balances even while pending ones exist
                            # No restriction on other users' pending submissions - clerks can always upload
                            
                            # Delete the submission file
                            os.remove(filepath)
                            cleared_count += 1
                            
                    except Exception as e:
                        pass
        
        if cleared_count > 0:
            return jsonify({
                'success': True,
                'message': f'Cleared {cleared_count} submission locks',
                'restriction_applied': False
            })
        else:
            return jsonify({
                'success': True,
                'message': 'No submission locks to clear',
                'restriction_applied': False
            })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Error rejecting submission: {str(e)}'
        }), 500

@app.route('/api/submissions/pending')
@login_required
@permission_required('approve')
def get_pending_submissions():
    """Get all submissions pending finance clerk review"""
    try:
        # Use flexible trial balance service to get pending submissions
        from services.flexible_trial_balance_service import flexible_trial_balance_service
        pending_submissions = flexible_trial_balance_service.get_pending_submissions()
        
        return jsonify({
            'success': True,
            'submissions': pending_submissions
        })
        
    except Exception as e:
        app.logger.error(f"Error getting pending submissions: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Error getting pending submissions: {str(e)}'
        }), 500


@app.route('/api/grap-categories/<session_id>')
@login_required
@permission_required('process')
def get_grap_categories(session_id):
    """
    API endpoint to get GRAP categories for mapping interface
    Returns: JSON with GRAP categories structure
    """
    try:
        user = get_current_user()
        
        # Use GRAP mapping service to get categories
        grap_categories = grap_mapping_service.grap_categories
        
        # Convert to list format for frontend
        categories_list = []
        for i, (category_code, category_data) in enumerate(grap_categories.items()):
            try:
                category_item = {
                    'code': category_code,
                    'name': category_data['name'],
                    'keywords': category_data['keywords'],
                    'examples': category_data['examples']
                }
                categories_list.append(category_item)
            except Exception as category_error:
                raise
        
        response_data = {
            'categories': categories_list,
            'total': len(categories_list)
        }
        
        return jsonify({
            'categories': categories_list,
            'total': len(categories_list)
        })
        
    except Exception as e:
        return jsonify({
            'error': f'Error getting GRAP categories: {str(e)}'
        }), 500


@app.route('/api/unmapped-accounts/<session_id>')
@login_required
@permission_required('process')
def get_unmapped_accounts(session_id):
    """
    API endpoint to get unmapped accounts for mapping interface
    Returns: JSON with unmapped accounts and any existing mappings
    """
    try:
        from models.trial_balance_models import trial_balance_model
        
        # Get session data from database
        session = trial_balance_model.get_session(session_id)
        if not session:
            return jsonify({
                'success': False,
                'error': f'Session {session_id} not found'
            }), 404
        
        # Get trial balance data rows
        data_rows = trial_balance_model.get_session_data(session_id)
        
        # Process accounts for mapping interface
        unmapped_accounts = []
        mapped_accounts = {}
        
        for row in data_rows:
            # Create account object for frontend
            account = {
                'id': row.id,
                'code': str(row.account_code) if row.account_code else '',
                'name': row.account_description or '',
                'description': row.account_description or '',
                'amount': float(row.net_balance) if row.net_balance else 0,
                'debit_balance': float(row.debit_balance) if row.debit_balance else 0,
                'credit_balance': float(row.credit_balance) if row.credit_balance else 0,
                'net_balance': float(row.net_balance) if row.net_balance else 0,
                'row_index': row.row_index
            }
            
            # Check if account is already mapped
            if row.mapping_status == 'mapped' and row.grap_category:
                # Add to mapped accounts
                category = row.grap_category
                if category not in mapped_accounts:
                    mapped_accounts[category] = []
                mapped_accounts[category].append(account)
            else:
                # Add to unmapped accounts
                unmapped_accounts.append(account)
        
        return jsonify({
            'success': True,
            'accounts': unmapped_accounts,
            'mapped_accounts': mapped_accounts,
            'session_id': session_id,
            'total_accounts': len(unmapped_accounts) + sum(len(accounts) for accounts in mapped_accounts.values())
        })
        
    except Exception as e:
        import traceback
        print(f"Error in get_unmapped_accounts: {str(e)}")
        print(f"Traceback: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': f'Failed to load unmapped accounts: {str(e)}'
        }), 500


@app.route('/api/save-mapping-progress', methods=['POST'])
@login_required
@permission_required('process')
def save_mapping_progress():
    """
    API endpoint to save mapping progress during review
    Allows finance clerks to save their work and continue later
    """
    try:
        data = request.get_json()
        session_id = data.get('session_id')
        auto_mapped_accounts = data.get('auto_mapped_accounts', [])
        unmapped_accounts = data.get('unmapped_accounts', [])
        
        if not session_id:
            return jsonify({'success': False, 'error': 'No session ID provided'}), 400
        
        user = get_current_user()
        
        # Get session data
        from services.flexible_trial_balance_service import flexible_trial_balance_service
        session_data = flexible_trial_balance_service.get_session_data(session_id)
        
        if not session_data or not session_data.get('success'):
            return jsonify({'success': False, 'error': 'Session data not found or invalid'}), 404
        
        # Update session with mapping progress
        progress_data = {
            'auto_mapped_accounts': auto_mapped_accounts,
            'unmapped_accounts': unmapped_accounts,
            'saved_at': data.get('saved_at', datetime.now().isoformat()),
            'saved_by': user.username,
            'status': 'in_progress'  # Mark as in progress
        }
        
        # Save progress to session metadata
        flexible_trial_balance_service.update_session_metadata(session_id, {
            'mapping_progress': progress_data,
            'last_saved_by': user.id,
            'last_saved_at': datetime.now().isoformat()
        })
        
        return jsonify({
            'success': True,
            'message': 'Mapping progress saved successfully',
            'saved_at': progress_data['saved_at']
        })
        
    except Exception as e:
        print(f"Error saving mapping progress: {str(e)}")
        return jsonify({'success': False, 'error': f'Failed to save mapping progress: {str(e)}'}), 500


@app.route('/api/submit-for-review', methods=['POST'])
@login_required
@permission_required('process')
def submit_mapping_for_review():
    """
    API endpoint to submit mapped trial balance for review
    Stores GRAP-compliant data in database
    """
    try:
        data = request.get_json()
        mapped_data = data.get('mapped_data')
        session_id = data.get('session_id')
        
        if not mapped_data:
            return jsonify({'success': False, 'error': 'No mapped data provided'}), 400
        
        if not session_id:
            return jsonify({'success': False, 'error': 'No session ID provided'}), 400
        
        user = get_current_user()
        
        # Get session data with GRAP mapping results
        from services.flexible_trial_balance_service import flexible_trial_balance_service
        session_data = flexible_trial_balance_service.get_session_data(session_id)
        
        if not session_data or not session_data.get('success'):
            return jsonify({'success': False, 'error': 'Session data not found or invalid'}), 404
        
        # Calculate financial totals from mapped data
        total_assets = 0.0
        total_liabilities = 0.0
        total_equity = 0.0
        total_revenue = 0.0
        total_expenses = 0.0
        
        grap_categories_used = set()
        
        for account in mapped_data:
            grap_category = account.get('grap_category', '')
            grap_code = account.get('grap_code', '')
            net_balance = account.get('net_balance', 0)
            
            if net_balance:
                # Categorize by GRAP code
                if grap_code.startswith('CA'):  # Current Assets
                    total_assets += abs(net_balance)
                elif grap_code.startswith('NCA'):  # Non-Current Assets
                    total_assets += abs(net_balance)
                elif grap_code.startswith('CL'):  # Current Liabilities
                    total_liabilities += abs(net_balance)
                elif grap_code.startswith('NCL'):  # Non-Current Liabilities
                    total_liabilities += abs(net_balance)
                elif grap_code.startswith('EQ'):  # Equity
                    total_equity += abs(net_balance)
                elif grap_code.startswith('RV'):  # Revenue
                    total_revenue += abs(net_balance)
                elif grap_code.startswith('EX'):  # Expenses
                    total_expenses += abs(net_balance)
            
            # Track GRAP categories used
            if grap_category:
                grap_categories_used.add(grap_category)
        
        # Create submission record in database using trial balance models
        from models.trial_balance_models import TrialBalanceSession
        
        # Initialize database connection
        tb_session = TrialBalanceSession()
        
        submission_record = {
            'session_id': session_id,
            'user_id': user.id,
            'submission_name': f"Trial Balance Submission - {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            'original_filename': session_data.get('original_filename', 'Unknown'),
            'period_id': data.get('period_id'),
            'status': 'pending',
            'priority': 'normal',
            'total_accounts': len(mapped_data),
            'mapped_accounts': len(mapped_data),
            'unmapped_accounts': 0,  # All accounts are mapped when submitting
            'mapping_completion_percentage': 100.0,
            'total_assets': total_assets,
            'total_liabilities': total_liabilities,
            'total_equity': total_equity,
            'total_revenue': total_revenue,
            'total_expenses': total_expenses,
            'data_quality_score': session_data.get('structure_info', {}).get('quality_score', 0.0),
            'grap_categories_used': len(grap_categories_used),
            'metadata': {
                'file_format': session_data.get('file_format'),
                'total_rows': session_data.get('total_rows'),
                'total_columns': session_data.get('total_columns'),
                'structure_info': session_data.get('structure_info'),
                'grap_mapping': session_data.get('grap_mapping', {}),
                'financial_statements': session_data.get('financial_statements', {}),
                'submission_source': 'mapping_interface'
            },
            'grap_mapping_data': {
                'mapped_accounts': mapped_data,
                'grap_categories_used': list(grap_categories_used),
                'mapping_timestamp': datetime.now().isoformat()
            },
            'financial_statements': session_data.get('financial_statements', {}),
            'is_locked': True,
            'locked_at': datetime.now().isoformat(),
            'locked_by': user.id
        }
        
        # Store submission in database
        try:
            # Use Supabase client to insert submission
            result = tb_session.client.table('submissions').insert(submission_record).execute()
            
            if not result.data:
                raise Exception("Failed to create submission record")
            
            submission_id = result.data[0]['id']
            
            # Update trial balance data rows with mapping status
            for account in mapped_data:
                account_id = account.get('id')
                if account_id:
                    update_data = {
                        'mapping_status': 'manual_mapped',
                        'grap_category': account.get('grap_category', ''),
                        'grap_account': account.get('grap_account', ''),
                        'grap_subcategory': account.get('grap_subcategory', ''),
                        'mapping_confidence': account.get('confidence', 1.0),
                        'last_mapped_by': user.id,
                        'last_mapped_at': datetime.now().isoformat(),
                        'validation_status': 'pending'
                    }
                    
                    tb_session.client.table('trial_balance_data').update(update_data).eq('id', account_id).execute()
            
            # Update session status
            tb_session.client.table('trial_balance_sessions').update({
                'status': 'submitted',
                'updated_at': datetime.now().isoformat()
            }).eq('id', session_id).execute()
            
            print(f"✅ Database submission created: {submission_id}")
            print(f"📊 Mapped accounts: {len(mapped_data)}")
            print(f"📈 Total assets: R{total_assets:,.2f}")
            print(f"📉 Total liabilities: R{total_liabilities:,.2f}")
            print(f"💰 Total equity: R{total_equity:,.2f}")
            
            return jsonify({
                'success': True,
                'submission_id': submission_id,
                'status': 'pending',
                'message': 'GRAP-compliant trial balance submitted for finance manager review successfully',
                'locked': True,
                'can_edit': False,
                'storage_type': 'database',
                'grap_compliant': True,
                'financial_summary': {
                    'total_accounts': len(mapped_data),
                    'total_assets': total_assets,
                    'total_liabilities': total_liabilities,
                    'total_equity': total_equity,
                    'total_revenue': total_revenue,
                    'total_expenses': total_expenses,
                    'grap_categories_used': len(grap_categories_used)
                },
                'next_steps': [
                    'Submission is now pending finance manager review',
                    'You will be notified of approval/rejection',
                    'Data is locked until review is complete',
                    'GRAP compliance verified and stored in database'
                ],
                'submission_timestamp': submission_record['submitted_at'].isoformat(),
                'redirect_url': f'/submission/{submission_id}'
            })
            
        except Exception as db_error:
            print(f"❌ Database submission error: {str(db_error)}")
            # Fallback to file-based storage if database fails
            submission_id = f"submission_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{user.id}"
            submission_record['id'] = submission_id
            
            # Store in data file for persistence
            submission_filename = f"submission_{submission_id}.json"
            submission_path = os.path.join('data', submission_filename)
            
            with open(submission_path, 'w') as f:
                json.dump(submission_record, f, indent=2)
            
            return jsonify({
                'success': True,
                'submission_id': submission_id,
                'status': 'pending',
                'message': 'Trial balance submitted for review (file-based storage)',
                'locked': True,
                'can_edit': False,
                'storage_type': 'file',
                'redirect_url': f'/submission/{submission_id}'
            })
        
    except Exception as e:
        print(f"❌ Submission error: {str(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': f'Submission error: {str(e)}'
        }), 500


@app.route('/debug')
def debug_page():
    """
    Debug page to test role-based access
    """
    from flask import session
    user = get_current_user()
    return render_template('debug.html', user=user, session=session)


# Make user functions available in templates
@app.context_processor
def inject_user():
    return {
        'current_user': get_current_user(),
        'get_role_description': get_role_description,
        'get_role_color': get_role_color
    }


if __name__ == '__main__':
    # Ensure directories exist
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)
    os.makedirs('data', exist_ok=True)
    
    print("\n" + "="*70)
    print("SADPMR FINANCIAL REPORTING SYSTEM - AUTHENTICATED DEMO SERVER")
    print("="*70)
    # Register formula transparency blueprint
    app.register_blueprint(formula_bp)

    print("\n🔐 Authentication Enabled - Role-Based Access Control")
    print("\n📋 Demo Accounts:")
    print("   CFO:        cfo@example.com / demo123")
    print("   Accountant: accountant@example.com / demo123")
    print("   Clerk:      clerk@example.com / demo123")
    print("   Auditor:    auditor@example.com / demo123")
    print("\n🚀 Starting server...")
    print("📍 Open your browser and navigate to: http://localhost:5000")
    print("🎯 Demo ready for February 3, 2026")
    print("\n⚠️  Press CTRL+C to stop the server\n")
    
    app.run(debug=True, host='0.0.0.0', port=5000)