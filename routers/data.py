"""
Data management router for export and data operations
"""

from fastapi import APIRouter, HTTPException, status, Depends, Query
from fastapi.responses import StreamingResponse
from typing import List, Optional, Dict, Any
import pandas as pd
import io
from datetime import datetime, timedelta

from models.schemas import ExportRequest, ApiResponse
from core.auth import verify_admin_token
from core.database import get_data_manager_instance, get_teams_config_manager_instance

router = APIRouter()


@router.post("/export")
async def export_data(
    export_request: ExportRequest,
    token_data: dict = Depends(verify_admin_token)
):
    """Export team data as Excel file"""
    data_manager = get_data_manager_instance()
    teams_config_manager = get_teams_config_manager_instance()
    
    teams_config = teams_config_manager.load_teams_config()
    
    # Validate team names
    invalid_teams = [team for team in export_request.teams if team not in teams_config]
    if invalid_teams:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid teams: {', '.join(invalid_teams)}"
        )
    
    if export_request.export_type == "combined":
        # Create combined export
        combined_df = pd.DataFrame()
        
        for team_name in export_request.teams:
            df = data_manager.load_team_data(team_name)
            if not df.empty:
                combined_df = pd.concat([combined_df, df], ignore_index=True)
        
        if combined_df.empty:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No data found for selected teams"
            )
        
        # Create Excel file in memory
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            combined_df.to_excel(writer, sheet_name='Combined_Data', index=False)
        
        output.seek(0)
        
        return StreamingResponse(
            io.BytesIO(output.read()),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=combined_efficiency_data.xlsx"}
        )
    
    else:
        # Create individual team exports in a zip file
        import zipfile
        
        zip_buffer = io.BytesIO()
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for team_name in export_request.teams:
                df = data_manager.load_team_data(team_name)
                
                if not df.empty:
                    # Create Excel file for this team
                    excel_buffer = io.BytesIO()
                    with pd.ExcelWriter(excel_buffer, engine='xlsxwriter') as writer:
                        df.to_excel(writer, sheet_name=f'{team_name}_Data', index=False)
                    
                    excel_buffer.seek(0)
                    zip_file.writestr(f"{team_name}_efficiency_data.xlsx", excel_buffer.read())
        
        zip_buffer.seek(0)
        
        return StreamingResponse(
            io.BytesIO(zip_buffer.read()),
            media_type="application/zip",
            headers={"Content-Disposition": "attachment; filename=team_efficiency_data.zip"}
        )


@router.delete("/teams/{team_name}/entries/{entry_id}", response_model=ApiResponse)
async def delete_entry(
    team_name: str,
    entry_id: int,
    token_data: dict = Depends(verify_admin_token)
):
    """Delete a specific entry"""
    data_manager = get_data_manager_instance()
    teams_config_manager = get_teams_config_manager_instance()
    
    teams_config = teams_config_manager.load_teams_config()
    
    if team_name not in teams_config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Team '{team_name}' not found"
        )
    
    df = data_manager.load_team_data(team_name)
    
    if df.empty or entry_id >= len(df):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Entry not found"
        )
    
    # Remove the entry
    df = df.drop(df.index[entry_id]).reset_index(drop=True)
    
    if data_manager.save_team_data(team_name, df):
        return ApiResponse(
            success=True,
            message="Entry deleted successfully"
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete entry"
        )


@router.get("/teams/{team_name}/entries")
async def get_team_entries(
    team_name: str,
    token_data: dict = Depends(verify_admin_token)
):
    """Get all entries for a team with pagination"""
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
                "total": 0
            }
        }
    
    # Convert to records and handle data types
    entries = df.to_dict('records')
    
    for entry in entries:
        for key, value in entry.items():
            if pd.isna(value):
                entry[key] = None
            elif isinstance(value, (pd.Timestamp, pd.Period)):
                entry[key] = str(value)
            elif hasattr(value, 'item'):
                entry[key] = value.item()
    
    return {
        "success": True,
        "data": {
            "entries": entries,
            "total": len(entries)
        }
    }


@router.get("/analytics/team/{team_name}")
async def get_team_analytics(
    team_name: str,
    start_date: Optional[str] = Query(None, description="Start date in YYYY-MM-DD format"),
    end_date: Optional[str] = Query(None, description="End date in YYYY-MM-DD format"),
    token_data: dict = Depends(verify_admin_token)
):
    """Get analytics data for a specific team"""
    data_manager = get_data_manager_instance()
    teams_config_manager = get_teams_config_manager_instance()
    
    teams_config = teams_config_manager.load_teams_config()
    
    if team_name not in teams_config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Team '{team_name}' not found"
        )
    
    # Load team data
    df = data_manager.load_team_data(team_name)
    
    if df.empty:
        return {
            "success": True,
            "data": {
                "team_name": team_name,
                "total_time_saved": 0.0,
                "total_entries": 0,
                "average_efficiency": 0.0,
                "copilot_usage_rate": 0.0,
                "developers_count": 0,
                "monthly_trends": [],
                "category_breakdown": [],
                "developer_stats": []
            }
        }
    
    # Filter by date range if provided
    if start_date or end_date:
        try:
            df['Week'] = pd.to_datetime(df['Week'])
            if start_date:
                start_dt = datetime.strptime(start_date, '%Y-%m-%d')
                df = df[df['Week'] >= start_dt]
            if end_date:
                end_dt = datetime.strptime(end_date, '%Y-%m-%d')
                df = df[df['Week'] <= end_dt]
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid date format: {str(e)}"
            )
    
    # Calculate basic stats
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
    copilot_yes = len(df[df['Copilot_Used'].str.upper() == 'YES'])
    copilot_usage_rate = (copilot_yes / total_entries * 100) if total_entries > 0 else 0.0
    
    # Developer count
    developers_count = df['Developer_Name'].nunique()
    
    # Monthly trends
    df_copy = df.copy()
    df_copy['Month'] = pd.to_datetime(df_copy['Week']).dt.to_period('M')
    monthly_stats = df_copy.groupby('Month').agg({
        'Efficiency_Gained_Hours': 'sum',
        'Original_Estimate_Hours': 'sum',
        'Developer_Name': 'count'
    }).reset_index()
    
    monthly_trends = []
    for _, row in monthly_stats.iterrows():
        efficiency_rate = (row['Efficiency_Gained_Hours'] / row['Original_Estimate_Hours'] * 100) if row['Original_Estimate_Hours'] > 0 else 0
        monthly_trends.append({
            "month": str(row['Month']),
            "time_saved": float(row['Efficiency_Gained_Hours']),
            "entries": int(row['Developer_Name']),
            "efficiency_rate": float(efficiency_rate)
        })
    
    # Category breakdown
    category_stats = df.groupby('Category').agg({
        'Efficiency_Gained_Hours': 'sum',
        'Developer_Name': 'count'
    }).reset_index()
    
    category_breakdown = []
    for _, row in category_stats.iterrows():
        category_breakdown.append({
            "category": row['Category'],
            "time_saved": float(row['Efficiency_Gained_Hours']),
            "entries": int(row['Developer_Name'])
        })
    
    # Developer stats
    developer_stats = df.groupby('Developer_Name').agg({
        'Efficiency_Gained_Hours': 'sum',
        'Original_Estimate_Hours': 'sum',
        'Developer_Name': 'count'
    }).reset_index()
    developer_stats.columns = ['Developer_Name', 'Efficiency_Gained_Hours', 'Original_Estimate_Hours', 'Entries']
    
    developer_list = []
    for _, row in developer_stats.iterrows():
        efficiency_rate = (row['Efficiency_Gained_Hours'] / row['Original_Estimate_Hours'] * 100) if row['Original_Estimate_Hours'] > 0 else 0
        developer_list.append({
            "developer_name": row['Developer_Name'],
            "time_saved": float(row['Efficiency_Gained_Hours']),
            "entries": int(row['Entries']),
            "efficiency_rate": float(efficiency_rate)
        })
    
    return {
        "success": True,
        "data": {
            "team_name": team_name,
            "total_time_saved": total_time_saved,
            "total_entries": total_entries,
            "average_efficiency": average_efficiency,
            "copilot_usage_rate": copilot_usage_rate,
            "developers_count": developers_count,
            "monthly_trends": monthly_trends,
            "category_breakdown": category_breakdown,
            "developer_stats": developer_list
        }
    }


@router.get("/analytics/overall")
async def get_overall_analytics(
    start_date: Optional[str] = Query(None, description="Start date in YYYY-MM-DD format"),
    end_date: Optional[str] = Query(None, description="End date in YYYY-MM-DD format"),
    token_data: dict = Depends(verify_admin_token)
):
    """Get overall analytics data across all teams"""
    data_manager = get_data_manager_instance()
    teams_config_manager = get_teams_config_manager_instance()
    
    teams_config = teams_config_manager.load_teams_config()
    
    # Combine data from all teams
    combined_df = pd.DataFrame()
    
    for team_name in teams_config.keys():
        df = data_manager.load_team_data(team_name)
        if not df.empty:
            combined_df = pd.concat([combined_df, df], ignore_index=True)
    
    if combined_df.empty:
        return {
            "success": True,
            "data": {
                "total_time_saved": 0.0,
                "total_entries": 0,
                "average_efficiency": 0.0,
                "copilot_usage_rate": 0.0,
                "teams_count": len(teams_config),
                "developers_count": 0,
                "team_breakdown": [],
                "monthly_trends": []
            }
        }
    
    # Filter by date range if provided
    if start_date or end_date:
        try:
            combined_df['Week'] = pd.to_datetime(combined_df['Week'])
            if start_date:
                start_dt = datetime.strptime(start_date, '%Y-%m-%d')
                combined_df = combined_df[combined_df['Week'] >= start_dt]
            if end_date:
                end_dt = datetime.strptime(end_date, '%Y-%m-%d')
                combined_df = combined_df[combined_df['Week'] <= end_dt]
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid date format: {str(e)}"
            )
    
    # Calculate overall stats
    total_time_saved = float(combined_df['Efficiency_Gained_Hours'].sum())
    total_entries = len(combined_df)
    
    # Calculate average efficiency
    valid_estimates = combined_df[combined_df['Original_Estimate_Hours'] > 0]
    if not valid_estimates.empty:
        average_efficiency = float(
            (valid_estimates['Efficiency_Gained_Hours'].sum() / 
             valid_estimates['Original_Estimate_Hours'].sum()) * 100
        )
    else:
        average_efficiency = 0.0
    
    # Calculate Copilot usage rate
    copilot_yes = len(combined_df[combined_df['Copilot_Used'].str.upper() == 'YES'])
    copilot_usage_rate = (copilot_yes / total_entries * 100) if total_entries > 0 else 0.0
    
    # Teams and developers count
    teams_count = len(teams_config)
    developers_count = combined_df['Developer_Name'].nunique()
    
    # Team breakdown
    team_stats = combined_df.groupby('Team_Name').agg({
        'Efficiency_Gained_Hours': 'sum',
        'Original_Estimate_Hours': 'sum',
        'Developer_Name': ['count', 'nunique']
    }).reset_index()
    
    team_breakdown = []
    for _, row in team_stats.iterrows():
        efficiency_rate = (row[('Efficiency_Gained_Hours', 'sum')] / row[('Original_Estimate_Hours', 'sum')] * 100) if row[('Original_Estimate_Hours', 'sum')] > 0 else 0
        team_breakdown.append({
            "team_name": row['Team_Name'],
            "time_saved": float(row[('Efficiency_Gained_Hours', 'sum')]),
            "entries": int(row[('Developer_Name', 'count')]),
            "developers_count": int(row[('Developer_Name', 'nunique')]),
            "efficiency_rate": float(efficiency_rate)
        })
    
    # Monthly trends
    df_copy = combined_df.copy()
    df_copy['Month'] = pd.to_datetime(df_copy['Week']).dt.to_period('M')
    monthly_stats = df_copy.groupby('Month').agg({
        'Efficiency_Gained_Hours': 'sum',
        'Original_Estimate_Hours': 'sum',
        'Developer_Name': 'count'
    }).reset_index()
    
    monthly_trends = []
    for _, row in monthly_stats.iterrows():
        efficiency_rate = (row['Efficiency_Gained_Hours'] / row['Original_Estimate_Hours'] * 100) if row['Original_Estimate_Hours'] > 0 else 0
        monthly_trends.append({
            "month": str(row['Month']),
            "time_saved": float(row['Efficiency_Gained_Hours']),
            "entries": int(row['Developer_Name']),
            "efficiency_rate": float(efficiency_rate)
        })
    
    return {
        "success": True,
        "data": {
            "total_time_saved": total_time_saved,
            "total_entries": total_entries,
            "average_efficiency": average_efficiency,
            "copilot_usage_rate": copilot_usage_rate,
            "teams_count": teams_count,
            "developers_count": developers_count,
            "team_breakdown": team_breakdown,
            "monthly_trends": monthly_trends
        }
    }


@router.get("/export/team/{team_name}")
async def export_team_data(
    team_name: str,
    format: str = Query("excel", description="Export format: excel or csv"),
    token_data: dict = Depends(verify_admin_token)
):
    """Export data for a specific team"""
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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No data found for team '{team_name}'"
        )
    
    if format.lower() == "excel":
        # Create Excel file in memory
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, sheet_name=f'{team_name}_Data', index=False)
        
        output.seek(0)
        
        return StreamingResponse(
            io.BytesIO(output.read()),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={team_name}_efficiency_data.xlsx"}
        )
    
    elif format.lower() == "csv":
        # Create CSV file in memory
        output = io.StringIO()
        df.to_csv(output, index=False)
        csv_content = output.getvalue()
        
        return StreamingResponse(
            io.StringIO(csv_content),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={team_name}_efficiency_data.csv"}
        )
    
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid format. Supported formats: excel, csv"
        ) 