from datetime import datetime
import uuid
from pydantic import EmailStr
from pydantic import BaseModel



class LoginRequestModel(BaseModel):
    email : EmailStr
    password : str

class LoginResponseModel(BaseModel):
    user_id : uuid.UUID
    name : str
    email : str
    access_token : str
    access_token_expiry : int
    refresh_token : str
    created_at : datetime
    updated_at : datetime


class RegisterRequestModel(BaseModel):
    name : str
    email : EmailStr
    password : str


class RegisterResponseModel(BaseModel):
    user_id : uuid.UUID
    name : str
    email : str
    created_at : datetime
    updated_at : datetime


class RefreshTokenRequestModel(BaseModel):
    refresh_token : str


class RefreshTokenResponseModel(BaseModel):
    access_token : str
    access_token_expiry : int
    refresh_token : str
