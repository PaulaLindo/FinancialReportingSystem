"""
SADPMR Financial Reporting System - Configuration Settings
Application configuration for different environments
"""

import os
from datetime import timedelta


class Config:
    """Base configuration class"""
    
    # Flask Configuration
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'sadpmr-demo-2025-secure-key'
    
    # File Upload Configuration
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'uploads')
    OUTPUT_FOLDER = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'outputs')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    
    # Allowed file extensions
    ALLOWED_EXTENSIONS = {'xlsx', 'xls', 'csv'}
    
    # GRAP Configuration
    GRAP_MAPPING_VERSION = '2.0'
    GRAP_COMPLIANCE_YEAR = 2026
    
    # PDF Configuration
    PDF_PAGE_SIZE = 'A4'
    PDF_MARGIN_TOP = 2.0  # cm
    PDF_MARGIN_BOTTOM = 2.0  # cm
    PDF_MARGIN_LEFT = 2.5  # cm
    PDF_MARGIN_RIGHT = 2.5  # cm
    
    # Financial Ratios Benchmarks
    RATIO_BENCHMARKS = {
        'current_ratio': {'min': 1.5, 'target': 2.0},
        'debt_to_equity': {'max': 1.0, 'target': 0.5},
        'operating_margin': {'min': 10.0, 'target': 15.0},
        'return_on_assets': {'min': 5.0, 'target': 8.0}
    }
    
    # Session Configuration
    PERMANENT_SESSION_LIFETIME = timedelta(hours=1)
    
    # Security Configuration
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = None
    
    @staticmethod
    def init_app(app):
        """Initialize application with this configuration"""
        # Create upload and output directories
        os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
        os.makedirs(Config.OUTPUT_FOLDER, exist_ok=True)


class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    TESTING = False
    
    # Development-specific settings
    WTF_CSRF_ENABLED = False  # Disable CSRF for development


class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    TESTING = False
    
    # Production-specific security settings
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # Production file handling
    MAX_CONTENT_LENGTH = 32 * 1024 * 1024  # 32MB for production


class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    DEBUG = True
    
    # Testing-specific settings
    WTF_CSRF_ENABLED = False
    
    # Use temporary directories for testing
    UPLOAD_FOLDER = 'test_uploads'
    OUTPUT_FOLDER = 'test_outputs'


# Configuration mapping
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
