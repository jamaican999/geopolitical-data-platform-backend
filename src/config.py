# Production environment configuration
import os
from urllib.parse import urlparse

class Config:
    """Base configuration class"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # CORS settings for production
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', '*').split(',')
    
    # Database configuration - supports both PostgreSQL and Supabase
    DATABASE_URL = os.environ.get('DATABASE_URL')
    SUPABASE_URL = os.environ.get('SUPABASE_URL')
    SUPABASE_KEY = os.environ.get('SUPABASE_KEY')
    
    if SUPABASE_URL and SUPABASE_KEY:
        # Use Supabase connection
        # Extract project ID from Supabase URL
        project_id = SUPABASE_URL.replace('https://', '' ).replace('.supabase.co', '')
        SQLALCHEMY_DATABASE_URI = f'postgresql://postgres:{SUPABASE_KEY}@db.{project_id}.supabase.co:5432/postgres'
    elif DATABASE_URL:
        # Handle PostgreSQL URL format
        if DATABASE_URL.startswith('postgres://'):
            DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
        SQLALCHEMY_DATABASE_URI = DATABASE_URL
    else:
        # Fallback to SQLite for development
        SQLALCHEMY_DATABASE_URI = 'sqlite:///geopolitical_data.db'
    
    # Application settings
    DEBUG = False
    TESTING = False
    
    # Logging configuration
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    
    # External API settings
    CIA_FACTBOOK_URL = 'https://raw.githubusercontent.com/factbook/factbook.json/master'
    
    # Rate limiting
    RATELIMIT_STORAGE_URL = os.environ.get('REDIS_URL', 'memory://' )

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///geopolitical_data.db'

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    
    # Get SECRET_KEY from environment, with fallback for development
    _secret_key = os.environ.get('SECRET_KEY', '').strip().strip('"').strip("'")
    if not _secret_key:
        # Generate a secure fallback if not set
        import secrets
        _secret_key = secrets.token_hex(32)
    SECRET_KEY = _secret_key

class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'

# Configuration mapping
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
