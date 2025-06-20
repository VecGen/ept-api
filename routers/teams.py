"""
Teams router for managing teams and developers
"""

from fastapi import APIRouter, HTTPException, status, Depends
from typing import List, Dict
import os

from models.schemas import (
    Team, CreateTeamRequest, AddDeveloperRequest, Developer, ApiResponse
)
from core.auth import verify_admin_token, verify_engineer_token
from core.database import get_teams_config_manager_instance

router = APIRouter()


def generate_engineer_link(developer_name: str, team_name: str) -> str:
    """Generate an access link for an engineer"""
    # Get frontend URL from environment variable or use default
    frontend_url = os.getenv("FRONTEND_URL", "https://bynixti6xn.us-east-1.awsapprunner.com")
    return f"{frontend_url}/engineer?team={team_name}&dev={developer_name}"


@router.get("/test", response_model=List[Team])
async def get_teams_test():
    """Test endpoint without authentication to verify hardcoded data works"""
    print("🧪 Test endpoint called - returning hardcoded teams data...")
    
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
    
    print(f"✅ Test endpoint returning {len(hardcoded_teams)} hardcoded teams")
    return hardcoded_teams


@router.get("/", response_model=List[Team])
async def get_teams(token_data: dict = Depends(verify_engineer_token)):
    """Get all teams"""
    
    # 🚨 TEMPORARY: Bypassing S3 logic to test authentication
    # Comment out S3-dependent code and return hardcoded data
    
    """
    # Original S3-dependent code (commented out for testing)
    teams_config_manager = get_teams_config_manager_instance()
    
    try:
        teams_config = teams_config_manager.load_teams_config()
    except Exception as e:
        print(f"⚠️ Error loading teams config: {str(e)}")
        # If loading fails, create a default empty config
        teams_config = {}
        try:
            teams_config_manager.save_teams_config(teams_config)
            print("✅ Created default empty teams config")
        except Exception as save_error:
            print(f"❌ Failed to create default config: {str(save_error)}")
            # Still return empty list rather than failing
    
    teams = []
    for team_name, team_data in teams_config.items():
        developers = []
        
        # Handle both old and new data structures
        if isinstance(team_data, list):
            for dev in team_data:
                if isinstance(dev, dict):
                    developers.append(Developer(**dev))
                else:
                    developers.append(Developer(name=dev))
        
        teams.append(Team(name=team_name, developers=developers))
    
    return teams
    """
    
    # 🔥 HARDCODED RESPONSE FOR TESTING (remove this when S3 is working)
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


@router.post("/", response_model=ApiResponse)
async def create_team(
    team_data: CreateTeamRequest,
    token_data: dict = Depends(verify_admin_token)
):
    """Create a new team"""
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


@router.post("/{team_name}/developers", response_model=ApiResponse)
async def add_developer(
    team_name: str,
    developer_data: AddDeveloperRequest,
    token_data: dict = Depends(verify_admin_token)
):
    """Add a developer to a team"""
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


@router.delete("/{team_name}/developers/{developer_name}", response_model=ApiResponse)
async def remove_developer(
    team_name: str,
    developer_name: str,
    token_data: dict = Depends(verify_admin_token)
):
    """Remove a developer from a team"""
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


@router.delete("/{team_name}", response_model=ApiResponse)
async def delete_team(
    team_name: str,
    token_data: dict = Depends(verify_admin_token)
):
    """Delete a team"""
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


@router.get("/{team_name}", response_model=Team)
async def get_team(
    team_name: str,
    token_data: dict = Depends(verify_engineer_token)
):
    """Get a specific team"""
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