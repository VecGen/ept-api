"""
Admin router for dashboard and management endpoints
Made public for testing purposes - remove auth dependencies
"""

from fastapi import APIRouter, HTTPException, status
import pandas as pd
from datetime import datetime, date, timedelta
from typing import Dict, Any

from models.schemas import TeamSettings, UpdateSettingsRequest, ApiResponse
from core.database import (
    get_data_manager_instance, 
    get_teams_config_manager_instance,
    get_team_settings_manager_instance
)

router = APIRouter()


@router.get("/dashboard")
async def get_admin_dashboard():
    """Get admin dashboard statistics - Public for testing"""
    try:
        teams_config_manager = get_teams_config_manager_instance()
        data_manager = get_data_manager_instance()
        
        teams_config = teams_config_manager.load_teams_config()
        
        if not teams_config:
            return {
                "total_time_saved": 0.0,
                "total_entries": 0,
                "average_efficiency": 0.0,
                "copilot_usage_rate": 0.0,
                "teams_count": 0,
                "developers_count": 0,
                "team_stats": [],
                "developer_leaderboard": [],
                "monthly_trends": [],
                "daily_trends": [],
                "category_breakdown": [],
                "efficiency_trends": []
            }
        
        combined_df = pd.DataFrame()
        team_stats = []
        developer_leaderboard = []
        
        # Process each team with error handling
        for team_name in teams_config.keys():
            try:
                print(f"🔄 Processing team: {team_name}")
                df = data_manager.load_team_data(team_name)
                
                if not df.empty:
                    print(f"📊 Team {team_name} - loaded {len(df)} rows")
                    print(f"📋 Team {team_name} - columns: {list(df.columns)}")
                    
                    # Validate required columns
                    required_columns = ['Efficiency_Gained_Hours', 'Original_Estimate_Hours', 'Copilot_Used', 'Developer_Name']
                    missing_columns = [col for col in required_columns if col not in df.columns]
                    
                    if missing_columns:
                        print(f"⚠️ Team {team_name} - missing columns: {missing_columns}")
                        # Skip this team's data but continue processing others
                        continue
                    
                    # Add team identifier to each row
                    df['Team_Name'] = team_name
                    combined_df = pd.concat([combined_df, df], ignore_index=True)
                    
                    # Calculate team-specific stats with safe conversions
                    try:
                        total_time_saved = float(df['Efficiency_Gained_Hours'].fillna(0).sum())
                        total_entries = len(df)
                        
                        valid_estimates = df[df['Original_Estimate_Hours'].fillna(0) > 0]
                        if not valid_estimates.empty:
                            average_efficiency = float(
                                (valid_estimates['Efficiency_Gained_Hours'].fillna(0).sum() / 
                                 valid_estimates['Original_Estimate_Hours'].fillna(0).sum()) * 100
                            )
                        else:
                            average_efficiency = 0.0
                        
                        # Safe Copilot usage calculation
                        copilot_usage_rate = float(
                            (df['Copilot_Used'].fillna('').str.lower() == 'yes').sum() / len(df) * 100
                        ) if len(df) > 0 else 0.0
                        
                        # Count unique developers
                        developers_count = df['Developer_Name'].fillna('Unknown').nunique()
                        
                        team_stats.append({
                            "team_name": team_name,
                            "total_time_saved": total_time_saved,
                            "total_entries": total_entries,
                            "average_efficiency": average_efficiency,
                            "copilot_usage_rate": copilot_usage_rate,
                            "developers_count": developers_count
                        })
                        
                        # Calculate developer-level stats for leaderboard
                        developer_stats = df.groupby('Developer_Name').agg({
                            'Efficiency_Gained_Hours': 'sum',
                            'Original_Estimate_Hours': 'sum',
                            'Copilot_Used': lambda x: (x.str.lower() == 'yes').sum(),
                            'Story_ID': 'count'  # Total entries
                        }).reset_index()
                        
                        developer_stats.columns = ['developer_name', 'total_time_saved', 'total_estimates', 'copilot_count', 'total_entries']
                        
                        for _, dev_row in developer_stats.iterrows():
                            efficiency_rate = 0.0
                            if dev_row['total_estimates'] > 0:
                                efficiency_rate = (dev_row['total_time_saved'] / dev_row['total_estimates']) * 100
                            
                            copilot_rate = 0.0
                            if dev_row['total_entries'] > 0:
                                copilot_rate = (dev_row['copilot_count'] / dev_row['total_entries']) * 100
                            
                            developer_leaderboard.append({
                                "developer_name": dev_row['developer_name'],
                                "team_name": team_name,
                                "total_time_saved": float(dev_row['total_time_saved']),
                                "total_entries": int(dev_row['total_entries']),
                                "efficiency_rate": efficiency_rate,
                                "copilot_usage_rate": copilot_rate,
                                "avg_hours_per_entry": float(dev_row['total_time_saved'] / dev_row['total_entries']) if dev_row['total_entries'] > 0 else 0.0
                            })
                        
                        print(f"✅ Team {team_name} - stats calculated successfully")
                        
                    except Exception as calc_error:
                        print(f"⚠️ Team {team_name} - stats calculation error: {str(calc_error)}")
                        # Continue with other teams
                        continue
                        
                else:
                    print(f"📊 Team {team_name} - no data found")
                    
            except Exception as team_error:
                print(f"❌ Error processing team {team_name}: {str(team_error)}")
                # Continue with other teams instead of failing completely
                continue
        
        # Sort developer leaderboard by total time saved (descending)
        developer_leaderboard.sort(key=lambda x: x['total_time_saved'], reverse=True)
        
        # Calculate overall statistics
        total_time_saved = 0.0
        total_entries = 0
        average_efficiency = 0.0
        copilot_usage_rate = 0.0
        developers_count = 0
        monthly_trends = []
        daily_trends = []
        category_breakdown = []
        efficiency_trends = []
        
        if team_stats:
            try:
                # Use the combined_df that was already built during team processing
                if not combined_df.empty:
                    print(f"🔍 Combined dataframe debug:")
                    print(f"   Shape: {combined_df.shape}")
                    print(f"   Columns: {list(combined_df.columns)}")
                    print(f"   Developer_Name values: {combined_df['Developer_Name'].unique()}")
                    print(f"   Sample rows: {combined_df.head().to_dict('records')}")
                    
                    # Calculate total metrics
                    total_time_saved = float(combined_df['Efficiency_Gained_Hours'].fillna(0).sum())
                    total_entries = len(combined_df)
                    
                    # Calculate average efficiency
                    original_estimate_total = float(combined_df['Original_Estimate_Hours'].fillna(0).sum())
                    if original_estimate_total > 0:
                        average_efficiency = (total_time_saved / original_estimate_total) * 100
                    
                    # Calculate Copilot usage rate
                    copilot_usage_rate = float(
                        (combined_df['Copilot_Used'].fillna('').str.lower() == 'yes').sum() / len(combined_df) * 100
                    )
                    
                    developers_count = combined_df['Developer_Name'].fillna('Unknown').nunique()
                    
                    # Recalculate developer leaderboard from combined data for accuracy
                    developer_stats = combined_df.groupby('Developer_Name').agg({
                        'Efficiency_Gained_Hours': 'sum',
                        'Original_Estimate_Hours': 'sum',
                        'Copilot_Used': lambda x: (x.str.lower() == 'yes').sum(),
                        'Story_ID': 'count'  # Total entries
                    }).reset_index()
                    
                    developer_stats.columns = ['developer_name', 'total_time_saved', 'total_estimates', 'copilot_count', 'total_entries']
                    
                    # Clear existing leaderboard and rebuild from combined data
                    developer_leaderboard = []
                    
                    for _, dev_row in developer_stats.iterrows():
                        efficiency_rate = 0.0
                        if dev_row['total_estimates'] > 0:
                            efficiency_rate = (dev_row['total_time_saved'] / dev_row['total_estimates']) * 100
                        
                        copilot_rate = 0.0
                        if dev_row['total_entries'] > 0:
                            copilot_rate = (dev_row['copilot_count'] / dev_row['total_entries']) * 100
                        
                        # Find team name for this developer
                        dev_team = combined_df[combined_df['Developer_Name'] == dev_row['developer_name']]['Team_Name'].iloc[0] if not combined_df[combined_df['Developer_Name'] == dev_row['developer_name']].empty else 'Unknown'
                        
                        developer_leaderboard.append({
                            "developer_name": dev_row['developer_name'],
                            "team_name": str(dev_team),
                            "total_time_saved": float(dev_row['total_time_saved']),
                            "total_entries": int(dev_row['total_entries']),
                            "efficiency_rate": efficiency_rate,
                            "copilot_usage_rate": copilot_rate,
                            "avg_hours_per_entry": float(dev_row['total_time_saved'] / dev_row['total_entries']) if dev_row['total_entries'] > 0 else 0.0
                        })
                    
                    print(f"📊 Developer leaderboard: {len(developer_leaderboard)} developers found")
                    
                    # IMPORTANT: Only generate trends if we have REAL timestamp data
                    has_real_timestamps = False
                    
                    # Check for real timestamp data
                    if 'Timestamp' in combined_df.columns or 'Week' in combined_df.columns:
                        try:
                            # Use Timestamp if available, otherwise use Week
                            date_column = 'Timestamp' if 'Timestamp' in combined_df.columns else 'Week'
                            
                            # Convert to datetime and check if we have valid dates
                            combined_df[date_column] = pd.to_datetime(combined_df[date_column], errors='coerce')
                            
                            # Filter out invalid dates
                            valid_dates_df = combined_df.dropna(subset=[date_column])
                            
                            if not valid_dates_df.empty and len(valid_dates_df) > 0:
                                has_real_timestamps = True
                                
                                # Group by month for monthly trends
                                valid_dates_df['month'] = valid_dates_df[date_column].dt.to_period('M')
                                monthly_data = valid_dates_df.groupby('month').agg({
                                    'Efficiency_Gained_Hours': 'sum',
                                    'Original_Estimate_Hours': 'sum',
                                    'Copilot_Used': lambda x: (x.str.lower() == 'yes').sum(),
                                    'Story_ID': 'count'
                                }).reset_index()
                                
                                for _, month_row in monthly_data.iterrows():
                                    month_str = str(month_row['month'])
                                    efficiency_rate = 0.0
                                    if month_row['Original_Estimate_Hours'] > 0:
                                        efficiency_rate = (month_row['Efficiency_Gained_Hours'] / month_row['Original_Estimate_Hours']) * 100
                                    
                                    copilot_rate = 0.0
                                    if month_row['Story_ID'] > 0:
                                        copilot_rate = (month_row['Copilot_Used'] / month_row['Story_ID']) * 100
                                    
                                    monthly_trends.append({
                                        "month": month_str,
                                        "time_saved": round(float(month_row['Efficiency_Gained_Hours']), 1),
                                        "entries": int(month_row['Story_ID']),
                                        "efficiency_rate": round(efficiency_rate, 1),
                                        "copilot_usage": round(copilot_rate, 1)
                                    })
                                
                                # Generate daily trends for last 30 days
                                thirty_days_ago = pd.Timestamp.now() - pd.Timedelta(days=30)
                                recent_df = valid_dates_df[valid_dates_df[date_column] >= thirty_days_ago]
                                
                                if not recent_df.empty:
                                    recent_df['date'] = recent_df[date_column].dt.date
                                    daily_data = recent_df.groupby('date').agg({
                                        'Efficiency_Gained_Hours': 'sum',
                                        'Original_Estimate_Hours': 'sum',
                                        'Copilot_Used': lambda x: (x.str.lower() == 'yes').sum(),
                                        'Story_ID': 'count'
                                    }).reset_index()
                                    
                                    for _, day_row in daily_data.iterrows():
                                        efficiency_rate = 0.0
                                        if day_row['Original_Estimate_Hours'] > 0:
                                            efficiency_rate = (day_row['Efficiency_Gained_Hours'] / day_row['Original_Estimate_Hours']) * 100
                                        
                                        copilot_rate = 0.0
                                        if day_row['Story_ID'] > 0:
                                            copilot_rate = (day_row['Copilot_Used'] / day_row['Story_ID']) * 100
                                        
                                        daily_trends.append({
                                            "date": day_row['date'].strftime("%Y-%m-%d"),
                                            "time_saved": round(float(day_row['Efficiency_Gained_Hours']), 1),
                                            "entries": int(day_row['Story_ID']),
                                            "efficiency_rate": round(efficiency_rate, 1),
                                            "copilot_usage": round(copilot_rate, 1)
                                        })
                        except Exception as date_error:
                            print(f"⚠️ Error processing date-based trends: {str(date_error)}")
                            has_real_timestamps = False
                    
                    # Safe category breakdown - only if we have real data
                    if 'Category' in combined_df.columns and total_entries > 0:
                        try:
                            category_data = combined_df.groupby('Category').agg({
                                'Efficiency_Gained_Hours': 'sum',
                                'Original_Estimate_Hours': 'sum',
                                'Story_ID': 'count'
                            }).reset_index()
                            
                            for _, row in category_data.iterrows():
                                category_breakdown.append({
                                    "category": str(row['Category']),
                                    "time_saved": float(row['Efficiency_Gained_Hours']),
                                    "entries": int(row['Story_ID']),
                                    "percentage": float(row['Efficiency_Gained_Hours'] / total_time_saved * 100) if total_time_saved > 0 else 0
                                })
                        except Exception as cat_error:
                            print(f"⚠️ Category breakdown error: {str(cat_error)}")
                    
                    # Efficiency trends by team - only if we have real data
                    for team_stat in team_stats:
                        if team_stat.get("total_time_saved", 0) > 0:
                            efficiency_trends.append({
                                "team": team_stat["team_name"],
                                "efficiency_rate": team_stat["average_efficiency"],
                                "time_saved": team_stat["total_time_saved"],
                                "copilot_usage": team_stat["copilot_usage_rate"]
                            })
                    
                    print(f"✅ Dashboard calculations completed - Real data: {has_real_timestamps}, Entries: {total_entries}")
                    
                else:
                    print("⚠️ No valid team data found for calculations")
                    
            except Exception as calc_error:
                print(f"❌ Error in dashboard calculations: {str(calc_error)}")
                # Return basic stats even if trend calculations fail
                total_time_saved = 0.0
                total_entries = 0
                average_efficiency = 0.0
                copilot_usage_rate = 0.0
                developers_count = 0
        
        else:
            print("⚠️ No team stats available")
            total_time_saved = 0.0
            total_entries = 0
            average_efficiency = 0.0
            copilot_usage_rate = 0.0
            developers_count = 0
            
        # Sort trends chronologically if we have any
        if monthly_trends:
            monthly_trends.sort(key=lambda x: x['month'])
        if daily_trends:
            daily_trends.sort(key=lambda x: x['date'])
        
        # Sort developer leaderboard by time saved (descending)
        if developer_leaderboard:
            developer_leaderboard.sort(key=lambda x: x['total_time_saved'], reverse=True)
        
        print(f"🔍 Final debug before return:")
        print(f"   Developer leaderboard length: {len(developer_leaderboard)}")
        print(f"   Developer leaderboard content: {developer_leaderboard}")
        print(f"   Total entries: {total_entries}")
        print(f"   Team stats: {len(team_stats)}")
        
        # Return the response with proper data structure
        return {
            "success": True,
            "message": "Dashboard data retrieved successfully",
            "data": {
                "total_time_saved": round(total_time_saved, 2),
                "total_entries": total_entries,
                "teams_count": len(team_stats),
                "developers_count": developers_count,
                "average_efficiency": round(average_efficiency, 2),
                "copilot_usage_rate": round(copilot_usage_rate, 2),
                "team_stats": team_stats,
                "monthly_trends": monthly_trends,  # Empty if no real data
                "daily_trends": daily_trends,      # Empty if no real data
                "category_breakdown": category_breakdown,
                "efficiency_trends": efficiency_trends,
                "developer_leaderboard": developer_leaderboard,
                "data_quality": {
                    "has_real_timestamps": bool(monthly_trends or daily_trends),
                    "has_efficiency_data": total_entries > 0,
                    "data_completeness": "complete" if total_entries > 10 else "limited" if total_entries > 0 else "none"
                }
            }
        }
        
    except Exception as e:
        print(f"❌ Critical error in admin dashboard: {str(e)}")
        print(f"   Exception type: {type(e).__name__}")
        # Return basic empty response instead of 500 error
        return {
            "total_time_saved": 0.0,
            "total_entries": 0,
            "average_efficiency": 0.0,
            "copilot_usage_rate": 0.0,
            "teams_count": 0,
            "developers_count": 0,
            "team_stats": [],
            "developer_leaderboard": [],
            "monthly_trends": [],
            "daily_trends": [],
            "category_breakdown": [],
            "efficiency_trends": []
        }


@router.get("/settings", response_model=TeamSettings)
async def get_team_settings():
    """Get team settings - Public for testing"""
    settings_manager = get_team_settings_manager_instance()
    settings = settings_manager.load_team_settings()
    
    return TeamSettings(**settings)


@router.put("/settings", response_model=ApiResponse)
async def update_team_settings(settings_data: UpdateSettingsRequest):
    """Update team settings - Public for testing"""
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
async def get_team_data(team_name: str):
    """Get data for a specific team - Public for testing"""
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


@router.get("/debug/s3", response_model=ApiResponse)
async def debug_s3_connection():
    """Debug S3 connection and list bucket contents - Public for testing"""
    try:
        data_manager = get_data_manager_instance()
        
        # Test S3 connection
        data_manager.s3_client.head_bucket(Bucket=data_manager.s3_bucket)
        
        # List all objects in the teams/ folder
        response = data_manager.s3_client.list_objects_v2(
            Bucket=data_manager.s3_bucket,
            Prefix='teams/'
        )
        
        files = []
        if 'Contents' in response:
            for obj in response['Contents']:
                files.append({
                    "key": obj['Key'],
                    "size": obj['Size'],
                    "last_modified": obj['LastModified'].isoformat()
                })
        
        return {
            "success": True,
            "message": "S3 connection successful",
            "data": {
                "bucket": data_manager.s3_bucket,
                "total_files": len(files),
                "team_files": files
            }
        }
    except Exception as e:
        print(f"❌ S3 Debug Error: {str(e)}")
        return {
            "success": False,
            "message": f"S3 connection failed: {str(e)}",
            "data": None
        } 