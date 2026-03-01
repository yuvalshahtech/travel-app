from pydantic import BaseModel, EmailStr


class UserLogin(BaseModel):
    """Request schema for login and signup"""
    email: EmailStr
    password: str
