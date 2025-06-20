"""
Simple Teams router with distinct route names for better CORS handling
"""

from fastapi import APIRouter, HTTPException, status, Depends, Request
from typing import List, Dict, Optional
import os

from models.schemas import (
    Team, CreateTeamRequest, AddDeveloperRequest, Developer, ApiResponse
)
from core.auth import verify_admin_token, verify_engineer_token
from core.database import get_teams_config_manager_instance

router = APIRouter()


def generate_engineer_link(developer_name: str, team_name: str) -> str:
    """Generate an access link for an engineer"""
    frontend_url = os.getenv("FRONTEND_URL", "https://bynixti6xn.us-east-1.awsapprunner.com")
    return f"{frontend_url}/engineer?team={team_name}&dev={developer_name}"


@router.get("/list", response_model=List[Team])
async def list_all_teams(request: Request, token_data: dict = Depends(verify_engineer_token)):
    """Get all teams - renamed from GET / to avoid CORS issues"""
    
    print(f"🔍 list_all_teams called with token_data: {token_data}")
    print(f"🔍 Request method: {request.method}")
    print(f"🔍 Request headers: {dict(request.headers)}")
    
    # Handle OPTIONS requests gracefully
    if request.method == "OPTIONS":
        print("🔧 OPTIONS request detected in list_all_teams")
        return []
    
    # 🚨 TEMPORARY: Return hardcoded data for testing
    print("🧪 Returning hardcoded teams data for testing...")
    
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
async def create_new_team(
    team_data: CreateTeamRequest,
    token_data: dict = Depends(verify_admin_token)
):
    """Create a new team - renamed from POST / for clarity"""
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
    developer_data: AddDeveloperRequest,
    token_data: dict = Depends(verify_admin_token)
):
    """Add a developer to a team - renamed for clarity"""
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
    developer_name: str,
    token_data: dict = Depends(verify_admin_token)
):
    """Remove a developer from a team - renamed for clarity"""
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
async def delete_entire_team(
    team_name: str,
    token_data: dict = Depends(verify_admin_token)
):
    """Delete a team - renamed for clarity"""
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
async def get_team_details(
    team_name: str,
    token_data: dict = Depends(verify_engineer_token)
):
    """Get a specific team - renamed for clarity"""
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