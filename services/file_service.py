"""
SADPMR Financial Reporting System - File Service
Handles file upload, processing, and validation operations
"""

import os
import pandas as pd
from datetime import datetime
from werkzeug.utils import secure_filename
from utils.exceptions import FileProcessingError, ValidationError
from utils.constants import ALLOWED_EXTENSIONS, COLUMN_MAPPINGS, REQUIRED_COLUMNS


class FileService:
    """Service for handling file operations"""
    
    def __init__(self, upload_folder):
        self.upload_folder = upload_folder
    
    def validate_file(self, file):
        """Validate uploaded file"""
        if not file:
            raise FileProcessingError('No file uploaded')
        
        if file.filename == '':
            raise FileProcessingError('No file selected')
        
        if not self._is_allowed_file(file.filename):
            raise FileProcessingError('Invalid file type')
    
    def save_uploaded_file(self, file):
        """Save uploaded file with timestamp"""
        self.validate_file(file)
        
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{timestamp}_{filename}"
        filepath = os.path.join(self.upload_folder, filename)
        
        try:
            file.save(filepath)
            return filepath, filename
        except Exception as e:
            raise FileProcessingError(f'Failed to save file: {str(e)}', filename)
    
    def read_trial_balance_file(self, filepath):
        """Read and parse trial balance file"""
        try:
            if filepath.endswith('.xlsx'):
                df = pd.read_excel(filepath)
            else:
                df = pd.read_csv(filepath)
            
            # Standardize column names
            df.columns = df.columns.str.strip()
            df.rename(columns=COLUMN_MAPPINGS, inplace=True)
            
            # Validate required columns
            missing_columns = [col for col in REQUIRED_COLUMNS if col not in df.columns]
            if missing_columns:
                raise ValidationError(f"Missing required columns: {', '.join(missing_columns)}")
            
            # Calculate net balance if not present
            if 'Net Balance' not in df.columns:
                if 'Debit Balance' in df.columns and 'Credit Balance' in df.columns:
                    df['Net Balance'] = df['Debit Balance'] - df['Credit Balance']
                else:
                    raise ValidationError("File must contain Debit Balance and Credit Balance columns")
            
            return df, len(df)
            
        except Exception as e:
            if isinstance(e, (ValidationError, FileProcessingError)):
                raise
            raise FileProcessingError(f'Error reading file: {str(e)}', os.path.basename(filepath))
    
    def _is_allowed_file(self, filename):
        """Check if file extension is allowed"""
        return '.' in filename and \
               filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
