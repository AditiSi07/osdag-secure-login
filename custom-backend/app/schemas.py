from pydantic import BaseModel, EmailStr


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str


class RegisterResponse(BaseModel):
    id: str
    email: str
class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LoginUserInfo(BaseModel):
    id: str
    email: str


class LoginResponse(BaseModel):
    token: str
    user: LoginUserInfo
class ProfileResponse(BaseModel):
    id: str
    email: str
    profile: dict