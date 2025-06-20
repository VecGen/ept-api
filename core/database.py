"""
Standalone database and data management for the FastAPI backend
"""

import os
import json
import pandas as pd
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
import boto3
from botocore.exceptions import ClientError
from fastapi import HTTPException, status
import urllib.parse


class DataManager:
    """Handles data storage and retrieval operations - S3 ONLY"""
    
    def __init__(self, data_directory: str = "data", use_s3: bool = False, s3_bucket: str = None):
        self.data_directory = Path(data_directory)
        self.use_s3 = use_s3
        self.s3_bucket = s3_bucket
        
        if not self.use_s3 or not self.s3_bucket:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="S3 configuration required. Set USE_S3=true and S3_BUCKET_NAME"
            )
            
        try:
            self.s3_client = boto3.client('s3')
            # Test S3 connection
            self.s3_client.head_bucket(Bucket=self.s3_bucket)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to connect to S3: {str(e)}"
            )
    
    def load_team_data(self, team_name: str) -> pd.DataFrame:
        """Load team data from S3 only - Returns empty DataFrame if file doesn't exist"""
        try:
            # Try multiple S3 key variations to handle different naming conventions
            key_variations = [
                # Original URL-encoded approach (this one is working from logs)
                f"teams/{urllib.parse.quote(team_name, safe='')}_efficiency_data.xlsx",
                # Replace spaces with underscores
                f"teams/{team_name.replace(' ', '_')}_efficiency_data.xlsx",
                # Replace spaces with hyphens
                f"teams/{team_name.replace(' ', '-')}_efficiency_data.xlsx",
                # No spaces (concatenated)
                f"teams/{team_name.replace(' ', '')}_efficiency_data.xlsx",
                # Original team name as-is
                f"teams/{team_name}_efficiency_data.xlsx"
            ]
            
            # Create temp file for S3 download
            encoded_team_name = urllib.parse.quote(team_name, safe='')
            temp_file = self.data_directory / f"temp_{encoded_team_name}_efficiency_data.xlsx"
            self.data_directory.mkdir(exist_ok=True)
            
            last_error = None
            
            for s3_key in key_variations:
                try:
                    print(f"🔍 Loading S3 key: {s3_key}")
                    response = self.s3_client.get_object(Bucket=self.s3_bucket, Key=s3_key)
                    
                    # Save to temp file and read
                    with open(temp_file, 'wb') as f:
                        f.write(response['Body'].read())
                    
                    df = pd.read_excel(temp_file)
                    
                    # Clean up temp file
                    if temp_file.exists():
                        temp_file.unlink()
                        
                    print(f"✅ Successfully loaded {len(df)} rows from S3")
                    return df
                    
                except ClientError as e:
                    error_code = e.response['Error']['Code']
                    if error_code in ['NoSuchKey', '404', 'NotFound']:
                        # Key not found, try next variation
                        last_error = e
                        continue
                    else:
                        # For other S3 errors, log but continue trying other keys
                        print(f"⚠️ S3 error with key {s3_key}: {str(e)}")
                        last_error = e
                        continue
                except Exception as file_error:
                    # Handle any file processing errors
                    print(f"⚠️ File processing error with key {s3_key}: {str(file_error)}")
                    last_error = file_error
                    continue
                finally:
                    # Ensure temp file is cleaned up after each attempt
                    if temp_file.exists():
                        temp_file.unlink()
            
            # If we get here, none of the key variations worked
            print(f"📁 No existing data file found for team '{team_name}' using any naming convention")
            return pd.DataFrame()
                    
        except Exception as e:
            # For any other unexpected errors, log and return empty DataFrame to prevent 500 errors
            print(f"⚠️ Unexpected error in load_team_data (returning empty data): {str(e)}")
            print(f"   Exception type: {type(e).__name__}")
            return pd.DataFrame()
    
    def save_team_data(self, team_name: str, data: pd.DataFrame) -> bool:
        """Save team data to S3 only"""
        try:
            # URL encode team name for S3 key to handle spaces and special characters
            encoded_team_name = urllib.parse.quote(team_name, safe='')
            
            # Create temp file
            temp_file = self.data_directory / f"temp_{encoded_team_name}_efficiency_data.xlsx"
            self.data_directory.mkdir(exist_ok=True)
            
            try:
                data.to_excel(temp_file, index=False)
                
                # Upload to S3
                s3_key = f"teams/{encoded_team_name}_efficiency_data.xlsx"
                print(f"🔄 Uploading to S3 key: {s3_key}")
                self.s3_client.upload_file(str(temp_file), self.s3_bucket, s3_key)
                
                # Clean up temp file
                temp_file.unlink()
                print(f"✅ Successfully saved to S3")
                return True
                
            except Exception as e:
                # Clean up temp file on error
                if temp_file.exists():
                    temp_file.unlink()
                print(f"❌ Error saving to S3: {str(e)}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to save team data to S3: {str(e)}"
                )
                
        except Exception as e:
            print(f"❌ Unexpected error in save_team_data: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error saving team data: {str(e)}"
            )


class TeamsConfigManager:
    """Manages team configuration data - S3 ONLY"""
    
    def __init__(self, data_directory: str = "data", use_s3: bool = False, s3_bucket: str = None):
        self.data_directory = Path(data_directory)
        self.use_s3 = use_s3
        self.s3_bucket = s3_bucket
        
        if not self.use_s3 or not self.s3_bucket:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="S3 configuration required. Set USE_S3=true and S3_BUCKET_NAME"
            )
            
        try:
            self.s3_client = boto3.client('s3')
            # Test S3 connection
            self.s3_client.head_bucket(Bucket=self.s3_bucket)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to connect to S3: {str(e)}"
            )
    
    def load_teams_config(self) -> Dict[str, List[Dict[str, str]]]:
        """Load teams configuration from S3 only"""
        try:
            s3_key = "config/teams_config.json"
            
            try:
                response = self.s3_client.get_object(Bucket=self.s3_bucket, Key=s3_key)
                config_data = response['Body'].read().decode('utf-8')
                return json.loads(config_data)
            except ClientError as e:
                error_code = e.response['Error']['Code']
                if error_code in ['NoSuchKey', '404', 'NotFound']:
                    # File doesn't exist, return empty config instead of raising exception
                    print(f"📁 No teams config file found in S3, returning empty config")
                    return {}
                else:
                    # Other S3 errors should still raise exceptions
                    print(f"❌ S3 error loading teams config: {str(e)}")
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail=f"Failed to load teams config from S3: {str(e)}"
                    )
                    
        except HTTPException:
            # Re-raise HTTPExceptions as-is
            raise
        except Exception as e:
            print(f"❌ Unexpected error loading teams config: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error loading teams config: {str(e)}"
            )
    
    def save_teams_config(self, config: Dict[str, List[Dict[str, str]]]) -> bool:
        """Save teams configuration to S3 only"""
        try:
            s3_key = "config/teams_config.json"
            config_json = json.dumps(config, indent=2)
            
            self.s3_client.put_object(
                Bucket=self.s3_bucket,
                Key=s3_key,
                Body=config_json,
                ContentType='application/json'
            )
            return True
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to save teams config to S3: {str(e)}"
            )


class TeamSettingsManager:
    """Manages team settings (categories, efficiency areas, etc.) - S3 ONLY"""
    
    def __init__(self, data_directory: str = "data", use_s3: bool = False, s3_bucket: str = None):
        self.data_directory = Path(data_directory)
        self.use_s3 = use_s3
        self.s3_bucket = s3_bucket
        
        if not self.use_s3 or not self.s3_bucket:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="S3 configuration required. Set USE_S3=true and S3_BUCKET_NAME"
            )
            
        try:
            self.s3_client = boto3.client('s3')
            # Test S3 connection
            self.s3_client.head_bucket(Bucket=self.s3_bucket)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to connect to S3: {str(e)}"
            )
        
        # Default settings
        self.default_settings = {
            "categories": [
                "Feature Development",
                "Bug Fixes", 
                "Code Review",
                "Testing",
                "Documentation",
                "Refactoring",
                "API Development",
                "Database Work"
            ],
            "efficiency_areas": [
                "Code Generation",
                "Code Completion",
                "API Design", 
                "Documentation",
                "Debugging",
                "Code Analysis",
                "Test Writing",
                "Refactoring",
                "Test Data Creation",
                "Query Optimization"
            ],
            "category_efficiency_mapping": {
                "Feature Development": ["Code Generation", "Code Completion", "API Design"],
                "Bug Fixes": ["Debugging", "Code Analysis"],
                "Code Review": ["Code Analysis", "Documentation"],
                "Testing": ["Test Writing", "Test Data Creation"],
                "Documentation": ["Documentation", "Code Generation"],
                "Refactoring": ["Refactoring", "Code Analysis"],
                "API Development": ["API Design", "Code Generation"],
                "Database Work": ["Query Optimization", "Code Generation"]
            }
        }
    
    def load_team_settings(self) -> Dict[str, Any]:
        """Load team settings from S3, create default if not exists"""
        try:
            s3_key = "config/team_settings.json"
            
            try:
                response = self.s3_client.get_object(Bucket=self.s3_bucket, Key=s3_key)
                settings_data = response['Body'].read().decode('utf-8')
                return json.loads(settings_data)
            except ClientError as e:
                if e.response['Error']['Code'] == 'NoSuchKey':
                    # File doesn't exist, create default settings in S3
                    self.save_team_settings(self.default_settings)
                    return self.default_settings
                else:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail=f"Failed to load team settings from S3: {str(e)}"
                    )
                    
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error loading team settings: {str(e)}"
            )
    
    def save_team_settings(self, settings: Dict[str, Any]) -> bool:
        """Save team settings to S3 only"""
        try:
            s3_key = "config/team_settings.json"
            settings_json = json.dumps(settings, indent=2)
            
            self.s3_client.put_object(
                Bucket=self.s3_bucket,
                Key=s3_key,
                Body=settings_json,
                ContentType='application/json'
            )
            return True
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to save team settings to S3: {str(e)}"
            )


# Global instances
_data_manager = None
_teams_config_manager = None 
_team_settings_manager = None


def init_data_managers(settings):
    """Initialize data managers"""
    global _data_manager, _teams_config_manager, _team_settings_manager
    
    _data_manager = DataManager(
        data_directory=settings.data_directory,
        use_s3=settings.use_s3,
        s3_bucket=settings.s3_bucket_name
    )
    
    _teams_config_manager = TeamsConfigManager(
        data_directory=settings.data_directory,
        use_s3=settings.use_s3,
        s3_bucket=settings.s3_bucket_name
    )
    
    _team_settings_manager = TeamSettingsManager(
        data_directory=settings.data_directory,
        use_s3=settings.use_s3,
        s3_bucket=settings.s3_bucket_name
    )


def get_data_manager_instance() -> DataManager:
    """Get data manager instance"""
    return _data_manager


def get_teams_config_manager_instance() -> TeamsConfigManager:
    """Get teams config manager instance"""
    return _teams_config_manager


def get_team_settings_manager_instance() -> TeamSettingsManager:
    """Get team settings manager instance"""
    return _team_settings_manager 