"""
SADPMR Financial Reporting System - Flask Routes
Web interface and API endpoints for GRAP financial statement generation
"""

from flask import Flask, render_template, request, jsonify, send_file
from werkzeug.utils import secure_filename
import os
import pandas as pd
import json
from datetime import datetime
import sys

# Import models
from models.grap_models import GRAPMappingEngine, generate_pdf_report
from utils.validators import validate_file_format, validate_trial_balance
from utils.helpers import format_currency, generate_filename

# Configuration
app = Flask(__name__, 
           template_folder='../templates', 
           static_folder='../static',
           static_url_path='/static')
app.config['SECRET_KEY'] = 'sadpmr-demo-2025-secure-key'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['OUTPUT_FOLDER'] = 'outputs'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB

# Constants
ALLOWED_EXTENSIONS = {'xlsx', 'xls', 'csv'}


def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/')
def index():
    """Home page"""
    return render_template('index.html')


@app.route('/upload')
def upload_page():
    """Upload page"""
    return render_template('upload.html')


@app.route('/api/upload', methods=['POST'])
def upload_trial_balance():
    """Handle file upload"""
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
        
        # Validate file
        try:
            df = pd.read_excel(filepath) if filepath.endswith('.xlsx') else pd.read_csv(filepath)
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
def process_trial_balance():
    """Process trial balance and generate financial statements"""
    try:
        data = request.get_json()
        filepath = data.get('filepath')
        
        if not filepath or not os.path.exists(filepath):
            return jsonify({'success': False, 'error': 'File not found'}), 404
        
        # Initialize mapping engine
        engine = GRAPMappingEngine()
        
        # Import and map trial balance
        trial_balance = engine.import_trial_balance(filepath)
        mapped_data = engine.map_to_grap(trial_balance)
        
        # Check for unmapped accounts
        unmapped = mapped_data[mapped_data['grap_code'].isna()]
        if len(unmapped) > 0:
            return jsonify({
                'success': False,
                'error': 'Unmapped accounts detected',
                'unmapped_accounts': unmapped[['Account Code', 'Account Description', 'Net Balance']].to_dict('records')
            }), 400
        
        # Generate financial statements
        sofp = engine.generate_statement_of_financial_position(mapped_data)
        sofe = engine.generate_statement_of_performance(mapped_data)
        ratios = engine.calculate_ratios(sofp, sofe)
        
        # Prepare summary data
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
        
        return jsonify({
            'success': True,
            'summary': summary,
            'message': 'Financial statements generated successfully'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Processing error: {str(e)}'
        }), 500


@app.route('/api/download/<filename>')
def download_file(filename):
    """Download generated PDF report"""
    try:
        filepath = os.path.join(app.config['OUTPUT_FOLDER'], filename)
        if os.path.exists(filepath):
            return send_file(filepath, as_attachment=True)
        return jsonify({'error': 'File not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/about')
def about():
    """About page"""
    return render_template('about.html')


if __name__ == '__main__':
    # Create directories if they don't exist
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)
    
    app.run(debug=True, host='0.0.0.0', port=5000)
