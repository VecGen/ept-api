"""
Engineer router for data entry and dashboard - Public access for testing
"""

from fastapi import APIRouter, HTTPException, status, Query
import pandas as pd
from datetime import datetime, timedelta

from models.schemas import CreateEntryRequest, ApiResponse, EngineerStats, EntriesResponse
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
    developer_name: str = Query(..., description="Developer name"),
    team_name: str = Query(..., description="Team name")
):
    """Create a new efficiency entry - no authentication required for testing"""
    try:
        data_manager = get_data_manager_instance()
        
        print(f"🔄 Creating entry for developer: {developer_name}, team: {team_name}")
        
        if not developer_name or not team_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Missing developer name or team. Developer: {developer_name}, Team: {team_name}"
            )
        
        # Get week dates
        selected_monday, selected_sunday = get_week_dates(entry_data.week_date)
        print(f"📅 Week dates: {selected_monday} to {selected_sunday}")
        
        # Load existing data
        print(f"📂 Loading team data for: {team_name}")
        try:
            df = data_manager.load_team_data(team_name)
            print(f"📊 Loaded {len(df)} existing entries")
        except Exception as load_error:
            print(f"❌ Error loading team data: {str(load_error)}")
            print(f"   Load error type: {type(load_error).__name__}")
            raise load_error
        
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
        
        print(f"📝 Created new entry: {new_entry['Story_ID']}")
        
        # Add new entry to dataframe
        if df.empty:
            df = pd.DataFrame([new_entry])
        else:
            df = pd.concat([df, pd.DataFrame([new_entry])], ignore_index=True)
        
        print(f"💾 Saving {len(df)} entries to S3...")
        
        # Save data
        save_result = data_manager.save_team_data(team_name, df)
        
        if save_result:
            print(f"✅ Successfully saved entry for {developer_name}")
            return ApiResponse(
                success=True,
                message="Entry created successfully"
            )
        else:
            print(f"❌ Failed to save entry for {developer_name}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to save entry"
            )
            
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        print(f"❌ Unexpected error creating entry: {str(e)}")
        print(f"   Error type: {type(e).__name__}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error creating entry: {str(e)}"
        )


@router.get("/dashboard", response_model=EngineerStats)
async def get_engineer_dashboard(
    developer_name: str = Query(..., description="Developer name"),
    team_name: str = Query(..., description="Team name")
):
    """Get engineer dashboard data - no authentication required for testing"""
    data_manager = get_data_manager_instance()
    
    print(f"🔍 Getting dashboard for developer: {developer_name}, team: {team_name}")
    
    # Load engineer's data
    try:
        df = data_manager.load_team_data(team_name)
        print(f"📊 Loaded {len(df)} total entries for team {team_name}")
    except Exception as e:
        print(f"❌ Error loading team data: {str(e)}")
        return EngineerStats(
            developer_name=developer_name,
            team_name=team_name,
            total_time_saved=0.0,
            total_entries=0,
            average_efficiency=0.0,
            recent_entries=[]
        )
    
    if df.empty:
        print(f"📊 No data found for team {team_name}")
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
        print(f"📊 No entries found for developer {developer_name}")
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
    
    print(f"📊 Developer {developer_name} stats: {total_entries} entries, {total_time_saved}h saved")
    
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
    
    print(f"✅ Returning dashboard data for {developer_name}")
    return EngineerStats(
        developer_name=developer_name,
        team_name=team_name,
        total_time_saved=total_time_saved,
        total_entries=total_entries,
        average_efficiency=average_efficiency,
        recent_entries=recent_entries
    )


@router.get("/settings")
async def get_team_settings():
    """Get team settings for form options - no authentication required for testing"""
    try:
        settings_manager = get_team_settings_manager_instance()
        settings = settings_manager.load_team_settings()
        
        print("✅ Loaded team settings successfully")
        return {
            "success": True,
            "data": settings
        }
    except Exception as e:
        print(f"❌ Error loading team settings: {str(e)}")
        # Return default settings as fallback
        return {
            "success": True,
            "data": {
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
                ]
            }
        }


@router.get("/entry", response_model=EntriesResponse)
async def get_entries(
    week_date: str = Query(..., description="Date in YYYY-MM-DD format"),
    developer_name: str = Query(..., description="Developer name"),
    team_name: str = Query(..., description="Team name")
):
    """Get efficiency entries for a specific week - no authentication required for testing"""
    try:
        data_manager = get_data_manager_instance()
        
        print(f"🔍 Getting entries for developer: {developer_name}, team: {team_name}")
        
        if not developer_name or not team_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Missing developer name or team. Developer: {developer_name}, Team: {team_name}"
            )
        
        # Get week dates
        selected_monday, selected_sunday = get_week_dates(week_date)
        print(f"📅 Week dates: {selected_monday} to {selected_sunday}")
        
        # Load team data
        print(f"📂 Loading team data for: {team_name}")
        df = data_manager.load_team_data(team_name)
        print(f"📊 Loaded {len(df)} total entries")
        
        # Filter for the specific week and developer
        week_start_str = selected_monday.strftime('%Y-%m-%d')
        developer_entries = df[
            (df['Week'] == week_start_str) & 
            (df['Developer_Name'] == developer_name)
        ]
        
        print(f"📋 Found {len(developer_entries)} entries for {developer_name} in week {week_start_str}")
        
        # Convert to list of dictionaries
        entries = developer_entries.to_dict('records')
        
        # Convert pandas data types to Python native types
        for entry in entries:
            for key, value in entry.items():
                if pd.isna(value):
                    entry[key] = None
                elif isinstance(value, (pd.Timestamp, pd.Period)):
                    entry[key] = str(value)
                elif hasattr(value, 'item'):  # numpy types
                    entry[key] = value.item()
        
        return EntriesResponse(
            success=True,
            entries=entries
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Unexpected error getting entries: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error getting entries: {str(e)}"
        ) 