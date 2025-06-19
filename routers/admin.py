"""
Admin router for dashboard and management functionality
"""

from fastapi import APIRouter, HTTPException, status, Depends
from typing import List
import pandas as pd

from models.schemas import DashboardStats, TeamStats, TeamSettings, UpdateSettingsRequest, ApiResponse
from core.auth import verify_admin_token
from core.database import (
    get_data_manager_instance, 
    get_teams_config_manager_instance,
    get_team_settings_manager_instance
)

router = APIRouter()


@router.get("/dashboard", response_model=DashboardStats)
async def get_admin_dashboard(token_data: dict = Depends(verify_admin_token)):
    """Get admin dashboard statistics"""
    data_manager = get_data_manager_instance()
    teams_config_manager = get_teams_config_manager_instance()
    
    teams_config = teams_config_manager.load_teams_config()
    team_stats = []
    combined_df = pd.DataFrame()
    
    for team_name in teams_config.keys():
        df = data_manager.load_team_data(team_name)
        
        if not df.empty:
            combined_df = pd.concat([combined_df, df], ignore_index=True)
            
            # Calculate team stats
            total_time_saved = float(df['Efficiency_Gained_Hours'].sum())
            total_entries = len(df)
            
            # Calculate average efficiency
            valid_estimates = df[df['Original_Estimate_Hours'] > 0]
            if not valid_estimates.empty:
                average_efficiency = float(
                    (valid_estimates['Efficiency_Gained_Hours'].sum() / 
                     valid_estimates['Original_Estimate_Hours'].sum()) * 100
                )
            else:
                average_efficiency = 0.0
            
            # Calculate Copilot usage rate
            copilot_usage_rate = float(
                (df['Copilot_Used'] == 'Yes').sum() / len(df) * 100
            ) if len(df) > 0 else 0.0
            
            # Count unique developers
            developers_count = df['Developer_Name'].nunique()
            
            team_stats.append(TeamStats(
                team_name=team_name,
                total_time_saved=total_time_saved,
                total_entries=total_entries,
                average_efficiency=average_efficiency,
                copilot_usage_rate=copilot_usage_rate,
                developers_count=developers_count
            ))
    
    # Calculate overall stats
    if not combined_df.empty:
        total_time_saved = float(combined_df['Efficiency_Gained_Hours'].sum())
        total_entries = len(combined_df)
        
        valid_estimates = combined_df[combined_df['Original_Estimate_Hours'] > 0]
        if not valid_estimates.empty:
            average_efficiency = float(
                (valid_estimates['Efficiency_Gained_Hours'].sum() / 
                 valid_estimates['Original_Estimate_Hours'].sum()) * 100
            )
        else:
            average_efficiency = 0.0
        
        copilot_usage_rate = float(
            (combined_df['Copilot_Used'] == 'Yes').sum() / len(combined_df) * 100
        )
        
        developers_count = combined_df['Developer_Name'].nunique()
    else:
        total_time_saved = 0.0
        total_entries = 0
        average_efficiency = 0.0
        copilot_usage_rate = 0.0
        developers_count = 0
    
    return DashboardStats(
        total_time_saved=total_time_saved,
        total_entries=total_entries,
        average_efficiency=average_efficiency,
        copilot_usage_rate=copilot_usage_rate,
        teams_count=len(teams_config),
        developers_count=developers_count,
        team_stats=team_stats
    )


@router.get("/settings", response_model=TeamSettings)
async def get_team_settings(token_data: dict = Depends(verify_admin_token)):
    """Get team settings"""
    settings_manager = get_team_settings_manager_instance()
    settings = settings_manager.load_team_settings()
    
    return TeamSettings(**settings)


@router.put("/settings", response_model=ApiResponse)
async def update_team_settings(
    settings_data: UpdateSettingsRequest,
    token_data: dict = Depends(verify_admin_token)
):
    """Update team settings"""
    settings_manager = get_team_settings_manager_instance()
    current_settings = settings_manager.load_team_settings()
    
    # Update only provided fields
    if settings_data.categories is not None:
        current_settings['categories'] = settings_data.categories
    
    if settings_data.efficiency_areas is not None:
        current_settings['efficiency_areas'] = settings_data.efficiency_areas
    
    if settings_data.category_efficiency_mapping is not None:
        current_settings['category_efficiency_mapping'] = settings_data.category_efficiency_mapping
    
    if settings_manager.save_team_settings(current_settings):
        return ApiResponse(
            success=True,
            message="Team settings updated successfully"
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save team settings"
        )


@router.get("/teams/{team_name}/data")
async def get_team_data(
    team_name: str,
    token_data: dict = Depends(verify_admin_token)
):
    """Get data for a specific team"""
    data_manager = get_data_manager_instance()
    teams_config_manager = get_teams_config_manager_instance()
    
    teams_config = teams_config_manager.load_teams_config()
    
    if team_name not in teams_config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Team '{team_name}' not found"
        )
    
    df = data_manager.load_team_data(team_name)
    
    if df.empty:
        return {
            "success": True,
            "data": {
                "entries": [],
                "stats": {
                    "total_time_saved": 0.0,
                    "total_entries": 0,
                    "average_efficiency": 0.0,
                    "copilot_usage_rate": 0.0
                }
            }
        }
    
    # Convert dataframe to records for JSON serialization
    entries = df.to_dict('records')
    
    # Convert pandas data types to Python native types
    for entry in entries:
        for key, value in entry.items():
            if pd.isna(value):
                entry[key] = None
            elif isinstance(value, (pd.Timestamp, pd.Period)):
                entry[key] = str(value)
            elif hasattr(value, 'item'):  # numpy types
                entry[key] = value.item()
    
    # Calculate stats
    total_time_saved = float(df['Efficiency_Gained_Hours'].sum())
    total_entries = len(df)
    
    valid_estimates = df[df['Original_Estimate_Hours'] > 0]
    if not valid_estimates.empty:
        average_efficiency = float(
            (valid_estimates['Efficiency_Gained_Hours'].sum() / 
             valid_estimates['Original_Estimate_Hours'].sum()) * 100
        )
    else:
        average_efficiency = 0.0
    
    copilot_usage_rate = float(
        (df['Copilot_Used'] == 'Yes').sum() / len(df) * 100
    ) if len(df) > 0 else 0.0
    
    return {
        "success": True,
        "data": {
            "entries": entries,
            "stats": {
                "total_time_saved": total_time_saved,
                "total_entries": total_entries,
                "average_efficiency": average_efficiency,
                "copilot_usage_rate": copilot_usage_rate
            }
        }
    } 