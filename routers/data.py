"""
Data management router for export and data operations
"""

from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.responses import StreamingResponse
from typing import List
import pandas as pd
import io

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
    
    team_file = get_team_excel_file(team_name)
    df = data_manager.load_excel_data(team_file)
    
    if df.empty or entry_id >= len(df):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Entry not found"
        )
    
    # Remove the entry
    df = df.drop(df.index[entry_id]).reset_index(drop=True)
    
    if data_manager.save_excel_data(df, team_file):
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
    
    team_file = get_team_excel_file(team_name)
    df = data_manager.load_excel_data(team_file)
    
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