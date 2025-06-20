"""
Simple Teams router with no authentication for testing
"""

from fastapi import APIRouter, HTTPException, status, Request
from typing import List, Dict, Optional
import os

from models.schemas import (
    Team, CreateTeamRequest, AddDeveloperRequest, Developer, ApiResponse
)
from core.database import get_teams_config_manager_instance

router = APIRouter()


def generate_engineer_link(developer_name: str, team_name: str) -> str:
    """Generate an access link for an engineer"""
    frontend_url = os.getenv("FRONTEND_URL", "https://bynixti6xn.us-east-1.awsapprunner.com")
    return f"{frontend_url}/engineer?team={team_name}&dev={developer_name}"


@router.get("/list", response_model=List[Team])
async def list_all_teams():
    """Get all teams - no authentication required for testing"""
    
    print(f"🔍 list_all_teams called (no auth)")
    
    # Return hardcoded data for testing
    print("🧪 Returning hardcoded teams data...")
    
    hardcoded_teams = [
        Team(
            name="Frontend Team",
            description="Responsible for UI/UX development",
            developers=[
                Developer(name="Alice Johnson", email="alice@company.com"),
                Developer(name="Bob Smith", email="bob@company.com")
            ]
        ),
        Team(
            name="Backend Team", 
            description="API and database development",
            developers=[
                Developer(name="Charlie Brown", email="charlie@company.com"),
                Developer(name="Diana Prince", email="diana@company.com")
            ]
        ),
        Team(
            name="DevOps Team",
            description="Infrastructure and deployment",
            developers=[
                Developer(name="Eve Wilson", email="eve@company.com")
            ]
        )
    ]
    
    print(f"✅ Returning {len(hardcoded_teams)} hardcoded teams")
    return hardcoded_teams


@router.get("/test-public", response_model=List[Team])
async def test_public_endpoint():
    """Test endpoint without authentication to verify CORS works"""
    print("🧪 Public test endpoint called - returning hardcoded teams data...")
    
    hardcoded_teams = [
        Team(
            name="Frontend Team",
            description="Responsible for UI/UX development",
            developers=[
                Developer(name="Alice Johnson", email="alice@company.com"),
                Developer(name="Bob Smith", email="bob@company.com")
            ]
        ),
        Team(
            name="Backend Team", 
            description="API and database development",
            developers=[
                Developer(name="Charlie Brown", email="charlie@company.com"),
                Developer(name="Diana Prince", email="diana@company.com")
            ]
        )
    ]
    
    print(f"✅ Public test endpoint returning {len(hardcoded_teams)} hardcoded teams")
    return hardcoded_teams


@router.post("/create", response_model=ApiResponse)
async def create_new_team(team_data: CreateTeamRequest):
    """Create a new team - no authentication required for testing"""
    teams_config_manager = get_teams_config_manager_instance()
    teams_config = teams_config_manager.load_teams_config()
    
    if team_data.team_name in teams_config:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Team '{team_data.team_name}' already exists"
        )
    
    teams_config[team_data.team_name] = []
    
    if teams_config_manager.save_teams_config(teams_config):
        return ApiResponse(
            success=True,
            message=f"Team '{team_data.team_name}' created successfully"
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save team configuration"
        )


@router.post("/add-developer", response_model=ApiResponse)
async def add_developer_to_team(
    team_name: str,
    developer_data: AddDeveloperRequest
):
    """Add a developer to a team - no authentication required for testing"""
    teams_config_manager = get_teams_config_manager_instance()
    teams_config = teams_config_manager.load_teams_config()
    
    if team_name not in teams_config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Team '{team_name}' not found"
        )
    
    # Generate access link
    access_link = generate_engineer_link(developer_data.dev_name, team_name)
    
    developer = {
        'name': developer_data.dev_name,
        'email': developer_data.dev_email,
        'link': access_link
    }
    
    teams_config[team_name].append(developer)
    
    if teams_config_manager.save_teams_config(teams_config):
        return ApiResponse(
            success=True,
            message=f"{developer_data.dev_name} added to {team_name}",
            data={"access_link": access_link}
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save team configuration"
        )


@router.delete("/remove-developer")
async def remove_developer_from_team(
    team_name: str,
    developer_name: str
):
    """Remove a developer from a team - no authentication required for testing"""
    teams_config_manager = get_teams_config_manager_instance()
    teams_config = teams_config_manager.load_teams_config()
    
    if team_name not in teams_config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Team '{team_name}' not found"
        )
    
    # Find and remove the developer
    team_data = teams_config[team_name]
    for i, dev in enumerate(team_data):
        dev_name = dev['name'] if isinstance(dev, dict) else dev
        if dev_name == developer_name:
            team_data.pop(i)
            break
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Developer '{developer_name}' not found in team '{team_name}'"
        )
    
    if teams_config_manager.save_teams_config(teams_config):
        return ApiResponse(
            success=True,
            message=f"{developer_name} removed from {team_name}"
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save team configuration"
        )


@router.delete("/delete-team")
async def delete_entire_team(team_name: str):
    """Delete a team - no authentication required for testing"""
    teams_config_manager = get_teams_config_manager_instance()
    teams_config = teams_config_manager.load_teams_config()
    
    if team_name not in teams_config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Team '{team_name}' not found"
        )
    
    del teams_config[team_name]
    
    if teams_config_manager.save_teams_config(teams_config):
        return ApiResponse(
            success=True,
            message=f"Team '{team_name}' deleted successfully"
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save team configuration"
        )


@router.get("/get-team", response_model=Team)
async def get_team_details(team_name: str):
    """Get a specific team - no authentication required for testing"""
    teams_config_manager = get_teams_config_manager_instance()
    teams_config = teams_config_manager.load_teams_config()
    
    if team_name not in teams_config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Team '{team_name}' not found"
        )
    
    team_data = teams_config[team_name]
    developers = []
    
    # Handle both old and new data structures
    if isinstance(team_data, list):
        for dev in team_data:
            if isinstance(dev, dict):
                developers.append(Developer(**dev))
            else:
                developers.append(Developer(name=dev))
    
    return Team(name=team_name, developers=developers)


@router.get("/debug-token")
async def debug_token_endpoint(request: Request):
    """Debug endpoint to see what token is being sent"""
    headers = dict(request.headers)
    auth_header = headers.get('authorization', 'No Authorization header')
    
    print(f"🔍 Debug token endpoint called")
    print(f"🔍 Authorization header: {auth_header}")
    print(f"🔍 All headers: {headers}")
    
    return {
        "authorization_header": auth_header,
        "all_headers": headers,
        "message": "Check the console logs for details"
    } 