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


class DataManager:
    """Handles data storage and retrieval operations"""
    
    def __init__(self, data_directory: str = "data", use_s3: bool = False, s3_bucket: str = None):
        self.data_directory = Path(data_directory)
        self.data_directory.mkdir(exist_ok=True)
        self.use_s3 = use_s3
        self.s3_bucket = s3_bucket
        self.s3_client = boto3.client('s3') if use_s3 else None
    
    def get_team_file_path(self, team_name: str) -> Path:
        """Get the file path for a team's data"""
        return self.data_directory / f"{team_name}_efficiency_data.xlsx"
    
    def load_team_data(self, team_name: str) -> pd.DataFrame:
        """Load team data from Excel file"""
        file_path = self.get_team_file_path(team_name)
        
        if self.use_s3 and self.s3_bucket:
            try:
                # Download from S3
                s3_key = f"teams/{team_name}_efficiency_data.xlsx"
                self.s3_client.download_file(self.s3_bucket, s3_key, str(file_path))
            except ClientError:
                # File doesn't exist in S3, return empty dataframe
                return pd.DataFrame()
        
        if file_path.exists():
            try:
                return pd.read_excel(file_path)
            except Exception:
                return pd.DataFrame()
        
        return pd.DataFrame()
    
    def save_team_data(self, team_name: str, data: pd.DataFrame) -> bool:
        """Save team data to Excel file"""
        try:
            file_path = self.get_team_file_path(team_name)
            data.to_excel(file_path, index=False)
            
            if self.use_s3 and self.s3_bucket:
                # Upload to S3
                s3_key = f"teams/{team_name}_efficiency_data.xlsx"
                self.s3_client.upload_file(str(file_path), self.s3_bucket, s3_key)
            
            return True
        except Exception as e:
            print(f"Error saving team data: {e}")
            return False


class TeamsConfigManager:
    """Manages team configuration data"""
    
    def __init__(self, data_directory: str = "data", use_s3: bool = False, s3_bucket: str = None):
        self.data_directory = Path(data_directory)
        self.data_directory.mkdir(exist_ok=True)
        self.config_file = self.data_directory / "teams_config.json"
        self.use_s3 = use_s3
        self.s3_bucket = s3_bucket
        self.s3_client = boto3.client('s3') if use_s3 else None
    
    def load_teams_config(self) -> Dict[str, List[Dict[str, str]]]:
        """Load teams configuration"""
        if self.use_s3 and self.s3_bucket:
            try:
                # Download from S3
                s3_key = "config/teams_config.json"
                self.s3_client.download_file(self.s3_bucket, s3_key, str(self.config_file))
            except ClientError:
                pass  # File doesn't exist, will use local or create new
        
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            except Exception:
                return {}
        
        return {}
    
    def save_teams_config(self, config: Dict[str, List[Dict[str, str]]]) -> bool:
        """Save teams configuration"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2)
            
            if self.use_s3 and self.s3_bucket:
                # Upload to S3
                s3_key = "config/teams_config.json"
                self.s3_client.upload_file(str(self.config_file), self.s3_bucket, s3_key)
            
            return True
        except Exception as e:
            print(f"Error saving teams config: {e}")
            return False


class TeamSettingsManager:
    """Manages team settings (categories, efficiency areas, etc.)"""
    
    def __init__(self, data_directory: str = "data", use_s3: bool = False, s3_bucket: str = None):
        self.data_directory = Path(data_directory)
        self.data_directory.mkdir(exist_ok=True)
        self.settings_file = self.data_directory / "team_settings.json"
        self.use_s3 = use_s3
        self.s3_bucket = s3_bucket
        self.s3_client = boto3.client('s3') if use_s3 else None
        
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
        """Load team settings"""
        if self.use_s3 and self.s3_bucket:
            try:
                # Download from S3
                s3_key = "config/team_settings.json"
                self.s3_client.download_file(self.s3_bucket, s3_key, str(self.settings_file))
            except ClientError:
                pass  # File doesn't exist, will use local or defaults
        
        if self.settings_file.exists():
            try:
                with open(self.settings_file, 'r') as f:
                    return json.load(f)
            except Exception:
                return self.default_settings
        
        return self.default_settings
    
    def save_team_settings(self, settings: Dict[str, Any]) -> bool:
        """Save team settings"""
        try:
            with open(self.settings_file, 'w') as f:
                json.dump(settings, f, indent=2)
            
            if self.use_s3 and self.s3_bucket:
                # Upload to S3
                s3_key = "config/team_settings.json"
                self.s3_client.upload_file(str(self.settings_file), self.s3_bucket, s3_key)
            
            return True
        except Exception as e:
            print(f"Error saving team settings: {e}")
            return False


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