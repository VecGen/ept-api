"""
Pydantic models for API request/response schemas
"""

from pydantic import BaseModel, validator
from typing import List, Optional, Dict, Any
from datetime import date, datetime


# Authentication schemas
class LoginRequest(BaseModel):
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_type: str


class EngineerLoginRequest(BaseModel):
    developer_name: str
    team_name: str


# Team schemas
class Developer(BaseModel):
    name: str
    email: Optional[str] = None
    link: Optional[str] = None


class Team(BaseModel):
    name: str
    description: Optional[str] = None
    developers: List[Developer] = []


class CreateTeamRequest(BaseModel):
    team_name: str
    description: Optional[str] = None


class AddDeveloperRequest(BaseModel):
    dev_name: str
    dev_email: Optional[str] = None


# Data entry schemas
class EfficiencyEntry(BaseModel):
    week: date
    story_id: str
    developer_name: str
    team_name: str
    technology: Optional[str] = None
    original_estimate_hours: float
    efficiency_gained_hours: float
    category: str
    area_of_efficiency: str
    copilot_used: str
    task_type: Optional[str] = None
    completion_type: Optional[str] = None
    lines_of_code_saved: Optional[int] = None
    subjective_ease_rating: Optional[int] = None
    review_time_saved_hours: Optional[float] = None
    bugs_prevented: Optional[str] = None
    pr_merged_status: Optional[str] = None
    notes: Optional[str] = None
    
    @validator('efficiency_gained_hours')
    def validate_efficiency_gained(cls, v, values):
        if 'original_estimate_hours' in values and v > values['original_estimate_hours']:
            raise ValueError('Efficiency gained cannot be greater than original estimate')
        return v


class CreateEntryRequest(BaseModel):
    week_date: date
    story_id: str
    original_estimate: float
    efficiency_gained: float
    copilot_used: str
    category: str
    efficiency_areas: List[str]
    notes: Optional[str] = None


# Dashboard schemas
class TeamStats(BaseModel):
    team_name: str
    total_time_saved: float
    total_entries: int
    average_efficiency: float
    copilot_usage_rate: float
    developers_count: int


class DashboardStats(BaseModel):
    total_time_saved: float
    total_entries: int
    average_efficiency: float
    copilot_usage_rate: float
    teams_count: int
    developers_count: int
    team_stats: List[TeamStats]


class EngineerStats(BaseModel):
    developer_name: str
    team_name: str
    total_time_saved: float
    total_entries: int
    average_efficiency: float
    recent_entries: List[Dict[str, Any]]


# Team settings schemas
class TeamSettings(BaseModel):
    categories: List[str]
    efficiency_areas: List[str]
    category_efficiency_mapping: Dict[str, List[str]]


class UpdateSettingsRequest(BaseModel):
    categories: Optional[List[str]] = None
    efficiency_areas: Optional[List[str]] = None
    category_efficiency_mapping: Optional[Dict[str, List[str]]] = None


# Data management schemas
class ExportRequest(BaseModel):
    teams: List[str]
    export_type: str = "combined"  # "combined" or "individual"


# Response schemas
class ApiResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Any] = None


class ErrorResponse(BaseModel):
    success: bool = False
    message: str
    detail: Optional[str] = None 