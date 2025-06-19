"""
Configuration management for the Developer Efficiency Tracker API
"""

from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    """Application settings"""
    
    # App settings
    app_name: str = "Developer Efficiency Tracker API"
    debug: bool = False
    
    # Security
    secret_key: str = "your-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440  # 24 hours
    admin_password: str = "admin123"
    
    # AWS settings
    aws_region: str = "us-east-1"
    s3_bucket_name: Optional[str] = None
    use_s3: bool = False
    
    # Database/Storage
    data_directory: str = "data"
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        
        # Map environment variables
        fields = {
            'secret_key': {'env': 'SECRET_KEY'},
            'admin_password': {'env': 'ADMIN_PASSWORD'},
            'aws_region': {'env': 'AWS_REGION'},
            's3_bucket_name': {'env': 'S3_BUCKET_NAME'},
            'use_s3': {'env': 'USE_S3'},
            'debug': {'env': 'DEBUG'},
        }


def get_settings() -> Settings:
    """Get application settings"""
    return Settings() 