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
from datetime import datetime, timedelta
import sys

# Import our Phase 1 mapping engine and auth models
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from models.grap_models import GRAPMappingEngine
from models.auth_models import db, User, get_role_description, get_role_color

# Configuration
app = Flask(__name__, 
           template_folder='../templates', 
           static_folder='../static',
           static_url_path='/static')

# Get the project root directory (parent of controllers)
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

app.config['SECRET_KEY'] = 'sadpmr-demo-2025-secure-key-auth-enabled'
app.config['UPLOAD_FOLDER'] = os.path.join(project_root, 'uploads')
app.config['OUTPUT_FOLDER'] = os.path.join(project_root, 'outputs')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=1)  # 1 hour session
app.config['SESSION_COOKIE_SECURE'] = False  # Set to True in production with HTTPS
app.config['SESSION_COOKIE_HTTPONLY'] = True  # Prevent JavaScript access
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # CSRF protection
app.config['SESSION_REFRESH_EACH_REQUEST'] = True  # Refresh session on each request

ALLOWED_EXTENSIONS = {'xlsx', 'xls', 'csv'}

# Before request handler to ensure persistent sessions
@app.before_request
def make_session_permanent():
    """Make sessions permanent on each request if user is logged in"""
    if 'user_id' in session:
        session.permanent = True
        app.permanent_session_lifetime = timedelta(hours=1)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# Authentication decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


def permission_required(permission):
    """Decorator to check specific permissions"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                return jsonify({'success': False, 'error': 'Authentication required'}), 401
            
            user_data = db.get_user_by_id(session['user_id'])
            if not user_data:
                return jsonify({'success': False, 'error': 'User not found'}), 401
            
            user = User(user_data)
            if not user.has_permission(permission):
                return jsonify({'success': False, 'error': f'Permission denied. {permission.upper()} access required.'}), 403
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def get_current_user():
    """Get current logged-in user"""
    if 'user_id' in session:
        user_data = db.get_user_by_id(session['user_id'])
        if user_data:
            return User(user_data)
    return None


# Debug route to check session
@app.route('/debug-session')
def debug_session():
    """Debug session contents"""
    return {
        'session_keys': list(session.keys()),
        'user_id': session.get('user_id'),
        'username': session.get('username'),
        'current_user': get_current_user().__dict__ if get_current_user() else None
    }


# Authentication Routes
@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user_data = db.verify_password(username, password)
        
        if user_data and user_data['is_active']:
            session['user_id'] = user_data['id']
            session['username'] = user_data['username']
            session['role'] = user_data['role']
            session['full_name'] = user_data['full_name']
            session.permanent = True
            
            # DON'T flash message - just redirect
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password.', 'error')
    
    return render_template('login.html')


@app.route('/logout')
def logout():
    """Logout user"""
    username = session.get('full_name', 'User')
    session.clear()
    # Don't show flash message on logout to avoid "welcome back" on login page
    return redirect(url_for('login'))


@app.route('/')
@login_required
def index():
    """Home page - Dashboard"""
    user = get_current_user()
    return render_template('index.html', user=user)


@app.route('/upload')
@login_required
def upload_page():
    """Trial Balance Upload Page"""
    user = get_current_user()
    if not user.can_upload():
        flash('You do not have permission to upload files.', 'error')
        return redirect(url_for('index'))
    return render_template('upload.html', user=user)


@app.route('/api/upload', methods=['POST'])
@login_required
@permission_required('upload')
def upload_trial_balance():
    """
    API endpoint to handle Trial Balance file upload
    Returns: JSON with upload status and file details
    """
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'No file uploaded'}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'success': False, 'error': 'No file selected'}), 400
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{timestamp}_{filename}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        file.save(filepath)
        
        # Quick validation
        try:
            df = pd.read_excel(filepath) if filepath.endswith('.xlsx') else pd.read_csv(filepath)
            
            # Validate that this looks like a trial balance file
            required_keywords = ['account', 'debit', 'credit', 'balance']
            column_str = ' '.join(df.columns).lower()
            
            if not any(keyword in column_str for keyword in required_keywords):
                return jsonify({
                    'success': False,
                    'error': f"This doesn't appear to be a trial balance file. Expected columns like 'Account Code', 'Account Description', 'Debit Balance', 'Credit Balance'. Found columns: {list(df.columns)}. Please upload a proper trial balance file."
                }), 400
            
            row_count = len(df)
            
            return jsonify({
                'success': True,
                'filename': filename,
                'filepath': filepath,
                'row_count': row_count,
                'message': f'Successfully uploaded {row_count} accounts'
            })
        
        except Exception as e:
            return jsonify({
                'success': False,
                'error': f'Invalid file format: {str(e)}'
            }), 400
    
    return jsonify({'success': False, 'error': 'Invalid file type'}), 400


@app.route('/api/process', methods=['POST'])
@login_required
@permission_required('process')
def process_trial_balance():
    """
    API endpoint to process Trial Balance and generate financial statements
    """
    try:
        data = request.get_json()
        filepath = data.get('filepath')
        
        if not filepath or not os.path.exists(filepath):
            return jsonify({'success': False, 'error': 'File not found'}), 404
        
        # Initialize mapping engine
        engine = GRAPMappingEngine()
        
        # Step 1: Import TB
        trial_balance = engine.import_trial_balance(filepath)
        
        # Step 2: Map to GRAP
        mapped_data = engine.map_to_grap(trial_balance)
        
        # Step 3: Check for unmapped accounts
        unmapped = mapped_data[mapped_data['grap_code'].isna()]
        if len(unmapped) > 0:
            return jsonify({
                'success': False,
                'error': 'Unmapped accounts detected',
                'unmapped_accounts': unmapped[['Account Code', 'Account Description', 'Net Balance']].to_dict('records')
            }), 400
        
        # Step 4: Generate statements
        sofp = engine.generate_statement_of_financial_position(mapped_data)
        sofe = engine.generate_statement_of_performance(mapped_data)
        scf = engine.generate_cash_flow_statement(sofp, sofe, mapped_data)
        
        # Step 5: Calculate key ratios
        ratios = engine.calculate_ratios(sofp, sofe)
        
        # Step 6: Prepare summary for frontend
        summary = {
            'total_assets': float(sofp['assets']['Amount'].sum()),
            'total_liabilities': float(sofp['liabilities']['Amount'].sum()),
            'net_assets': float(sofp['net_assets']['Amount'].sum()),
            'total_revenue': float(sofe['revenue']['Amount'].sum()),
            'total_expenses': float(sofe['expenses']['Amount'].sum()),
            'surplus_deficit': float(sofe['surplus']),
            'ratios': ratios,
            'timestamp': datetime.now().isoformat()
        }
        
        # Store results in session (in production, use database)
        results_filename = f"results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        results_path = os.path.join(project_root, 'data', results_filename)
        
        # Convert DataFrames to JSON-serializable format
        def convert_df_to_serializable(df):
            """Convert DataFrame to JSON-serializable format, handling int64 and other numpy types"""
            records = []
            for _, row in df.iterrows():
                record = {}
                for col in df.columns:
                    value = row[col]
                    # Convert numpy types to native Python types
                    if hasattr(value, 'item'):
                        value = value.item()
                    elif pd.isna(value):
                        value = None
                    record[col] = value
                records.append(record)
            return records
        
        # Prepare JSON-serializable data
        json_data = {
            'summary': summary,
            'sofp': {
                'assets': convert_df_to_serializable(sofp['assets']),
                'liabilities': convert_df_to_serializable(sofp['liabilities']),
                'net_assets': convert_df_to_serializable(sofp['net_assets'])
            },
            'sofe': {
                'revenue': convert_df_to_serializable(sofe['revenue']),
                'expenses': convert_df_to_serializable(sofe['expenses'])
            },
            'scf': scf
        }
        
        with open(results_path, 'w') as f:
            json.dump(json_data, f, indent=2)
        
        return jsonify({
            'success': True,
            'summary': summary,
            'results_file': results_filename
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
        
        results_path = os.path.join(project_root, 'data', results_file)
        
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


@app.route('/results')
@login_required
def results_page():
    """
    Financial Statements Results Page
    """
    user = get_current_user()
    return render_template('results.html', user=user)


@app.route('/reports')
@login_required
def reports_page():
    """Reports page - displays generated reports"""
    user = get_current_user()
    return render_template('reports.html', user=user)


@app.route('/export')
@login_required
def export_page():
    """Export page - export statements in various formats"""
    user = get_current_user()
    return render_template('export.html', user=user)


@app.route('/admin')
@login_required
def admin_page():
    """Administration page - CFO only"""
    user = get_current_user()
    if user.role != 'CFO':
        flash('You do not have permission to access the administration panel.', 'error')
        return redirect(url_for('index'))
    return render_template('admin.html', user=user)


@app.route('/about')
@login_required
def about_page():
    """
    About the System
    """
    user = get_current_user()
    return render_template('about.html', user=user)


# Make user functions available in templates - MUST be at module level!
@app.context_processor
def inject_user():
    current_user = get_current_user()
    return {
        'current_user': current_user,
        'get_role_description': get_role_description,
        'get_role_color': get_role_color
    }


if __name__ == '__main__':
    # Ensure directories exist
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)
    os.makedirs(os.path.join(project_root, 'data'), exist_ok=True)
    
    print("\n" + "="*70)
    print("SADPMR FINANCIAL REPORTING SYSTEM - AUTHENTICATED DEMO SERVER")
    print("="*70)
    print("\n🔐 Authentication Enabled - Role-Based Access Control")
    print("\n📋 Demo Accounts:")
    print("   CFO:        cfo@sadpmr.gov.za / demo123")
    print("   Accountant: accountant@sadpmr.gov.za / demo123")
    print("   Clerk:      clerk@sadpmr.gov.za / demo123")
    print("   Auditor:    auditor@agsa.gov.za / demo123")
    print("\n🚀 Starting server...")
    print("📍 Open your browser and navigate to: http://localhost:5000")
    print("🎯 Demo ready for February 3, 2026")
    print("\n⚠️  Press CTRL+C to stop the server\n")
    
    app.run(debug=True, host='0.0.0.0', port=5000)
