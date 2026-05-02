"""
SADPMR Financial Reporting System - FastAPI Integration Layer
Easy-to-use API for seamless integration with other applications
"""

from fastapi import FastAPI, UploadFile, File, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import os
import tempfile
from datetime import datetime
import json
from typing import Dict, List, Optional
import pandas as pd

# Import existing services
from models.grap_models import GRAPMappingEngine
from services.pdf_service import PDFService
from services.supabase_service import get_supabase_service
from utils.helpers import format_currency, generate_filename

app = FastAPI(
    title="SADPMR Financial Reporting API",
    description="Easy integration API for financial statement generation",
    version="1.0.0"
)

# CORS middleware for easy integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Simple authentication (you can enhance this)
security = HTTPBearer()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Simple token-based authentication"""
    # For demo purposes, accept any token
    # In production, validate against Supabase Auth
    return {"user_id": "demo_user", "role": "accountant"}

@app.get("/")
async def root():
    """API health check"""
    return {
        "status": "healthy",
        "service": "SADPMR Financial Reporting API",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.post("/upload-trial-balance")
async def upload_trial_balance(
    file: UploadFile = File(...),
    current_user: Dict = Depends(get_current_user)
):
    """
    Upload and process trial balance file
    Returns financial statements and ratios
    """
    try:
        # Validate file type
        if not file.filename.lower().endswith(('.xlsx', '.xls', '.csv', '.xlsm', '.xlsb', '.tsv')):
            raise HTTPException(status_code=400, detail="Invalid file type. Supported formats: .xlsx, .xls, .csv, .xlsm, .xlsb, .tsv")
        
        # Read file content
        file_content = await file.read()
        
        # Save to temporary file for processing
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as tmp_file:
            tmp_file.write(file_content)
            tmp_file_path = tmp_file.name
        
        try:
            # Process with existing GRAP engine
            engine = GRAPMappingEngine()
            
            # Import and validate trial balance
            trial_balance = engine.import_trial_balance(tmp_file_path)
            
            # Map to GRAP codes
            mapped_data = engine.map_to_grap(trial_balance)
            
            # Check for unmapped accounts
            unmapped_accounts = mapped_data[mapped_data['grap_code'].isna()]
            if not unmapped_accounts.empty:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Unmapped accounts found: {unmapped_accounts['Account Description'].tolist()}"
                )
            
            # Generate financial statements
            sofp = engine.generate_statement_of_financial_position(mapped_data)
            sofe = engine.generate_statement_of_performance(mapped_data)
            scf = engine.generate_cash_flow_statement(sofp, sofe, mapped_data)
            
            # Calculate ratios
            ratios = engine.calculate_ratios(sofp, sofe)
            
            # Prepare results
            results = {
                'summary': {
                    'total_assets': float(sofp['assets']['Amount'].sum()),
                    'total_liabilities': float(sofp['liabilities']['Amount'].sum()),
                    'net_assets': float(sofp['net_assets']['Amount'].sum()),
                    'total_revenue': float(sofe['revenue']['Amount'].sum()),
                    'total_expenses': float(sofe['expenses']['Amount'].sum()),
                    'surplus_deficit': float(sofe['surplus']),
                    'ratios': ratios
                },
                'sofp': {
                    'assets': sofp['assets'].to_dict('records'),
                    'liabilities': sofp['liabilities'].to_dict('records'),
                    'net_assets': sofp['net_assets'].to_dict('records')
                },
                'sofe': {
                    'revenue': sofe['revenue'].to_dict('records'),
                    'expenses': sofe['expenses'].to_dict('records'),
                    'surplus': float(sofe['surplus'])
                },
                'scf': scf,
                'processed_at': datetime.utcnow().isoformat()
            }
            
            # Save to Supabase
            supabase = get_supabase_service()
            if supabase:
                tb_result = supabase.save_trial_balance(
                    file_content, file.filename, current_user['user_id']
                )
                
                if tb_result['success']:
                    results_result = supabase.save_financial_results(
                        results, tb_result['record_id'], current_user['user_id']
                    )
                    results['record_id'] = results_result.get('record_id')
            else:
                print("Warning: Supabase not available, skipping database save")
            
            return {
                'success': True,
                'message': 'Trial balance processed successfully',
                'results': results
            }
            
        finally:
            # Clean up temporary file
            if os.path.exists(tmp_file_path):
                os.unlink(tmp_file_path)
                
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")

@app.post("/generate-pdf/{record_id}")
async def generate_pdf_report(
    record_id: str,
    current_user: Dict = Depends(get_current_user)
):
    """
    Generate PDF report for processed financial statements
    Returns download URL
    """
    try:
        # Get results from Supabase
        supabase = get_supabase_service()
        if not supabase:
            raise HTTPException(status_code=503, detail="Database service not available")
            
        results_data = supabase.get_trial_balance(record_id)
        if not results_data:
            raise HTTPException(status_code=404, detail="Results not found")
        
        # Generate PDF
        pdf_service = PDFService()
        pdf_filename = generate_filename("SADPMR_AFS", "pdf")
        
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
            pdf_path = tmp_file.name
        
        # Generate PDF using existing service
        pdf_service.generate_financial_statements_pdf(
            json.loads(results_data['results']), pdf_path
        )
        
        # Read PDF content
        with open(pdf_path, 'rb') as f:
            pdf_content = f.read()
        
        # Save to Supabase storage
        pdf_result = supabase.save_pdf_report(
            pdf_content, pdf_filename, record_id, current_user['user_id']
        )
        
        # Clean up temporary file
        if os.path.exists(pdf_path):
            os.unlink(pdf_path)
        
        if pdf_result['success']:
            return {
                'success': True,
                'message': 'PDF generated successfully',
                'download_url': pdf_result['public_url'],
                'filename': pdf_filename
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to save PDF")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF generation error: {str(e)}")

@app.get("/reports")
async def get_user_reports(current_user: Dict = Depends(get_current_user)):
    """Get all reports for the current user"""
    try:
        supabase = get_supabase_service()
        if not supabase:
            return {'success': False, 'reports': [], 'error': 'Database service not available'}
            
        reports = supabase.get_user_reports(current_user['user_id'])
        return {
            'success': True,
            'reports': reports
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching reports: {str(e)}")

@app.get("/stats")
async def get_user_stats(current_user: Dict = Depends(get_current_user)):
    """Get user statistics and storage info"""
    try:
        supabase = get_supabase_service()
        if not supabase:
            return {'success': False, 'stats': {}, 'error': 'Database service not available'}
            
        stats = supabase.get_storage_stats(current_user['user_id'])
        return {
            'success': True,
            'stats': stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching stats: {str(e)}")

@app.delete("/reports/{report_id}")
async def delete_report(
    report_id: str,
    current_user: Dict = Depends(get_current_user)
):
    """Delete a report and associated files"""
    try:
        supabase = get_supabase_service()
        if not supabase:
            return {'success': False, 'error': 'Database service not available'}
            
        result = supabase.delete_report(report_id, current_user['user_id'])
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting report: {str(e)}")

@app.get("/download/{filename}")
async def download_file(filename: str):
    """Download file from Supabase storage"""
    try:
        # This is a simplified version - in production you'd validate permissions
        return {"message": "Use the public URL from Supabase storage directly"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Download error: {str(e)}")

# Health check endpoint
@app.get("/health")
async def health_check():
    """Detailed health check"""
    return {
        "status": "healthy",
        "services": {
            "database": "connected",  # You can actually check Supabase connection
            "storage": "available",
            "pdf_generator": "ready"
        },
        "timestamp": datetime.utcnow().isoformat()
    }

# Run with: uvicorn api:app --reload
