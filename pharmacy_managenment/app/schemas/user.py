from pydantic import BaseModel, EmailStr, validator
from typing import Optional, List
from datetime import datetime
from enum import Enum
from app.models.user import UserRole


class UserRoleEnum(str, Enum):
  ADMIN = "admin"
  PHARMACIST = "pharmacist"
  TECHNICIAN = "technician"
  MANAGER = "manager"
  CASHIER = "cashier"
  INVENTORY_MANAGER = "inventory_manager"
  CUSTOMER = "customer"


class UserBase(BaseModel):
  username: str
  email: EmailStr
  first_name: str
  last_name: str
  phone: Optional[str] = None
  role: UserRoleEnum = UserRoleEnum.PHARMACIST


class UserCreate(UserBase):
  password: str

  @validator('password')
  def password_strength(cls, v):
    if len(v) < 8:
      raise ValueError('Password must be at least 8 characters long')
    return v


class UserUpdate(BaseModel):
  email: Optional[EmailStr] = None
  first_name: Optional[str] = None
  last_name: Optional[str] = None
  phone: Optional[str] = None
  password: Optional[str] = None
  role: Optional[UserRoleEnum] = None
  is_active: Optional[bool] = None

  @validator('password')
  def password_strength(cls, v):
    if v and len(v) < 8:
      raise ValueError('Password must be at least 8 characters long')
    return v


class UserResponse(UserBase):
  id: int
  is_active: bool
  is_verified: bool
  created_at: datetime
  updated_at: Optional[datetime] = None

  class Config:
    from_attributes = True


class Token(BaseModel):
  access_token: str
  token_type: str
  user_id: int
  username: str
  role: str


class TokenData(BaseModel):
  username: Optional[str] = None
  role: Optional[str] = None


class LoginRequest(BaseModel):
  username: str
  password: str


class ChangePasswordRequest(BaseModel):
  old_password: str
  new_password: str
  confirm_password: str

  @validator('confirm_password')
  def passwords_match(cls, v, values):
    if 'new_password' in values and v != values['new_password']:
      raise ValueError('Passwords do not match')
    return v

  @validator('new_password')
  def password_strength(cls, v):
    if len(v) < 8:
      raise ValueError('Password must be at least 8 characters long')
    return v


class UserStats(BaseModel):
  total_users: int
  active_users: int
  users_by_role: dict
  new_users_today: int
  new_users_this_week: int