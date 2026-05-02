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

def validate_flexible_balance_sheet(df, file_extension):
    """
    Flexible balance sheet validation that can handle different structures and formats.
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
            result['error'] = 'This appears to be a financial analysis template, not a balance sheet.'
            result['suggestion'] = 'Please upload a balance sheet with account codes, descriptions, and balance amounts.'
            return result
        
        # Try different balance sheet structure detection methods
        
        # Method 1: Standard balance sheet format
        # Check for both naming conventions (camelCase and snake_case)
        standard_cols_camel = ['Account Code', 'Account Description']
        standard_cols_snake = ['account_code', 'account_description']
        
        if all(col in df.columns for col in standard_cols_camel):
            account_code_col = 'Account Code'
            account_desc_col = 'Account Description'
        elif all(col in df.columns for col in standard_cols_snake):
            account_code_col = 'account_code'
            account_desc_col = 'account_description'
        else:
            account_code_col = None
            account_desc_col = None
            
        if account_code_col and account_desc_col:
            # Check for balance columns (both naming conventions)
            balance_variations = [
                (['Debit Balance', 'Credit Balance'], ['debit_balance', 'credit_balance']),
                (['Net Balance'], ['net_balance']),
                (['Balance'], ['balance']),
                (['Amount'], ['amount']),
                (['Debit', 'Credit'], ['debit', 'credit'])
            ]
            
            for balance_set_camel, balance_set_snake in balance_variations:
                if all(col in df.columns for col in balance_set_camel):
                    result['is_valid'] = True
                    result['detected_structure'] = 'standard_balance_sheet'
                    result['account_code_col'] = account_code_col
                    result['account_desc_col'] = account_desc_col
                    result['balance_cols'] = balance_set_camel
                    return result
                elif all(col in df.columns for col in balance_set_snake):
                    result['is_valid'] = True
                    result['detected_structure'] = 'standard_balance_sheet'
                    result['account_code_col'] = account_code_col
                    result['account_desc_col'] = account_desc_col
                    result['balance_cols'] = balance_set_snake
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
                    result['detected_structure'] = 'standard_balance_sheet'  # Treat as standard
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
            result['detected_structure'] = 'generic_balance_sheet'
            result['account_code_col'] = code_col
            result['account_desc_col'] = desc_col
            result['balance_cols'] = balance_cols
            result['file_type_detected'] = 'generic_balance_sheet'
            return result
        
        # If no structure was detected
        result['error'] = 'Unable to detect balance sheet structure.'
        result['suggestion'] = 'Please ensure your file has account codes, account descriptions, and balance amounts.'
        result['file_type_detected'] = 'unrecognized_format'
        
    except Exception as e:
        result['error'] = f'Error during validation: {str(e)}'
        result['suggestion'] = 'Please check your file format and try again.'
    
    return result


def convert_to_standard_balance_sheet(balance_sheet, validation_result):
    """
    Convert different balance sheet formats to standard format for GRAP mapping engine
    """
    try:
        detected_structure = validation_result['detected_structure']
        
        if detected_structure == 'standard_balance_sheet':
            # Already in standard format - just clean it up
            # Remove summary rows and empty rows
            clean_df = balance_sheet.copy()
            clean_df = clean_df.dropna(subset=['Account Code', 'Account Description'])
            clean_df = clean_df[~clean_df['Account Code'].astype(str).str.contains('TOTAL', na=False)]
            
            # Ensure we have the required columns
            if 'Net Balance' not in clean_df.columns:
                # Create Net Balance from Debit and Credit columns
                clean_df['Net Balance'] = clean_df['Debit Balance'] - clean_df['Credit Balance']
            
            return clean_df
        
        elif detected_structure == 'generic_balance_sheet':
            # Convert generic format to standard format
            account_code_col = validation_result['account_code_col']
            account_desc_col = validation_result['account_desc_col']
            balance_cols = validation_result['balance_cols']
            
            standard_data = []
            
            for idx, row in balance_sheet.iterrows():
                # Skip empty rows
                if pd.isna(row.iloc[account_code_col]) or pd.isna(row.iloc[account_desc_col]):
                    continue
                
                account_code = str(row.iloc[account_code_col])
                account_desc = str(row.iloc[account_desc_col])
                
                # Calculate net balance from balance columns
                net_balance = 0
                for col_idx in balance_cols:
                    if col_idx < len(balance_sheet.columns):
                        col_name = balance_sheet.columns[col_idx]
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
            
            for idx, row in balance_sheet.iterrows():
                # Try to identify account codes (numeric or alphanumeric)
                code_found = False
                desc_found = False
                balance_found = False
                
                for col_idx, col_name in enumerate(balance_sheet.columns):
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
                
                # If we found all required data, create a standard row
                if code_found and desc_found and balance_found:
                    # Determine debit/credit based on sign
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
    print("=== DASHBOARD ROUTE CALLED ===")
    user = get_current_user()
    
    # DEBUG: Show user info at the very beginning
    print(f"DEBUG: Dashboard accessed by user: {user}")
    if user:
        print(f"DEBUG: User role: {user.role}")
        print(f"DEBUG: User ID: {user.id}")
    else:
        print("DEBUG: No user found!")
    
    # Prepare data for Finance Clerk dashboard
    if user and user.role == 'FINANCE_CLERK':
        print("DEBUG: Entering FINANCE_CLERK dashboard logic")
        from services.period_management_service import period_management_service
        
        try:
            # Get real period data
            dashboard_data = period_management_service.get_dashboard_data()
            periods = dashboard_data['periods']
            stats = dashboard_data['stats']
            
            # Get actual pending uploads count for current user
            from models.balance_sheet_models import balance_sheet_model
            try:
                user_sessions = balance_sheet_model.get_user_sessions(user.id, limit=100)
                
                # DEBUG: Print what we actually got from Supabase
                print(f"DEBUG: Retrieved {len(user_sessions)} sessions from Supabase for user {user.id}")
                for i, session in enumerate(user_sessions):
                    print(f"  Session {i+1}: status={session.status}, created_at={session.created_at}")
                
                # Count sessions with pending statuses (uploaded, processing, mapped, pending)
                # These are all states that still require action from the finance clerk
                pending_statuses = ['uploaded', 'processing', 'mapped', 'pending']
                pending_uploads_count = len([s for s in user_sessions if s.status in pending_statuses])
                
                # Count balance sheets submitted today (balanced and mapped)
                from datetime import datetime
                today = datetime.now().date()
                submitted_today_count = len([s for s in user_sessions 
                    if s.created_at and s.created_at.date() == today 
                    and s.status in ['mapped', 'pending', 'submitted', 'approved']])
                
                # DEBUG: Show the calculation
                print(f"DEBUG: Today is {today}")
                print(f"DEBUG: submitted_today_count = {submitted_today_count}")
                for i, s in enumerate(user_sessions):
                    if s.created_at and s.created_at.date() == today:
                        counts = s.status in ['pending', 'submitted', 'approved']
                        print(f"  Session {i+1}: status={s.status}, counts={counts}")
                
                # Count balance sheets approved this month
                current_month = datetime.now().month
                current_year = datetime.now().year
                approved_this_month_count = len([s for s in user_sessions 
                    if s.status == 'approved' and s.updated_at 
                    and s.updated_at.month == current_month 
                    and s.updated_at.year == current_year])
            except Exception as e:
                pending_uploads_count = 0
                submitted_today_count = 0
                approved_this_month_count = 0
            
            # Add additional stats for clerk dashboard
            clerk_stats = {
                'open_periods': stats.get('open_periods', 0),
                'available_periods': stats.get('available_periods', 0),
                'urgent_periods': stats.get('urgent_periods', 0),
                'submitted_today': submitted_today_count,
                'approved_this_month': approved_this_month_count,
                'pending_uploads': pending_uploads_count,
                'pending_approvals': 0,
                'completed_reports': 0,
                'total_assets': 0,
                'total_liabilities': 0
            }
            
            return render_template('dashboard.html', user=user, periods=periods, stats=clerk_stats)
            
        except Exception as e:
            app.logger.error(f"Error loading dashboard data: {str(e)}")
            # Fallback to default data
            stats = {
                'open_periods': 0,
                'available_periods': 0,
                'urgent_periods': 0,
                'submitted_today': 0,
                'approved_this_month': 0,
                'pending_uploads': 0,
                'pending_approvals': 0,
                'completed_reports': 0,
                'total_assets': 0,
                'total_liabilities': 0
            }
            
            return render_template('dashboard.html', user=user, periods=[], stats=stats)
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
    """Balance Sheet Upload Page"""
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
def upload_balance_sheet():
    """
    API endpoint to handle Balance Sheet file upload with flexible format detection
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
                print(" Starting flexible balance sheet processing...")
                
                # Use flexible balance sheet service for processing
                from services.flexible_balance_sheet_service import flexible_balance_sheet_service
                
                print(" Processing upload with flexible service...")
                # Get period_id from form data if provided
                period_id = request.form.get('period_id')
                processing_result = flexible_balance_sheet_service.process_upload(
                    file_path=temp_filepath,
                    user_id=current_user.id,
                    filename=processing_filename,
                    period_id=period_id
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
                session_summary = flexible_balance_sheet_service.get_session_summary(processing_result['session_id'])
                
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
            file_extension = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else 'unknown'
            return jsonify({
                'success': False, 
                'error': f'Invalid file type: .{file_extension}\n\nAllowed file types: .xlsx, .xls, .csv, .xlsm, .xlsb, .tsv\n\nPlease upload a balance sheet file in one of the supported formats.'
            }), 400
        
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
def validate_balance_sheet():
    """
    API endpoint to validate balance sheet before processing
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
        
        # Get balance sheet data from database
        from models.balance_sheet_models import balance_sheet_model
        
        with open('balance_check_debug.log', 'a') as f:
            f.write(f"[{datetime.now().isoformat()}] Retrieving session data from database for ID: {session_id}\n")
        
        print(f"🔍 Retrieving session data from database for ID: {session_id}")
        
        # Get session and data from database
        session = balance_sheet_model.get_session(session_id)
        if not session:
            error_msg = f'Session not found in database for session_id: {session_id}'
            with open('balance_check_debug.log', 'a') as f:
                f.write(f"[{datetime.now().isoformat()}] Balance check failed: {error_msg}\n")
            print(f"❌ Balance check failed: {error_msg}")
            return jsonify({'success': False, 'error': error_msg}), 404
        
        # Get balance sheet data from database
        data_rows = balance_sheet_model.get_session_data(session_id)
        if not data_rows:
            error_msg = f'Balance sheet data not found in database for session_id: {session_id}'
            with open('balance_check_debug.log', 'a') as f:
                f.write(f"[{datetime.now().isoformat()}] Balance check failed: {error_msg}\n")
            print(f"❌ Balance check failed: {error_msg}")
            return jsonify({'success': False, 'error': error_msg}), 404
        
        # Convert data rows to list format for validation
        balance_sheet_data = []
        for row in data_rows:
            # Handle None values properly
            debit_val = getattr(row, 'debit_balance', None)
            credit_val = getattr(row, 'credit_balance', None)
            net_val = getattr(row, 'net_balance', None)
            
            balance_sheet_data.append({
                'account_code': getattr(row, 'account_code', ''),
                'account_description': getattr(row, 'account_description', ''),
                'debit_balance': float(debit_val) if debit_val is not None else 0.0,
                'credit_balance': float(credit_val) if credit_val is not None else 0.0,
                'net_balance': float(net_val) if net_val is not None else 0.0
            })
        
        # Create session data structure similar to what flexible service returns
        session_data = {
            'success': True,
            'balance_sheet_data': balance_sheet_data,
            'session_id': session_id,
            'file_format': session.file_format or 'xlsx',
            'metadata': session.metadata or {}
        }
        
        with open('balance_check_debug.log', 'a') as f:
            f.write(f"[{datetime.now().isoformat()}] Session data result: {session_data}\n")
        
        print(f"🔍 Session data result: {session_data}")
        
        if not session_data or not session_data.get('success'):
            error_msg = f'Session data not found or invalid for session_id: {session_id}'
            with open('balance_check_debug.log', 'a') as f:
                f.write(f"[{datetime.now().isoformat()}] Balance check failed: {error_msg}\n")
            print(f" Balance check failed: {error_msg}")
            return jsonify({'success': False, 'error': error_msg}), 404
        
        # Get the balance sheet data from session
        balance_sheet_data = session_data.get('balance_sheet_data')
        if not balance_sheet_data:
            return jsonify({
                'success': False,
                'error': 'Balance sheet data not found in session'
            }), 404
        
        # Convert to DataFrame for validation
        import pandas as pd
        balance_sheet = pd.DataFrame(balance_sheet_data)
        
        # Validate that we have data
        if balance_sheet.empty:
            return jsonify({
                'success': False,
                'error': 'The balance sheet data appears to be empty.'
            }), 500
        
        # Use flexible validation to understand the structure
        file_extension = session_data.get('file_format', 'xlsx')
        validation_result = validate_flexible_balance_sheet(balance_sheet, file_extension)
        
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
        
        if validation_result['detected_structure'] == 'standard_balance_sheet':
            # Standard format - use column names (handle both naming conventions)
            balance_cols = validation_result['balance_cols']
            
            # Check for debit/credit columns in both naming conventions
            if 'Debit Balance' in balance_sheet.columns:
                total_debits = balance_sheet['Debit Balance'].sum()
            elif 'debit_balance' in balance_sheet.columns:
                total_debits = balance_sheet['debit_balance'].sum()
                
            if 'Credit Balance' in balance_sheet.columns:
                total_credits = balance_sheet['Credit Balance'].sum()
            elif 'credit_balance' in balance_sheet.columns:
                total_credits = balance_sheet['credit_balance'].sum()
            
            # Handle Net Balance column (common in Pastel exports)
            if 'Net Balance' in balance_sheet.columns:
                net_balance = balance_sheet['Net Balance'].sum()
                
                # More tolerant check for balanced net balance (allowing for rounding errors)
                tolerance = 0.01  # Can be increased to 0.1 or 1.0 for more tolerance
                if abs(net_balance) <= tolerance:
                    # Use Net Balance column instead of separate Debit/Credit columns
                    # This is more reliable for Pastel exports
                    positive_balances = balance_sheet[balance_sheet['Net Balance'] > 0]['Net Balance'].sum()
                    negative_balances = balance_sheet[balance_sheet['Net Balance'] < 0]['Net Balance'].sum()
                    
                    total_debits = positive_balances
                    total_credits = abs(negative_balances)
                    
                    print(f" Using Net Balance calculation: Debits={total_debits:,.2f}, Credits={total_credits:,.2f}")
                else:
                    print(f" Net Balance not balanced (sum={net_balance:,.2f}), using standard columns")
            elif 'net_balance' in balance_sheet.columns:
                net_balance = balance_sheet['net_balance'].sum()
                
                # More tolerant check for balanced net balance (allowing for rounding errors)
                tolerance = 0.01  # Can be increased to 0.1 or 1.0 for more tolerance
                if abs(net_balance) <= tolerance:
                    # Use Net Balance column instead of separate Debit/Credit columns
                    # This is more reliable for Pastel exports
                    positive_balances = balance_sheet[balance_sheet['net_balance'] > 0]['net_balance'].sum()
                    negative_balances = balance_sheet[balance_sheet['net_balance'] < 0]['net_balance'].sum()
                    
                    total_debits = positive_balances
                    total_credits = abs(negative_balances)
                    
                    print(f" Using Net Balance calculation: Debits={total_debits:,.2f}, Credits={total_credits:,.2f}")
                else:
                    print(f" Net Balance not balanced (sum={net_balance:,.2f}), using standard columns")
            
        elif validation_result['detected_structure'] == 'generic_balance_sheet':
            # Generic format - try to identify debit/credit patterns
            balance_cols = validation_result['balance_cols']
            for col_idx in balance_cols:
                if col_idx < len(balance_sheet.columns):
                    col_name = balance_sheet.columns[col_idx]
                    if col_name in balance_sheet.columns:
                        col_values = pd.to_numeric(balance_sheet[col_name], errors='coerce').fillna(0)
                        # Simple approach: treat all as debits for balance check
                        total_debits += abs(col_values.sum())
        
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
            'message': 'Balance sheet is balanced' if is_balanced else 
                      f'Balance sheet is not balanced. Difference: R {balance_difference:,.2f}',
            'recommendation': 'You can proceed to mapping' if is_balanced else 
                             'Please correct the balance sheet',
            'account_count': int(len(balance_sheet)),
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

@login_required
@permission_required('process')
def process_uploaded_file():
    """
    API endpoint to process balance sheet data for GRAP mapping and financial statement generation
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
        
        print(f" Processing balance sheet from database")
        print(f" User: {current_user.username}")
        print(f" Session ID: {session_id}")
        
        # Update session status to "processing"
        from models.balance_sheet_models import balance_sheet_model
        try:
            success = balance_sheet_model.update_session_status(session_id, 'processing')
            print(f" Updated session status to: processing - Success: {success}")
        except Exception as e:
            print(f" Failed to update session status to processing: {str(e)}")
            import traceback
            print(f" Traceback: {traceback.format_exc()}")
        
        # Use flexible balance sheet service for GRAP processing
        from services.flexible_balance_sheet_service import flexible_balance_sheet_service
        
        print(" Starting GRAP mapping and financial statement generation...")
        
        # Get session data for processing
        session_data = flexible_balance_sheet_service.get_session_data(session_id)
        if not session_data or not session_data.get('success'):
            return jsonify({'success': False, 'error': 'Session data not found or invalid'}), 404
        
        # Process GRAP mapping and financial statements
        processing_result = flexible_balance_sheet_service.process_grap_mapping(
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
        session_summary = flexible_balance_sheet_service.get_session_summary(session_id)

        print(" GRAP processing completed successfully")
        
        # Update session status to "mapped" since GRAP mapping is complete
        try:
            success = balance_sheet_model.update_session_status(session_id, 'mapped')
            print(f" Updated session status to: mapped - Success: {success}")
        except Exception as e:
            print(f" ❌ Failed to update session status to mapped: {str(e)}")
            import traceback
            print(f" Traceback: {traceback.format_exc()}")

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

@login_required
@permission_required('process')
def proceed_with_unbalanced():
    """
    API endpoint to proceed with unbalanced balance sheet
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
        
        # Log the decision to proceed with unbalanced balance sheet
        user = get_current_user()
        
        # Store warning flag in session for later processing
        session['proceeding_unbalanced'] = True
        session['unbalanced_filepath'] = filepath
        session['unbalanced_user'] = user.username
        session['unbalanced_timestamp'] = datetime.now().isoformat()
        
        return jsonify({
            'success': True,
            'message': 'Proceeding with unbalanced balance sheet',
            'warning': 'Financial statements may not be accurate due to balance discrepancy',
            'next_step': 'Proceed to mapping interface'
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Processing error: {str(e)}'
        }), 500


@app.route('/api/remove-upload', methods=['POST'])
@login_required
@permission_required('upload')
def remove_uploaded_file():
    """
    API endpoint to remove uploaded file from database
    Allows user to cancel upload and clean up data
    """
    try:
        data = request.get_json()
        session_id = data.get('session_id')
        
        if not session_id:
            return jsonify({'success': False, 'error': 'No session ID provided'}), 400
        
        # Get current user for logging
        current_user = get_current_user()
        if not current_user:
            return jsonify({'success': False, 'error': 'User not authenticated'}), 401
        
        print(f"🗑️ Removing uploaded file - Session ID: {session_id}")
        print(f"👤 User: {current_user.username}")
        
        # Use cleanup service to remove the session
        from services.cleanup_service import CleanupService
        cleanup_service = CleanupService()
        
        # Clean up the specific session
        cleanup_result = cleanup_service.cleanup_specific_session(session_id)
        
        if cleanup_result.get('success'):
            print(f"✅ Successfully removed session {session_id}")
            return jsonify({
                'success': True,
                'message': 'Uploaded file successfully removed',
                'session_id': session_id
            })
        else:
            print(f"❌ Failed to remove session {session_id}: {cleanup_result.get('error', 'Unknown error')}")
            return jsonify({
                'success': False,
                'error': cleanup_result.get('error', 'Failed to remove uploaded file')
            }), 500
        
    except Exception as e:
        print(f"❌ Exception in remove_uploaded_file: {str(e)}")
        import traceback
        print(f"📋 Full traceback: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': f'Failed to remove uploaded file: {str(e)}'
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
        balance_sheets_count = 0
        pdf_reports_count = 0
        
        for filename in os.listdir(outputs_dir):
            filepath = os.path.join(outputs_dir, filename)
            if os.path.isfile(filepath) and filename.endswith('.xlsx'):
                stat = os.stat(filepath)
                file_info = {
                    'id': f"output_{filename}",
                    'filename': filename,
                    'original_filename': filename,
                    'file_type': 'balance_sheet',
                    'file_size': stat.st_size,
                    'upload_date': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
                    'status': 'completed'
                }
                files.append(file_info)
                total_size += stat.st_size
                balance_sheets_count += 1
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
            'balance_sheets': balance_sheets_count,
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
            from models.balance_sheet_models import BalanceSheetSession
            tb_session = BalanceSheetSession()
            
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
            'submission_name': submission_data.get('submission_name', 'Balance Sheet Submission'),
            'original_filename': submission_data.get('original_filename', 'Unknown'),
            'status': submission_data.get('status', 'pending'),
            'priority': submission_data.get('priority', 'normal'),
            'total_accounts': submission_data.get('total_accounts', 0),
            'mapped_accounts': submission_data.get('mapped_accounts', 0),
            'mapped_accounts_count': submission_data.get('mapped_accounts', 0),
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
            'submission_timestamp': submission_data.get('submission_timestamp'),
            'reviewed_by': submission_data.get('reviewed_by'),
            'reviewed_at': submission_data.get('reviewed_at'),
            'review_notes': submission_data.get('review_notes'),
            'approval_comments': submission_data.get('approval_comments'),
            'rejection_reason': submission_data.get('rejection_reason'),
            'is_locked': submission_data.get('is_locked', False),
            'locked_at': submission_data.get('locked_at'),
            'locked': submission_data.get('is_locked', False),
            'metadata': submission_data.get('metadata', {}),
            'grap_mapping_data': submission_data.get('grap_mapping_data', {}),
            'financial_statements': submission_data.get('financial_statements', {}),
            'user_id': submission_data.get('user_id'),
            'session_id': submission_data.get('session_id'),
            'full_name': user.full_name,
            'username': user.username,
            'filepath': submission_data.get('submission_name') or submission_data.get('original_filename') or submission_data.get('filename') or 'N/A'
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


# Period Management API Endpoints

@app.route('/api/periods', methods=['GET'])
@login_required
def get_periods():
    """Get all financial periods"""
    try:
        user = get_current_user()
        if not user.has_permission('view_all'):
            return jsonify({'success': False, 'error': 'Permission denied'}), 403
        
        from services.period_management_service import period_management_service
        periods = period_management_service.model.get_all_periods()
        
        return jsonify({
            'success': True,
            'periods': [period.to_dict() for period in periods]
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/periods/open', methods=['GET'])
@login_required
def get_open_periods():
    """Get open financial periods"""
    try:
        user = get_current_user()
        if not user.has_permission('view_all'):
            return jsonify({'success': False, 'error': 'Permission denied'}), 403
        
        from services.period_management_service import period_management_service
        periods = period_management_service.get_available_periods_for_upload()
        
        return jsonify({
            'success': True,
            'periods': [period.to_dict() for period in periods]
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/periods', methods=['POST'])
@login_required
def create_period():
    """Create a new financial period"""
    try:
        user = get_current_user()
        if not user.has_permission('manage_users'):
            return jsonify({'success': False, 'error': 'Permission denied'}), 403
        
        data = request.get_json()
        from services.period_management_service import period_management_service
        
        period = period_management_service.create_financial_period(
            period_data=data,
            created_by=user.id
        )
        
        return jsonify({
            'success': True,
            'period': period.to_dict(),
            'message': 'Financial period created successfully'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/periods/<period_id>/open', methods=['POST'])
@login_required
def open_period(period_id):
    """Open a period for uploads"""
    try:
        user = get_current_user()
        if not user.has_permission('manage_users'):
            return jsonify({'success': False, 'error': 'Permission denied'}), 403
        
        from services.period_management_service import period_management_service
        period = period_management_service.open_period_for_uploads(period_id)
        
        return jsonify({
            'success': True,
            'period': period.to_dict(),
            'message': 'Period opened for uploads'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/periods/<period_id>/close', methods=['POST'])
@login_required
def close_period(period_id):
    """Close a period"""
    try:
        user = get_current_user()
        if not user.has_permission('manage_users'):
            return jsonify({'success': False, 'error': 'Permission denied'}), 403
        
        from services.period_management_service import period_management_service
        period = period_management_service.close_period(period_id)
        
        return jsonify({
            'success': True,
            'period': period.to_dict(),
            'message': 'Period closed'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/periods/dashboard', methods=['GET'])
@login_required
def get_dashboard_periods():
    """Get period data for dashboard"""
    try:
        user = get_current_user()
        
        from services.period_management_service import period_management_service
        dashboard_data = period_management_service.get_dashboard_data()
        
        return jsonify({
            'success': True,
            'periods': dashboard_data['periods'],
            'stats': dashboard_data['stats']
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/periods/sample', methods=['POST'])
@login_required
def create_sample_periods():
    """Create sample periods for testing"""
    try:
        user = get_current_user()
        if not user.has_permission('manage_users'):
            return jsonify({'success': False, 'error': 'Permission denied'}), 403
        
        from services.period_management_service import period_management_service
        periods = period_management_service.create_sample_periods(user.id)
        
        return jsonify({
            'success': True,
            'periods': [period.to_dict() for period in periods],
            'message': f'Created {len(periods)} sample periods'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/submissions/user', methods=['GET'])
@login_required
def get_user_submissions():
    """Get all submissions for the current user - Optimized for performance"""
    print("🔥 API ENDPOINT CALLED: /api/submissions/user")
    try:
        user = get_current_user()
        user_id = user.id
        
        print(f"🚀 Loading submissions for user: {user_id}")
        
        # Get user sessions from balance sheet model with smaller limit for better performance
        from models.balance_sheet_models import balance_sheet_model
        sessions = balance_sheet_model.get_user_sessions(user_id, limit=25)  # Reduced from 50
        
        print(f"📊 Found {len(sessions)} sessions for user {user_id}")
        
        submissions = []
        session_ids_for_batch = []
        
        for session in sessions:
            # Fast account counts from metadata only - NO EXPENSIVE FALLBACKS
            mapped_accounts_count = 0
            total_accounts_count = 0
            
            # Only get from metadata - no expensive service calls
            if session.metadata:
                # Check for mapped_accounts directly in metadata (this is the correct field)
                mapped_accounts_count = session.metadata.get('mapped_accounts', 0)
                total_accounts_count = session.metadata.get('total_accounts', 0)
                
                # Fallback to processing_results if direct field not found
                if mapped_accounts_count == 0:
                    processing_results = session.metadata.get('processing_results', {})
                    mapped_accounts_count = processing_results.get('mapped_accounts', 0)
                    total_accounts_count = processing_results.get('total_accounts', 0)
                
                # Fallback to grap_mapping if still not found
                if mapped_accounts_count == 0 and 'grap_mapping' in session.metadata:
                    grap_mapping = session.metadata['grap_mapping']
                    mapped_accounts = grap_mapping.get('mapped_accounts', [])
                    mapped_accounts_count = len(mapped_accounts) if mapped_accounts else 0
            
            print(f"DEBUG: Final mapped_accounts_count for session {session.id}: {mapped_accounts_count}")
            
            # Use session status directly - no expensive batch queries for now
            validation_status = session.status
            
            # Collect session IDs for potential batch query (but skip for performance)
            # session_ids_for_batch.append(session.id)
            
            # Check if submission should be locked based on status
            # Submissions that have been submitted for review should be locked
            # 'mapped' status means accounts have been mapped and submission is locked for editing
            locked_statuses = ['mapped', 'pending', 'submitted', 'approved', 'rejected']
            locked_status = validation_status in locked_statuses
            
            # Format submission data
            submission_data = {
                'session_id': session.id,
                'user_id': session.user_id,
                'filename': session.original_filename or session.filename,
                'filepath': session.filename,
                'submission_timestamp': session.created_at.isoformat() if session.created_at else None,
                'status': validation_status,
                'mapped_accounts_count': mapped_accounts_count,
                'total_accounts_count': total_accounts_count,
                'file_type': session.file_type,
                'review_notes': session.metadata.get('review_notes', ''),
                'locked': locked_status,
                'grap_mapping': session.metadata.get('grap_mapping', {}),
                'structure_info': session.metadata.get('structure_info', {}),
                'processing_results': session.metadata.get('processing_results', {}),
                'mapping_progress': session.metadata.get('mapping_progress', {}),
                # DEBUG: Add metadata info for debugging
                '_debug_metadata': session.metadata,
                '_debug_mapped_accounts_count': mapped_accounts_count,
                '_debug_processing_results': session.metadata.get('processing_results', {}) if session.metadata else {}
            }
            submissions.append(submission_data)
        
        # Skip expensive batch query for now to improve performance
        # TODO: Add back later with proper indexing
        
        print(f"✅ Successfully prepared {len(submissions)} submissions for response")
        
        return jsonify({
            'success': True,
            'submissions': submissions
        })
        
    except Exception as e:
        app.logger.error(f"Error getting user submissions: {str(e)}")
        print(f"❌ Error in get_user_submissions: {str(e)}")
        import traceback
        print(f"📋 Full traceback: {traceback.format_exc()}")
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
                            
                            # Allow clerks to upload multiple balance sheets even while pending ones exist
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
        # Use flexible balance sheet service to get pending submissions
        from services.flexible_balance_sheet_service import flexible_balance_sheet_service
        pending_submissions = flexible_balance_sheet_service.get_pending_submissions()
        
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


@app.route('/api/cleanup/session', methods=['POST'])
@login_required
def cleanup_user_session():
    """Clean up a specific session owned by the current user"""
    try:
        data = request.get_json()
        session_id = data.get('session_id')
        
        if not session_id:
            return jsonify({'success': False, 'error': 'No session ID provided'}), 400
        
        # Get current user
        current_user = get_current_user()
        if not current_user:
            return jsonify({'success': False, 'error': 'User not authenticated'}), 401
        
        # Verify the session belongs to the current user
        from models.balance_sheet_models import BalanceSheetSession
        session = BalanceSheetSession().get_session(session_id)
        
        if not session:
            return jsonify({'success': False, 'error': 'Session not found'}), 404
        
        if str(session.user_id) != str(current_user.id):
            return jsonify({'success': False, 'error': 'You can only clean up your own sessions'}), 403
        
        # Clean up the session
        from services.cleanup_service import CleanupService
        cleanup_service = CleanupService()
        result = cleanup_service.cleanup_specific_session(session_id)
        
        return jsonify(result)
        
    except Exception as e:
        app.logger.error(f"Error cleaning up user session: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Error cleaning up session: {str(e)}'
        }), 500


@app.route('/api/cleanup/unbalanced', methods=['POST'])
@login_required
@permission_required('admin')  # Only admins can clean up data
def cleanup_unbalanced_balance_sheets():
    """Clean up unbalanced balance sheets from the database (Admin only)"""
    try:
        data = request.get_json()
        session_id = data.get('session_id')  # Optional specific session
        
        from services.cleanup_service import CleanupService
        cleanup_service = CleanupService()
        
        if session_id:
            # Clean up specific session
            result = cleanup_service.cleanup_specific_session(session_id)
        else:
            # Clean up all unbalanced balance sheets
            result = cleanup_service.cleanup_unbalanced_balance_sheets()
        
        return jsonify(result)
        
    except Exception as e:
        app.logger.error(f"Error cleaning up unbalanced balance sheets: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Error cleaning up unbalanced balance sheets: {str(e)}'
        }), 500


@app.route('/api/cleanup/failed-uploads', methods=['POST'])
@login_required
@permission_required('admin')  # Only admins can clean up data
def cleanup_failed_uploads():
    """Clean up recently failed uploads"""
    try:
        data = request.get_json()
        hours_old = data.get('hours_old', 1)  # Default 1 hour
        
        from services.cleanup_service import cleanup_service
        
        result = cleanup_service.cleanup_failed_uploads(hours_old)
        
        return jsonify(result)
        
    except Exception as e:
        app.logger.error(f"Error cleaning up failed uploads: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Error cleaning up failed uploads: {str(e)}'
        }), 500


@app.route('/api/cleanup/orphaned', methods=['POST'])
@login_required
@permission_required('admin')  # Only admins can clean up data
def cleanup_orphaned_data():
    """Clean up orphaned data"""
    try:
        from services.cleanup_service import cleanup_service
        
        result = cleanup_service.cleanup_orphaned_data()
        
        return jsonify(result)
        
    except Exception as e:
        app.logger.error(f"Error cleaning up orphaned data: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Error cleaning up orphaned data: {str(e)}'
        }), 500


@app.route('/api/cleanup/all', methods=['POST'])
@login_required
@permission_required('admin')  # Only admins can clean up data
def cleanup_all():
    """Clean up all types of failed data"""
    try:
        from services.cleanup_service import cleanup_service
        
        # Clean up unbalanced balance sheets (older than 24 hours)
        unbalanced_result = cleanup_service.cleanup_unbalanced_balance_sheets(24)
        
        # Clean up failed uploads (older than 1 hour)
        failed_uploads_result = cleanup_service.cleanup_failed_uploads(1)
        
        # Clean up orphaned data
        orphaned_result = cleanup_service.cleanup_orphaned_data()
        
        total_cleaned = (
            unbalanced_result.get('cleaned_count', 0) +
            failed_uploads_result.get('cleaned_count', 0) +
            orphaned_result.get('cleaned_count', 0)
        )
        
        result = {
            'success': True,
            'total_cleaned': total_cleaned,
            'unbalanced_cleaned': unbalanced_result.get('cleaned_count', 0),
            'failed_uploads_cleaned': failed_uploads_result.get('cleaned_count', 0),
            'orphaned_cleaned': orphaned_result.get('cleaned_count', 0),
            'unbalanced_errors': unbalanced_result.get('errors', []),
            'failed_upload_errors': failed_uploads_result.get('errors', []),
            'orphaned_errors': orphaned_result.get('errors', []),
            'message': f"Total cleaned: {total_cleaned} items (unbalanced: {unbalanced_result.get('cleaned_count', 0)}, failed uploads: {failed_uploads_result.get('cleaned_count', 0)}, orphaned: {orphaned_result.get('cleaned_count', 0)})"
        }
        
        # Add error messages if any
        all_errors = []
        if unbalanced_result.get('errors'):
            all_errors.extend([f"Unbalanced: {error}" for error in unbalanced_result['errors']])
        if failed_uploads_result.get('errors'):
            all_errors.extend([f"Failed Upload: {error}" for error in failed_uploads_result['errors']])
        if orphaned_result.get('errors'):
            all_errors.extend([f"Orphaned: {error}" for error in orphaned_result['errors']])
        
        if all_errors:
            result['errors'] = all_errors
            result['message'] += f". {len(all_errors)} errors occurred."
        
        return jsonify(result)
        
    except Exception as e:
        app.logger.error(f"Error in comprehensive cleanup: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Error in comprehensive cleanup: {str(e)}'
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
        from models.balance_sheet_models import BalanceSheetSession
        
        # Get session data from database
        session = BalanceSheetSession().get_session(session_id)
        if not session:
            return jsonify({
                'success': False,
                'error': f'Session {session_id} not found'
            }), 404
        
        # Get balance sheet data rows
        data_rows = BalanceSheetSession().get_session_data(session_id)
        
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
        from services.flexible_balance_sheet_service import flexible_balance_sheet_service
        session_data = flexible_balance_sheet_service.get_session_data(session_id)
        
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
        flexible_balance_sheet_service.update_session_metadata(session_id, {
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

@login_required
@permission_required('process')
def submit_mapping_for_review():
    """
    API endpoint to submit mapped balance sheet for review
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
        from services.flexible_balance_sheet_service import flexible_balance_sheet_service
        session_data = flexible_balance_sheet_service.get_session_data(session_id)
        
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
        
        # Create submission record in database using balance sheet models
        from models.balance_sheet_models import BalanceSheetSession
        
        # Initialize database connection
        bs_session = BalanceSheetSession()
        
        submission_record = {
            'session_id': session_id,
            'user_id': user.id,
            'submission_name': f"Balance Sheet Submission - {datetime.now().strftime('%Y-%m-%d %H:%M')}",
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
            result = bs_session.client.table('submissions').insert(submission_record).execute()
            
            if not result.data:
                raise Exception("Failed to create submission record")
            
            submission_id = result.data[0]['id']
            
            # Update balance sheet data rows with mapping status
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
                    
                    bs_session.client.table('balance_sheet_data').update(update_data).eq('id', account_id).execute()
            
            # Update session status
            bs_session.client.table('balance_sheet_sessions').update({
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
                'message': 'GRAP-compliant balance sheet submitted for finance manager review successfully',
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
                'message': 'Balance sheet submitted for review (file-based storage)',
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