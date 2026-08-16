from fastapi import APIRouter, Depends

from app.auth import get_current_user
from app.models import User
from app.schemas import ProfileResponse

router = APIRouter()


@router.get("/me", response_model=ProfileResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return ProfileResponse(
        id=str(current_user.id),
        email=current_user.email,
        profile={
            "fullName": current_user.full_name,
            "displayName": current_user.display_name,
            "bio": current_user.bio,
            "createdAt": current_user.created_at.isoformat() + "Z",
            "role": current_user.role,
        },
    )