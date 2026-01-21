from pydantic import BaseModel, EmailStr

class User(BaseModel):
    """User model for requests"""
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    """User response model"""
    id: int
    email: str
    message: str
