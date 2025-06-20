"""
Simple Teams router with S3 backend and no authentication for testing
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
    """Get all teams from S3 - no authentication required for testing"""
    
    print(f"🔍 list_all_teams called (no auth) - loading from S3")
    
    try:
        teams_config_manager = get_teams_config_manager_instance()
        teams_config = teams_config_manager.load_teams_config()
        
        teams = []
        for team_name, team_data in teams_config.items():
            developers = []
            
            # Handle both old and new data structures
            if isinstance(team_data, list):
                for dev in team_data:
                    if isinstance(dev, dict):
                        developers.append(Developer(
                            name=dev.get('name', ''),
                            email=dev.get('email', '')
                        ))
                    else:
                        # Handle old format where it's just a string
                        developers.append(Developer(name=str(dev), email=''))
            
            teams.append(Team(
                name=team_name,
                description=f"Team {team_name}",  # Default description
                developers=developers
            ))
        
        print(f"✅ Loaded {len(teams)} teams from S3")
        return teams
        
    except Exception as e:
        print(f"❌ Failed to load teams from S3: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load teams from S3: {str(e)}"
        )



@router.post("/create", response_model=ApiResponse)
async def create_new_team(team_data: CreateTeamRequest):
    """Create a new team in S3 - no authentication required for testing"""
    
    print(f"🔍 create_new_team called: {team_data.team_name}")
    
    try:
        teams_config_manager = get_teams_config_manager_instance()
        teams_config = teams_config_manager.load_teams_config()
        
        if team_data.team_name in teams_config:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Team '{team_data.team_name}' already exists"
            )
        
        teams_config[team_data.team_name] = []
        
        if teams_config_manager.save_teams_config(teams_config):
            print(f"✅ Team '{team_data.team_name}' created successfully in S3")
            return ApiResponse(
                success=True,
                message=f"Team '{team_data.team_name}' created successfully"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to save team configuration to S3"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Failed to create team: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create team: {str(e)}"
        )


@router.post("/add-developer", response_model=ApiResponse)
async def add_developer_to_team(
    team_name: str,
    developer_data: AddDeveloperRequest
):
    """Add a developer to a team in S3 - no authentication required for testing"""
    
    print(f"🔍 add_developer_to_team called: {developer_data.dev_name} to {team_name}")
    
    try:
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
            print(f"✅ Developer '{developer_data.dev_name}' added to '{team_name}' in S3")
            return ApiResponse(
                success=True,
                message=f"{developer_data.dev_name} added to {team_name}",
                data={"access_link": access_link}
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to save team configuration to S3"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Failed to add developer: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add developer: {str(e)}"
        )


@router.delete("/remove-developer")
async def remove_developer_from_team(
    team_name: str,
    developer_name: str
):
    """Remove a developer from a team in S3 - no authentication required for testing"""
    
    print(f"🔍 remove_developer_from_team called: {developer_name} from {team_name}")
    
    try:
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
            print(f"✅ Developer '{developer_name}' removed from '{team_name}' in S3")
            return ApiResponse(
                success=True,
                message=f"{developer_name} removed from {team_name}"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to save team configuration to S3"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Failed to remove developer: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to remove developer: {str(e)}"
        )


@router.delete("/delete-team")
async def delete_entire_team(team_name: str):
    """Delete a team from S3 - no authentication required for testing"""
    
    print(f"🔍 delete_entire_team called: {team_name}")
    
    try:
        teams_config_manager = get_teams_config_manager_instance()
        teams_config = teams_config_manager.load_teams_config()
        
        if team_name not in teams_config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Team '{team_name}' not found"
            )
        
        del teams_config[team_name]
        
        if teams_config_manager.save_teams_config(teams_config):
            print(f"✅ Team '{team_name}' deleted successfully from S3")
            return ApiResponse(
                success=True,
                message=f"Team '{team_name}' deleted successfully"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to save team configuration to S3"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Failed to delete team: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete team: {str(e)}"
        )


@router.get("/get-team", response_model=Team)
async def get_team_details(team_name: str):
    """Get a specific team from S3 - no authentication required for testing"""
    
    print(f"🔍 get_team_details called: {team_name}")
    
    try:
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
                    developers.append(Developer(
                        name=dev.get('name', ''),
                        email=dev.get('email', '')
                    ))
                else:
                    developers.append(Developer(name=str(dev), email=''))
        
        print(f"✅ Team '{team_name}' retrieved from S3 with {len(developers)} developers")
        return Team(name=team_name, developers=developers)
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Failed to get team details: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get team details: {str(e)}"
        ) 