"""
SADPMR Financial Reporting System - Custom Exceptions
Centralized exception handling for better error management
"""


class SADPMRException(Exception):
    """Base exception for SADPMR application"""
    
    def __init__(self, message, error_code=None, status_code=500):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.status_code = status_code


class ValidationError(SADPMRException):
    """Raised when data validation fails"""
    
    def __init__(self, message, field=None):
        super().__init__(message, 'VALIDATION_ERROR', 400)
        self.field = field


class FileProcessingError(SADPMRException):
    """Raised when file processing fails"""
    
    def __init__(self, message, filename=None):
        super().__init__(message, 'FILE_PROCESSING_ERROR', 400)
        self.filename = filename


class MappingError(SADPMRException):
    """Raised when GRAP mapping fails"""
    
    def __init__(self, message, account_code=None):
        super().__init__(message, 'MAPPING_ERROR', 422)
        self.account_code = account_code


class ReportGenerationError(SADPMRException):
    """Raised when PDF report generation fails"""
    
    def __init__(self, message, report_type=None):
        super().__init__(message, 'REPORT_GENERATION_ERROR', 500)
        self.report_type = report_type


class ConfigurationError(SADPMRException):
    """Raised when configuration is invalid"""
    
    def __init__(self, message, config_key=None):
        super().__init__(message, 'CONFIGURATION_ERROR', 500)
        self.config_key = config_key
