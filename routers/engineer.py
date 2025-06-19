"""
Engineer router for data entry and dashboard
"""

from fastapi import APIRouter, HTTPException, status, Depends
import pandas as pd
from datetime import datetime, timedelta

from models.schemas import CreateEntryRequest, ApiResponse, EngineerStats
from core.auth import verify_engineer_token
from core.database import get_data_manager_instance, get_team_settings_manager_instance

router = APIRouter()


def get_week_dates(date_input):
    """Get Monday and Sunday for the week containing the given date"""
    if isinstance(date_input, str):
        date_input = datetime.strptime(date_input, '%Y-%m-%d').date()
    
    # Find Monday of the week
    days_since_monday = date_input.weekday()
    monday = date_input - timedelta(days=days_since_monday)
    sunday = monday + timedelta(days=6)
    
    return monday, sunday


@router.post("/entry", response_model=ApiResponse)
async def create_entry(
    entry_data: CreateEntryRequest,
    token_data: dict = Depends(verify_engineer_token)
):
    """Create a new efficiency entry"""
    data_manager = get_data_manager_instance()
    
    developer_name = token_data.get("sub")
    team_name = token_data.get("team")
    
    # Get week dates
    selected_monday, selected_sunday = get_week_dates(entry_data.week_date)
    
    # Load existing data
    df = data_manager.load_team_data(team_name)
    
    # Create new entry
    new_entry = {
        'Week': selected_monday.strftime('%Y-%m-%d'),
        'Week_End': selected_sunday.strftime('%Y-%m-%d'),
        'Story_ID': entry_data.story_id,
        'Developer_Name': developer_name,
        'Team_Name': team_name,
        'Technology': 'General',  # Default value
        'Original_Estimate_Hours': entry_data.original_estimate,
        'Efficiency_Gained_Hours': entry_data.efficiency_gained,
        'Category': entry_data.category,
        'Area_of_Efficiency': ', '.join(entry_data.efficiency_areas),
        'Copilot_Used': entry_data.copilot_used,
        'Task_Type': 'General',  # Default value
        'Completion_Type': 'Inline Suggestion' if entry_data.copilot_used == 'Yes' else 'Manual',
        'Lines_of_Code_Saved': None,
        'Subjective_Ease_Rating': None,
        'Review_Time_Saved_Hours': None,
        'Bugs_Prevented': None,
        'PR_Merged_Status': None,
        'Notes': entry_data.notes or '',
        'Timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    # Add calculated fields
    efficiency_percentage = (entry_data.efficiency_gained / entry_data.original_estimate) * 100 if entry_data.original_estimate > 0 else 0
    new_entry['Efficiency_Percentage'] = efficiency_percentage
    
    # Add new entry to dataframe
    if df.empty:
        df = pd.DataFrame([new_entry])
    else:
        df = pd.concat([df, pd.DataFrame([new_entry])], ignore_index=True)
    
    # Save data
    if data_manager.save_team_data(team_name, df):
        return ApiResponse(
            success=True,
            message="Entry created successfully"
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save entry"
        )


@router.get("/dashboard", response_model=EngineerStats)
async def get_engineer_dashboard(token_data: dict = Depends(verify_engineer_token)):
    """Get engineer dashboard data"""
    data_manager = get_data_manager_instance()
    
    developer_name = token_data.get("sub")
    team_name = token_data.get("team")
    
    # Load engineer's data
    df = data_manager.load_team_data(team_name)
    
    if df.empty:
        return EngineerStats(
            developer_name=developer_name,
            team_name=team_name,
            total_time_saved=0.0,
            total_entries=0,
            average_efficiency=0.0,
            recent_entries=[]
        )
    
    engineer_df = df[df['Developer_Name'] == developer_name]
    
    if engineer_df.empty:
        return EngineerStats(
            developer_name=developer_name,
            team_name=team_name,
            total_time_saved=0.0,
            total_entries=0,
            average_efficiency=0.0,
            recent_entries=[]
        )
    
    # Calculate stats
    total_time_saved = float(engineer_df['Efficiency_Gained_Hours'].sum())
    total_entries = len(engineer_df)
    
    # Calculate average efficiency
    valid_estimates = engineer_df[engineer_df['Original_Estimate_Hours'] > 0]
    if not valid_estimates.empty:
        average_efficiency = float(
            (valid_estimates['Efficiency_Gained_Hours'].sum() / 
             valid_estimates['Original_Estimate_Hours'].sum()) * 100
        )
    else:
        average_efficiency = 0.0
    
    # Get recent entries (last 10)
    recent_entries = engineer_df.tail(10).to_dict('records')
    
    # Convert pandas data types to Python native types for JSON serialization
    for entry in recent_entries:
        for key, value in entry.items():
            if pd.isna(value):
                entry[key] = None
            elif isinstance(value, (pd.Timestamp, pd.Period)):
                entry[key] = str(value)
            elif hasattr(value, 'item'):  # numpy types
                entry[key] = value.item()
    
    return EngineerStats(
        developer_name=developer_name,
        team_name=team_name,
        total_time_saved=total_time_saved,
        total_entries=total_entries,
        average_efficiency=average_efficiency,
        recent_entries=recent_entries
    )


@router.get("/settings")
async def get_team_settings(token_data: dict = Depends(verify_engineer_token)):
    """Get team settings for form options"""
    settings_manager = get_team_settings_manager_instance()
    settings = settings_manager.load_team_settings()
    
    return {
        "success": True,
        "data": settings
    } 