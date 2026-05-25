"""

Varydian Financial Reporting System - Flask Routes with Authentication

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
import uuid



# Import our Phase 1 mapping engine and auth models

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.grap_models import GRAPMappingEngine

from models.supabase_auth_models import supabase_auth, SupabaseUser, get_role_description, get_role_color, get_role_label

from services.grap_mapping_service import grap_mapping_service

from services.approval_facade import approval_facade

from utils.constants import WorkflowErrorMessages



# Import formula transparency blueprint

from controllers.routes_formula import formula_bp



# Set up logging

logger = logging.getLogger(__name__)



# Configuration

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

app = Flask(__name__, 

           template_folder='../templates', 

           static_folder='../static',

           static_url_path='/static')

app.config['SECRET_KEY'] = 'varydian-demo-2025-secure-key-auth-enabled'

app.config['UPLOAD_FOLDER'] = os.path.join(_PROJECT_ROOT, 'uploads')

app.config['OUTPUT_FOLDER'] = os.path.join(_PROJECT_ROOT, 'outputs')

os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)

app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

app.config['DEBUG'] = True  # Enable debug logging

app.jinja_env.globals['get_role_label'] = get_role_label


app.register_blueprint(formula_bp)


from utils.datetime_display import format_display_datetime, format_display_date_range


@app.template_filter('display_datetime')
def display_datetime_filter(value):
    return format_display_datetime(value)


@app.template_filter('display_date_range')
def display_date_range_filter(start, end=None):
    return format_display_date_range(start, end)


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

                        if (str_val.isdigit() and len(str_val) >= 3) or (any(c.isalpha() for c in str_val) and any(c.isdigit() for c in str_val)):

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





def permission_required(*permissions):

    """Decorator — user must have at least one of the listed permissions."""

    required = permissions or ('',)

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

                if not any(user.has_permission(p) for p in required):

                    label = ' or '.join(p.upper() for p in required)

                    return jsonify({'success': False, 'error': f'Permission denied. {label} access required.'}), 403

                

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


@app.context_processor
def inject_template_globals():
    """Expose current_user and role helpers to all Jinja templates (base.html, dashboard, etc.)."""
    return {
        'current_user': get_current_user(),
        'get_role_description': get_role_description,
        'get_role_color': get_role_color,
        'get_role_label': get_role_label,
    }


# Authentication Routes

@app.route('/login', methods=['GET', 'POST'])

def login():

    """Login page"""

    if request.method == 'POST':

        username = request.form.get('username')

        password = request.form.get('password')

        

        user_data = supabase_auth.verify_password(username, password)

        

        if user_data and user_data['is_active']:
            print(f"DEBUG: User authenticated: {user_data['id']}")

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
            print(f"DEBUG: User authenticated: {user_data['id']}")

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

                'can_download_pdf': user.can_download_pdf(),

                'can_access_export_center': user.can_access_export_center(),

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

        

        periods = []
        period_stats = {
            'open_periods': 0,
            'available_periods': 0,
            'urgent_periods': 0,
        }
        submission_counts = {
            'pending_uploads': 0,
            'submitted_today': 0,
            'approved_this_month': 0,
        }

        try:
            dashboard_data = period_management_service.get_dashboard_data()
            periods = dashboard_data.get('periods', [])
            period_stats = dashboard_data.get('stats', period_stats)
        except Exception as e:
            app.logger.error(f"Error loading period dashboard data: {str(e)}")

        try:
            from models.balance_sheet_models import balance_sheet_model
            from models.income_statement_models import income_statement_model
            from models.budget_report_models import budget_report_model
            from utils.session_workflow import clerk_submission_stats

            user_sessions = (
                balance_sheet_model.get_user_sessions(user.id, limit=100)
                + income_statement_model.get_user_sessions(user.id, limit=100)
                + budget_report_model.get_user_sessions(user.id, limit=100)
            )
            submission_counts = clerk_submission_stats(user_sessions)
        except Exception as e:
            app.logger.error(f"Error loading clerk submission stats: {str(e)}")

        clerk_stats = {
            'open_periods': period_stats.get('open_periods', 0),
            'available_periods': period_stats.get('available_periods', 0),
            'urgent_periods': period_stats.get('urgent_periods', 0),
            'submitted_today': submission_counts.get('submitted_today', 0),
            'approved_this_month': submission_counts.get('approved_this_month', 0),
            'pending_uploads': submission_counts.get('pending_uploads', 0),
            'pending_approvals': 0,
            'completed_reports': 0,
            'total_assets': 0,
            'total_liabilities': 0,
        }

        return render_template(
            'dashboard.html', user=user, current_user=user, periods=periods, stats=clerk_stats
        )

    if user and user.role == 'CFO':
        cfo_kpis = {
            'pending_finalization_count': 0,
            'surplus_deficit_total': None,
            'surplus_deficit_submission_count': 0,
            'budget_variance_total': None,
            'budget_variance_submission_count': 0,
        }
        try:
            from services.universal_workflow_service import UniversalWorkflowService

            kpi_result = UniversalWorkflowService().get_cfo_dashboard_kpis(user.id)
            if kpi_result.get('success'):
                cfo_kpis = kpi_result
        except Exception as e:
            app.logger.error(f"Error loading CFO dashboard KPIs: {str(e)}")

        stats = {
            'open_periods': 0,
            'pending_uploads': 0,
            'pending_approvals': cfo_kpis.get('pending_finalization_count', 0),
            'completed_reports': 0,
            'total_assets': 0,
            'total_liabilities': 0,
        }
        return render_template(
            'dashboard.html',
            user=user,
            current_user=user,
            stats=stats,
            cfo_kpis=cfo_kpis,
        )

    if user and user.role == 'ASSET_MANAGER':
        asset_stats = {}
        try:
            from services.asset_register_service import asset_register_service

            asset_register_service.seed_demo_assets_if_empty(user.id)
            stats_result = asset_register_service.get_dashboard_stats(user.id)
            if stats_result.get('success'):
                asset_stats = stats_result
        except Exception as e:
            app.logger.error(f"Error loading asset manager dashboard: {str(e)}")

        stats = {
            'open_periods': 0,
            'pending_uploads': 0,
            'pending_approvals': asset_stats.get('pending_journals_total', 0),
            'completed_reports': 0,
            'total_assets': asset_stats.get('asset_count', 0),
            'total_liabilities': 0,
        }
        return render_template(
            'dashboard.html',
            user=user,
            current_user=user,
            stats=stats,
            asset_stats=asset_stats,
        )

    if user and user.role == 'AUDITOR':
        auditor_stats = {'finalized_count': 0}
        try:
            from services.export_center_service import export_center_service

            sessions = export_center_service.list_exportable_sessions(limit=200)
            auditor_stats = {
                'finalized_count': len(sessions),
                'success': True,
            }
        except Exception as e:
            app.logger.error(f"Error loading auditor dashboard: {str(e)}")

        stats = {
            'open_periods': 0,
            'pending_uploads': 0,
            'pending_approvals': 0,
            'completed_reports': auditor_stats.get('finalized_count', 0),
            'total_assets': 0,
            'total_liabilities': 0,
        }
        return render_template(
            'dashboard.html',
            user=user,
            current_user=user,
            stats=stats,
            auditor_stats=auditor_stats,
        )

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

        

        return render_template('dashboard.html', user=user, current_user=user, stats=stats)





@app.route('/approvals')

@login_required

def approvals_page():

    """Statement review host (?review=statement). Queue/history live on FM routes."""

    user = get_current_user()

    review_statement = request.args.get('review') == 'statement'

    if review_statement and user.role == 'FINANCE_CLERK' and user.has_permission('process'):
        return render_template('approvals.html', user=user)

    if review_statement and user.role == 'AUDITOR' and user.can_access_audit_workspace():
        return render_template('approvals.html', user=user)

    if not user.can_review():

        flash('Access denied. Finance Manager or CFO privileges required.', 'error')

        return redirect(url_for('dashboard'))

    if not review_statement:

        if user.role == 'FINANCE_MANAGER':

            return redirect(url_for('finance_manager_review_queue'))

        if user.role == 'CFO':

            return redirect(url_for('finance_manager_review_queue'))

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
@app.route('/mapping-interface')
@app.route('/mapping/<session_id>')

@login_required

def mapping_page(session_id=None):

    """Account Mapping Interface Page"""

    user = get_current_user()

    if not user.can_process():

        flash('You do not have permission to access mapping interface.', 'error')

        return redirect(url_for('dashboard'))

    from utils.session_workflow import normalize_mapping_session_id

    if session_id is None:
        session_id = request.args.get('session_id')
    session_id = normalize_mapping_session_id(session_id) or ''

    return render_template('mapping_interface.html', user=user, session_id=session_id)





@app.route('/finance-clerk-workflow')
@login_required
def finance_clerk_workflow():
    """Legacy bookmark → clerk submission history."""
    denied = _finance_clerk_page_guard(get_current_user())
    if denied:
        return denied
    return redirect(url_for('submission_history_page'))


def _finance_clerk_page_guard(user):
    """Redirect non-clerks away from clerk-only pages."""
    if user and user.role == 'FINANCE_CLERK':
        return None
    flash('Access denied. Finance Clerk privileges required.', 'error')
    if user and user.can_review():
        return redirect(url_for('finance_manager_history'))
    return redirect(url_for('dashboard'))


def _finance_clerk_api_guard(user):
    """JSON guard for clerk-only submission list APIs."""
    if user and user.role == 'FINANCE_CLERK':
        return None
    return jsonify({
        'success': False,
        'error': 'Finance Clerk privileges required.',
    }), 403





@app.route('/api/upload', methods=['POST'])
def upload_balance_sheet():
    """Deprecated — use POST /api/universal/upload (all document types)."""
    return jsonify({
        'success': False,
        'error': 'This endpoint is deprecated. Use POST /api/universal/upload with document_type in form data.',
        'deprecated': True,
        'replacement': '/api/universal/upload',
    }), 410


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

            'allow_proceed_with_warning': False,

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

        user = get_current_user()

        if user and user.role == 'FINANCE_CLERK':

            return jsonify({

                'success': False,

                'error': 'Trial balance must be balanced. Debits must equal credits before processing.',

            }), 400

        

        # Log the decision to proceed with unbalanced balance sheet

        

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

    """Generate PDF financial statements (requires locked reporting period)."""

    try:

        data = request.get_json()

        results_file = data.get('results_file')
        session_id = data.get('session_id')
        document_type = data.get('document_type')
        period_id = data.get('period_id')

        

        if not results_file:

            return jsonify({'success': False, 'error': 'No results file specified'}), 400

        from utils.pdf_availability import resolve_pdf_availability

        availability = resolve_pdf_availability(
            session_id=session_id,
            document_type=document_type,
            period_id=period_id,
        )
        if not availability["can_generate_pdf"]:
            return jsonify({
                'success': False,
                'error': availability["reason"],
                'period_locked': availability["period_locked"],
            }), 403

        

        results_path = os.path.join('data', results_file)

        

        if not os.path.exists(results_path):

            return jsonify({'success': False, 'error': 'Results file not found'}), 404

        

        # Load results

        with open(results_path, 'r') as f:

            results = json.load(f)

        

        # Generate PDF

        pdf_filename = f"Varydian_AFS_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"

        pdf_path = os.path.join(app.config['OUTPUT_FOLDER'], pdf_filename)

        

        # Import PDF generation function

        from models.grap_models import generate_pdf_report

        generate_pdf_report(results, pdf_path)

        current_user = get_current_user()
        user_id = current_user.id if current_user else session.get('user_id')
        from utils.pdf_download_guard import write_pdf_download_meta

        write_pdf_download_meta(
            app.config['OUTPUT_FOLDER'],
            pdf_filename,
            session_id=session_id,
            document_type=document_type,
            period_id=period_id,
            user_id=user_id,
        )

        download_q = []
        if session_id:
            download_q.append(f'session_id={session_id}')
        if document_type:
            download_q.append(f'document_type={document_type}')
        download_suffix = f'?{"&".join(download_q)}' if download_q else ''

        return jsonify({

            'success': True,

            'pdf_filename': pdf_filename,

            'download_url': f'/download/{pdf_filename}{download_suffix}'

        })

    

    except Exception as e:

        return jsonify({

            'success': False,

            'error': f'PDF generation error: {str(e)}'

        }), 500


@app.route('/api/pdf/availability', methods=['GET'])
@login_required
def pdf_availability():
    """Check whether PDF generation/download is allowed (period must be locked by CFO)."""
    session_id = request.args.get('session_id')
    document_type = request.args.get('document_type')
    period_id = request.args.get('period_id')
    from utils.pdf_availability import resolve_pdf_availability
    result = resolve_pdf_availability(
        session_id=session_id,
        document_type=document_type,
        period_id=period_id,
    )
    user = get_current_user()
    period_ok = bool(result.get('period_locked'))
    if user:
        result['can_generate_pdf'] = period_ok and user.can_generate_pdf()
        result['can_download_pdf'] = period_ok and user.can_download_pdf()
    else:
        result['can_generate_pdf'] = False
        result['can_download_pdf'] = False
    return jsonify({'success': True, **result})



@app.route('/download/<filename>')

@login_required

def download_file(filename):

    """

    Download generated PDF (requires locked reporting period).

    """

    filepath = os.path.join(app.config['OUTPUT_FOLDER'], os.path.basename(filename))

    

    if not os.path.isfile(filepath):

        return "File not found", 404

    from utils.pdf_download_guard import verify_pdf_download_allowed

    current_user = get_current_user()
    if not current_user or not current_user.can_download_pdf():
        return jsonify({'success': False, 'error': 'Permission denied. PDF download access required.'}), 403

    user_id = current_user.id if current_user else session.get('user_id')
    allowed, err = verify_pdf_download_allowed(
        app.config['OUTPUT_FOLDER'],
        filename,
        session_id=request.args.get('session_id'),
        document_type=request.args.get('document_type'),
        period_id=request.args.get('period_id'),
        user_id=user_id,
    )
    if not allowed:
        return jsonify({'success': False, 'error': err, 'period_locked': True}), 403

    try:
        from utils.pdf_download_guard import read_pdf_download_meta
        from services.export_log_service import export_log_service

        meta = read_pdf_download_meta(app.config['OUTPUT_FOLDER'], filename) or {}
        sid = request.args.get('session_id') or meta.get('session_id')
        dtype = request.args.get('document_type') or meta.get('document_type')
        if sid and dtype:
            export_log_service.record(
                export_format='pdf_download',
                session_id=sid,
                document_type=dtype,
                user_id=user_id,
                user_name=current_user.full_name if current_user else '',
                user_role=current_user.role if current_user else '',
                filename=os.path.basename(filename),
                ip_address=request.remote_addr,
                user_agent=(request.headers.get('User-Agent') or '')[:500],
            )
    except Exception as log_exc:
        app.logger.warning('Export log (pdf download) failed: %s', log_exc)

    return send_file(filepath, as_attachment=True, download_name=os.path.basename(filename))





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
    denied = _finance_clerk_page_guard(user)
    if denied:
        return denied

    # Calculate stats for the submission history page

    try:

        from datetime import datetime, timezone

        from models.balance_sheet_models import balance_sheet_model

        from models.income_statement_models import income_statement_model

        from models.budget_report_models import budget_report_model

        

        # Get user sessions from all document type models

        balance_sheet_sessions = balance_sheet_model.get_user_sessions(user.id, limit=100)

        income_statement_sessions = income_statement_model.get_user_sessions(user.id, limit=100)

        budget_report_sessions = budget_report_model.get_user_sessions(user.id, limit=100)

        

        # Combine all sessions

        all_sessions = balance_sheet_sessions + income_statement_sessions + budget_report_sessions

        

        from utils.session_workflow import clerk_submission_stats

        submission_counts = clerk_submission_stats(all_sessions)
        stats = {
            'submitted_today': submission_counts['submitted_today'],
            'total_submissions': submission_counts['total_submissions'],
            'pending': submission_counts['pending'],
            'approved': submission_counts['approved'],
            'rejected': submission_counts['rejected'],
        }

        

    except Exception as e:

        print(f"Error calculating submission history stats: {e}")

        stats = {

            'submitted_today': 0,

            'total_submissions': 0,

            'pending': 0,

            'approved': 0,

            'rejected': 0,

        }

    

    return render_template('submission-history.html', user=user, stats=stats)





@app.route('/export')

@login_required

def export_page():

    """

    Export Center — CFO full export; Finance Manager read-only finalized PDF download.

    """

    user = get_current_user()

    if not user or not user.can_access_export_center():

        flash('Access denied. Export privileges required.', 'error')

        return redirect(url_for('index'))

    return render_template('export.html', user=user, read_only_export=user.can_download_pdf() and not user.can_export())





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

        

        # If not found in database, try treating as session_id (universal workflow)

        if not submission_data:

            try:

                # Try to find session by ID across all document types

                from models.balance_sheet_models import BalanceSheetModel

                from models.income_statement_models import IncomeStatementModel

                from models.budget_report_models import BudgetReportModel

                

                # Try each document type

                for model_class, doc_type in [(BalanceSheetModel, 'balance_sheet'), 

                                               (IncomeStatementModel, 'income_statement'),

                                               (BudgetReportModel, 'budget_report')]:

                    try:

                        session = model_class().get_session(submission_id)

                        from utils.session_workflow import effective_workflow_status

                        eff_status = effective_workflow_status(session)
                        visible_statuses = {
                            'pending_review', 'pending_cfo', 'pending',
                            'rejected', 'rejected_by_manager', 'rejected_by_cfo',
                            'mapped', 'uploaded', 'draft', 'validated', 'processing',
                            'approved_by_manager', 'resubmitted', 'submitted',
                        }
                        if session and session.user_id == user.id and (
                            session.status in visible_statuses or eff_status in visible_statuses
                        ):
                            meta = getattr(session, 'metadata', None) or {}

                            # Create submission-like data from session

                            submission_data = {

                                'id': session.id,

                                'submission_name': f'{doc_type.replace("_", " ").title()} Submission',

                                'original_filename': getattr(session, 'original_filename', 'Unknown'),

                                'status': eff_status,

                                'user_id': session.user_id,

                                'document_type': doc_type,

                                'created_at': session.created_at.isoformat() if session.created_at else None,

                                'submitted_at': meta.get('submitted_at'),

                                'total_accounts': meta.get('total_accounts', 0),

                                'mapped_accounts': meta.get('total_mapped_accounts', 0),

                                'mapping_completion_percentage': 100.0 if meta.get('total_mapped_accounts', 0) > 0 else 0.0,

                                'review_notes': meta.get('review_notes', ''),

                                'rejection_reason': meta.get('rejection_reason', ''),

                                'is_locked': False,

                                'session_metadata': meta,

                            }

                            print(f"✅ Found session as submission: {submission_id} ({doc_type})")

                            try:
                                from controllers.routes_universal import compute_submission_balance_totals
                                balance = compute_submission_balance_totals(session.id, doc_type)
                                if balance:
                                    submission_data.update({
                                        k: balance[k]
                                        for k in (
                                            'total_revenue', 'total_expenses', 'net_income',
                                            'total_debits', 'total_credits', 'total_budget', 'total_actual',
                                        )
                                        if k in balance
                                    })
                            except Exception as balance_err:
                                print(f"Balance totals for submission status: {balance_err}")

                            break

                    except Exception as e:

                        continue

                        

            except Exception as e:

                print(f"Session lookup failed: {str(e)}")

        

        # If not found in database or session, try file-based storage

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

            'document_type': submission_data.get('document_type', 'balance_sheet'),

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

            'total_debits': submission_data.get('total_debits', 0),

            'total_credits': submission_data.get('total_credits', 0),

            'total_budget': submission_data.get('total_budget', 0),

            'total_actual': submission_data.get('total_actual', 0),

            'net_income': submission_data.get('net_income', 0),

            'data_quality_score': submission_data.get('data_quality_score', 0),

            'grap_categories_used': submission_data.get('grap_categories_used', 0),

            'submitted_at': submission_data.get('submitted_at'),

            'submission_timestamp': submission_data.get('submitted_at'),  # Use submitted_at as submission_timestamp for template

            'reviewed_by': submission_data.get('reviewed_by'),

            'reviewed_at': submission_data.get('reviewed_at'),

            'review_notes': submission_data.get('review_notes'),

            'approval_comments': submission_data.get('approval_comments'),

            'rejection_reason': submission_data.get('rejection_reason')
            or (submission_data.get('session_metadata') or {}).get('rejection_reason', ''),

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

        doc_type = formatted_submission.get('document_type') or 'balance_sheet'
        sid = submission_id or formatted_submission.get('id')
        needs_balance = (
            (doc_type == 'balance_sheet' and not (formatted_submission.get('total_debits') or formatted_submission.get('total_credits')))
            or (doc_type == 'income_statement' and not (formatted_submission.get('total_revenue') or formatted_submission.get('total_expenses')))
            or (doc_type == 'budget_report' and not (formatted_submission.get('total_budget') or formatted_submission.get('total_actual')))
        )
        if sid and needs_balance:
            try:
                from controllers.routes_universal import compute_submission_balance_totals
                balance = compute_submission_balance_totals(sid, doc_type)
                for key in (
                    'total_revenue', 'total_expenses', 'net_income',
                    'total_debits', 'total_credits', 'total_budget', 'total_actual',
                ):
                    if key in balance:
                        formatted_submission[key] = balance[key]
            except Exception as balance_err:
                print(f"Balance totals enrichment for submission status: {balance_err}")

        

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

                submission_data = None

                for doc_type, model in (
                    ('balance_sheet', None),
                    ('income_statement', None),
                    ('budget_report', None),
                ):
                    try:
                        if doc_type == 'balance_sheet':
                            from models.balance_sheet_models import balance_sheet_model as doc_model
                        elif doc_type == 'income_statement':
                            from models.income_statement_models import income_statement_model as doc_model
                        else:
                            from models.budget_report_models import budget_report_model as doc_model
                        db_session = doc_model.get_session(submission_id)
                        if db_session:
                            from utils.session_workflow import (
                                CLERK_ACTIONABLE_REJECTION_STATUSES,
                                effective_workflow_status,
                            )

                            meta = getattr(db_session, 'metadata', None) or {}
                            eff = effective_workflow_status(db_session)
                            submission_data = {
                                'user_id': db_session.user_id,
                                'status': eff,
                                'submission_timestamp': meta.get('submitted_at'),
                                'review_notes': meta.get('review_notes', ''),
                                'rejection_reason': meta.get('rejection_reason', '')
                                if eff in CLERK_ACTIONABLE_REJECTION_STATUSES
                                else '',
                                'document_type': doc_type,
                            }
                            break
                    except Exception:
                        continue

                if not submission_data:
                    return jsonify({'success': False, 'error': 'Submission not found'}), 404

        

        # Check if user owns this submission or has review permissions

        if submission_data['user_id'] != user.id and not user.can_review():

            return jsonify({'success': False, 'error': 'Access denied'}), 403

        

        locked_statuses = {
            'pending', 'submitted', 'approved',
            'pending_review', 'pending_cfo', 'approved_by_manager',
        }
        status = submission_data['status']
        is_locked = status in locked_statuses

        from utils.session_workflow import CLERK_ACTIONABLE_REJECTION_STATUSES

        can_edit = (
            status in ('draft', 'uploaded', 'processing', 'mapped', 'validated', 'resubmitted')
            or (
                status in CLERK_ACTIONABLE_REJECTION_STATUSES
                and submission_data['user_id'] == user.id
            )
        ) and not is_locked

        rejection_reason = ''
        if status in CLERK_ACTIONABLE_REJECTION_STATUSES:
            rejection_reason = submission_data.get('rejection_reason', '')
        is_correction_mode = status in CLERK_ACTIONABLE_REJECTION_STATUSES

        

        return jsonify({

            'success': True,

            'status': status,

            'locked': submission_data.get('locked', is_locked),

            'can_edit': can_edit,

            'is_correction_mode': is_correction_mode,

            'rejection_reason': rejection_reason,

            'submission_timestamp': submission_data.get('submission_timestamp'),

            'review_notes': submission_data.get('review_notes', ''),

            'message': f"File is {status}"

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

    """Get all submissions for the current user across all document types"""

    print("🔥 API ENDPOINT CALLED: /api/submissions/user")

    try:

        user = get_current_user()
        denied = _finance_clerk_api_guard(user)
        if denied:
            return denied

        user_id = user.id

        

        print(f"🚀 Loading submissions for user: {user_id}")

        

        # Get user sessions from all document type models
        submissions = []
        
        # 1. Balance Sheet Sessions
        from models.balance_sheet_models import balance_sheet_model
        balance_sheet_sessions = balance_sheet_model.get_user_sessions(user_id, limit=25)
        print(f"📊 Found {len(balance_sheet_sessions)} balance sheet sessions")
        
        # 2. Income Statement Sessions  
        from models.income_statement_models import income_statement_model
        income_statement_sessions = income_statement_model.get_user_sessions(user_id, limit=25)
        print(f"📊 Found {len(income_statement_sessions)} income statement sessions")
        
        # 3. Budget Report Sessions
        from models.budget_report_models import budget_report_model
        budget_report_sessions = budget_report_model.get_user_sessions(user_id, limit=25)
        print(f"📊 Found {len(budget_report_sessions)} budget report sessions")
        
        # Combine all sessions
        all_sessions = balance_sheet_sessions + income_statement_sessions + budget_report_sessions
        
        # Sort by created_at in descending order (newest first)
        all_sessions.sort(key=lambda x: x.created_at if x.created_at else datetime.min, reverse=True)
        
        print(f"📊 Total sessions across all document types: {len(all_sessions)}")

        from utils.session_metadata_helpers import (
            clerk_submission_account_counts,
            maybe_persist_legacy_rejection_repair,
            resolve_line_item_comments,
            resolve_rejection_reason,
        )
        from utils.session_workflow import (
            session_hidden_from_clerk_history,
            session_pending_approval,
            session_submitted_at,
            session_submitted_for_review,
        )

        for session in all_sessions:
            if session_hidden_from_clerk_history(session):
                continue
            if not session_submitted_for_review(session):
                continue

            md = session.metadata or {}
            model = None
            if getattr(session, 'document_type', None) == 'income_statement':
                model = income_statement_model
            elif getattr(session, 'document_type', None) == 'budget_report':
                model = budget_report_model
            else:
                model = balance_sheet_model
            maybe_persist_legacy_rejection_repair(session, model)
            md = session.metadata or {}
            mapped_accounts_count, total_accounts_count = clerk_submission_account_counts(md)

            validation_status = session.status

            locked_statuses = [
                'pending', 'submitted', 'approved',
                'pending_review', 'pending_cfo', 'approved_by_manager',
            ]
            correction_statuses = frozenset({'rejected', 'rejected_by_manager', 'rejected_by_cfo'})
            locked_status = validation_status in locked_statuses and validation_status not in correction_statuses

            document_type = getattr(session, 'document_type', 'balance_sheet')
            submitted_ts = session_submitted_at(session)
            submission_data = {
                'session_id': session.id,
                'user_id': session.user_id,
                'filename': session.original_filename or session.filename,
                'filepath': session.filename,
                'submission_timestamp': submitted_ts.isoformat() if submitted_ts else None,
                'submitted_at': submitted_ts.isoformat() if submitted_ts else None,
                'status': validation_status,
                'pending_approval': session_pending_approval(session),
                'mapped_accounts_count': mapped_accounts_count,
                'total_accounts_count': total_accounts_count,
                'file_type': session.file_type,
                'document_type': document_type,
                'review_notes': md.get('review_notes', ''),
                'rejection_reason': resolve_rejection_reason(md),
                'line_item_comments': resolve_line_item_comments(md),
                'locked': locked_status,
            }

            submissions.append(submission_data)

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



@app.route('/api/submission/<submission_id>/close', methods=['POST'])

@login_required

def close_submission(submission_id):

    """Close a submission"""

    try:
        user = get_current_user()

        # Use universal lookup approach to find submission across all document types
        submission_data = None
        document_type = None

        # First try to get from database
        try:
            from models.balance_sheet_models import BalanceSheetSession
            tb_session = BalanceSheetSession()

            # Get submission from database
            result = tb_session.client.table('submissions').select('*').eq('id', submission_id).execute()

            if result.data:
                submission_data = result.data[0]
                document_type = submission_data.get('document_type', 'balance_sheet')
                print(f"✅ Found submission in database: {submission_id}")

        except Exception as db_error:
            print(f"Database lookup failed: {str(db_error)}")

        # If not found in database, try treating as session_id (universal workflow)
        if not submission_data:
            try:
                # Try to find session by ID across all document types
                from models.balance_sheet_models import BalanceSheetModel
                from models.income_statement_models import IncomeStatementModel
                from models.budget_report_models import BudgetReportModel

                # Try each document type
                for model_class, doc_type in [(BalanceSheetModel, 'balance_sheet'), 
                                               (IncomeStatementModel, 'income_statement'),
                                               (BudgetReportModel, 'budget_report')]:
                    try:
                        session = model_class().get_session(submission_id)
                        if session:
                            # Create submission-like data from session
                            submission_data = {
                                'id': session.id,
                                'submission_name': f'{doc_type.replace("_", " ").title()} Submission',
                                'original_filename': getattr(session, 'original_filename', 'Unknown'),
                                'status': session.status,
                                'user_id': session.user_id,
                                'document_type': doc_type,
                                'created_at': session.created_at.isoformat() if session.created_at else None,
                            }
                            document_type = doc_type
                            print(f"✅ Found session as submission: {submission_id} ({doc_type})")
                            break

                    except Exception as model_error:
                        continue

            except Exception as session_error:
                print(f"Session lookup failed: {str(session_error)}")

        if not submission_data:
            return jsonify({'success': False, 'error': 'Submission not found'}), 404

        # Check if user owns this submission
        if submission_data['user_id'] != user.id:
            return jsonify({'success': False, 'error': 'Permission denied'}), 403

        # Use appropriate service based on document type
        if document_type == 'income_statement':
            from services.income_statement_service import income_statement_service
            income_statement_service.model.update_session_status(submission_id, 'closed', {})
        elif document_type == 'budget_report':
            from services.budget_report_service import budget_report_service
            budget_report_service.model.update_session_status(submission_id, 'closed', {})
        else:
            # Default to balance sheet service
            from services.flexible_balance_sheet_service import flexible_balance_sheet_service
            flexible_balance_sheet_service.model.update_session_status(submission_id, 'closed', {})

        return jsonify({

            'success': True,

            'message': 'Submission closed successfully'

        })

        

    except Exception as e:

        app.logger.error(f"Error closing submission: {str(e)}")

        return jsonify({

            'success': False,

            'error': f'Error closing submission: {str(e)}'

        }), 500





@app.route('/api/submission/<submission_id>/approve', methods=['POST'])
@login_required
@permission_required('process')
def submit_for_approval(submission_id):
    """Submit a document for approval workflow"""
    try:
        user = get_current_user()
        data = request.get_json()
        action = data.get('action')
        
        if action != 'submit_for_approval':
            return jsonify({'success': False, 'error': 'Invalid action'}), 400
        
        # Use universal lookup approach to find submission across all document types
        submission_data = None
        document_type = None
        session = None
        
        # Try each document type model
        for doc_type in ['balance_sheet', 'income_statement', 'budget_report']:
            try:
                if doc_type == 'balance_sheet':
                    from models.balance_sheet_models import balance_sheet_model
                    session = balance_sheet_model.get_session(submission_id)
                elif doc_type == 'income_statement':
                    from models.income_statement_models import income_statement_model
                    session = income_statement_model.get_session(submission_id)
                elif doc_type == 'budget_report':
                    from models.budget_report_models import budget_report_model
                    session = budget_report_model.get_session(submission_id)
                
                if session:
                    # Create submission-like data from session
                    submission_data = {
                        'id': session.id,
                        'submission_name': f'{doc_type.replace("_", " ").title()} Submission',
                        'original_filename': getattr(session, 'original_filename', 'Unknown'),
                        'status': session.status,
                        'user_id': session.user_id,
                        'document_type': doc_type,
                        'created_at': session.created_at.isoformat() if session.created_at else None,
                    }
                    document_type = doc_type
                    print(f"✅ Found session for approval: {submission_id} ({doc_type})")
                    break
                    
            except Exception as model_error:
                continue
        
        if not submission_data:
            return jsonify({'success': False, 'error': 'Submission not found'}), 404
        
        # Check if user owns this submission
        if submission_data['user_id'] != user.id:
            return jsonify({'success': False, 'error': 'Permission denied'}), 403

        from controllers.routes_universal import (
            _clerk_mapping_locked_json_error,
            _period_lock_json_error,
            require_balanced_session,
        )

        lock_resp = _period_lock_json_error(submission_id, document_type)
        if lock_resp:
            return lock_resp

        locked_resp = _clerk_mapping_locked_json_error(submission_id, document_type)
        if locked_resp:
            return locked_resp

        balanced, balance_error = require_balanced_session(submission_id, document_type)
        if not balanced:
            return jsonify({'success': False, 'error': balance_error}), 400
        
        from services.universal_workflow_service import UniversalWorkflowService

        wf = UniversalWorkflowService()
        result = wf.submit_for_review(
            document_type=document_type,
            session_id=submission_id,
            user_id=user.id,
            notes='Submitted from submission status page',
        )
        if result.get('success'):
            return jsonify({
                'success': True,
                'message': result.get('message') or f'{submission_data["submission_name"]} submitted for review',
                'new_status': result.get('new_status'),
            })
        return jsonify({
            'success': False,
            'error': result.get('error', 'Failed to submit for review'),
        }), 400
            
    except Exception as e:
        app.logger.error(f"Error submitting for approval: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Error submitting for approval: {str(e)}'
        }), 500


@app.route('/api/submissions/pending')
@login_required
@permission_required('approve', 'final_approve')

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

        print(f" Found {len(grap_categories)} GRAP categories")

        

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

        from services.universal_grap_service import universal_grap_service

        

        # Get session data from database using universal service

        session_data = universal_grap_service.get_session_data(session_id)

        if not session_data or not session_data.get('success'):

            return jsonify({

                'success': False,

                'error': f'Session {session_id} not found'
            }), 404

        # Get data rows and mapping results from session metadata
        data_rows = session_data.get('balance_sheet_data', [])
        session_metadata = session_data.get('metadata', {})
        
        print(f" Found {len(data_rows)} data rows for session {session_id}")
        print(f" Session metadata keys: {list(session_metadata.keys()) if session_metadata else 'None'}")

        # Get mapping results from session metadata (mapped_data, grap_mapping, etc.)
        from services.statement_validation_service import mapped_lines_from_metadata

        mapped_lines = mapped_lines_from_metadata(session_metadata)
        mapping_confidence = session_metadata.get('mapping_confidence', 0)

        print(f" Found {len(mapped_lines)} mapped account rows from metadata")
        print(f" Mapping confidence: {mapping_confidence}")

        # Process accounts for mapping interface
        unmapped_accounts = []
        mapped_accounts = {}

        def _account_code_from_row(row: dict) -> str:
            return str(
                row.get('account_code')
                or row.get('code')
                or row.get('Account Code')
                or ''
            )

        mapped_by_code = {}
        for mapped_acc in mapped_lines:
            code = _account_code_from_row(mapped_acc)
            if code:
                mapped_by_code[code] = mapped_acc
        
        for i, row in enumerate(data_rows):
            account_code = str(row.get('Account Code', ''))
            account_desc = row.get('Account Description', '')
            
            # Create account object for frontend
            account = {
                'id': f"account_{i}",
                'account_code': account_code,
                'account_desc': account_desc,
                'name': account_desc,
                'description': account_desc,
                'amount': float(row.get('Net Balance', 0)),
                'debit_balance': float(row.get('Debit Balance', 0)),
                'credit_balance': float(row.get('Credit Balance', 0)),
                'net_balance': float(row.get('Net Balance', 0)),
                'row_index': i
            }
            
            mapped_account = mapped_by_code.get(account_code)
            
            if mapped_account:
                grap_code = (
                    mapped_account.get('grap_code')
                    or mapped_account.get('grap_category')
                    or mapped_account.get('mapped_to_grap')
                    or ''
                )
                if grap_code not in mapped_accounts:
                    mapped_accounts[grap_code] = []
                
                account_with_mapping = account.copy()
                account_with_mapping.update({
                    'grap_code': grap_code,
                    'grap_name': mapped_account.get('grap_name') or mapped_account.get('grap_category') or '',
                    'confidence': mapped_account.get('confidence', 1.0)
                })
                mapped_accounts[grap_code].append(account_with_mapping)
            else:
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

    Draft mapping save is disabled — data is kept in staging until Submit for Review.

    """

    return jsonify({
        'success': False,
        'error': 'Saving mapping drafts is not supported. Complete mapping and use Submit for Review.',
    }), 410


@app.route('/api/processing', methods=['POST'])
@login_required
def process_grap_mapping():
    """Deprecated alias — use POST /api/universal/process-grap-mapping."""
    try:
        data = request.get_json() or {}
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        current_user = get_current_user()
        if not current_user:
            return jsonify({'success': False, 'error': 'User not authenticated'}), 401
        from controllers.handlers.grap_processing import process_grap_mapping_request
        return process_grap_mapping_request(
            data.get('session_id'),
            current_user.id,
            data.get('document_type'),
        )
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
