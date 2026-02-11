"""
SADPMR Financial Reporting System - Configuration Settings
Application configuration for different environments
"""

import os
from datetime import timedelta
from utils.constants import (
    MAX_FILE_SIZE_BYTES, ALLOWED_EXTENSIONS, GRAP_MAPPING_VERSION,
    GRAP_COMPLIANCE_YEAR, PDF_PAGE_SIZE, PDF_MARGIN_TOP_CM,
    PDF_MARGIN_BOTTOM_CM, PDF_MARGIN_LEFT_CM, PDF_MARGIN_RIGHT_CM,
    RATIO_BENCHMARKS, SESSION_LIFETIME_HOURS, SECRET_KEY_DEFAULT
)


class Config:
    """Base configuration class"""
    
    # Flask Configuration
    SECRET_KEY = os.environ.get('SECRET_KEY') or SECRET_KEY_DEFAULT
    
    # File Upload Configuration
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'uploads')
    OUTPUT_FOLDER = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'outputs')
    MAX_CONTENT_LENGTH = MAX_FILE_SIZE_BYTES
    
    # Allowed file extensions
    ALLOWED_EXTENSIONS = ALLOWED_EXTENSIONS
    
    # GRAP Configuration
    GRAP_MAPPING_VERSION = GRAP_MAPPING_VERSION
    GRAP_COMPLIANCE_YEAR = GRAP_COMPLIANCE_YEAR
    
    # PDF Configuration
    PDF_PAGE_SIZE = PDF_PAGE_SIZE
    PDF_MARGIN_TOP = PDF_MARGIN_TOP_CM
    PDF_MARGIN_BOTTOM = PDF_MARGIN_BOTTOM_CM
    PDF_MARGIN_LEFT = PDF_MARGIN_LEFT_CM
    PDF_MARGIN_RIGHT = PDF_MARGIN_RIGHT_CM
    
    # Financial Ratios Benchmarks
    RATIO_BENCHMARKS = RATIO_BENCHMARKS
    
    # Session Configuration
    PERMANENT_SESSION_LIFETIME = timedelta(hours=SESSION_LIFETIME_HOURS)
    
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
