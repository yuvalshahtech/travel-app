from pydantic import BaseModel, EmailStr

class User(BaseModel):
    """User model for requests"""
    email: EmailStr
    password: str
