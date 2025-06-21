"""
Authentication router for admin and engineer login
"""

from fastapi import APIRouter, HTTPException, status, Depends
from datetime import timedelta

from models.schemas import LoginRequest, TokenResponse, EngineerLoginRequest, ApiResponse
from core.auth import verify_admin_password, create_access_token, get_settings
from core.database import get_teams_config_manager_instance

router = APIRouter()


@router.post("/admin/login", response_model=TokenResponse)
async def admin_login(login_data: LoginRequest):
    """Admin login endpoint"""
    if not verify_admin_password(login_data.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin password"
        )
    
    access_token = create_access_token(
        data={"user_type": "admin", "sub": "admin"}
    )
    
    return TokenResponse(
        access_token=access_token,
        user_type="admin"
    )


@router.post("/engineer/login", response_model=TokenResponse)
async def engineer_login(login_data: EngineerLoginRequest):
    """Engineer login endpoint with password validation"""
    teams_config_manager = get_teams_config_manager_instance()
    teams_config = teams_config_manager.load_teams_config()
    
    # Verify team exists
    if login_data.team_name not in teams_config:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid team name"
        )
    
    team_config = teams_config[login_data.team_name]
    
    # Handle both old and new data structures
    if isinstance(team_config, dict) and 'developers' in team_config:
        developers = team_config['developers']
    elif isinstance(team_config, list):
        # Convert old format to new format for processing
        developers = [{'name': dev} if isinstance(dev, str) else dev for dev in team_config]
    else:
        developers = []
    
    # Find the developer and validate credentials
    developer_found = False
    password_valid = False
    
    for dev in developers:
        if isinstance(dev, dict):
            dev_name = dev.get('name', '')
            dev_password = dev.get('password', '')
        else:
            dev_name = str(dev)
            dev_password = ''
        
        if dev_name == login_data.developer_name:
            developer_found = True
            # If no password is set for the developer, allow any password
            # If password is set, it must match
            if not dev_password or dev_password == login_data.password:
                password_valid = True
            break
    
    if not developer_found:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid developer name for this team"
        )
    
    if not password_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid password"
        )
    
    access_token = create_access_token(
        data={
            "user_type": "engineer",
            "sub": login_data.developer_name,
            "team": login_data.team_name
        }
    )
    
    return TokenResponse(
        access_token=access_token,
        user_type="engineer"
    )


@router.post("/verify", response_model=ApiResponse)
async def verify_token_endpoint(token_data: dict = Depends(lambda: None)):
    """Verify token endpoint"""
    return ApiResponse(
        success=True,
        message="Token is valid",
        data=token_data
    ) 