from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta
from typing import Any

from app.database import get_db
from app.models.user import User
from app.schemas.user import UserCreate, UserResponse, Token, UserUpdate
from app.core.config import settings
from app.utils.security import (
  get_password_hash, verify_password,
  create_access_token, get_current_user,
  get_current_active_user, get_current_admin_user
)
from app.crud.user_crud import (
  create_user, get_user_by_email,
  get_user_by_username, update_user,
  delete_user, get_users
)

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token")


@router.post("/register", response_model=UserResponse)
async def register(
    user_data: UserCreate,
    db: Session = Depends(get_db)
):
  """Register a new user"""
  # Check if user exists
  db_user = get_user_by_email(db, email=user_data.email)
  if db_user:
    raise HTTPException(
      status_code=status.HTTP_400_BAD_REQUEST,
      detail="Email already registered"
    )

  db_user = get_user_by_username(db, username=user_data.username)
  if db_user:
    raise HTTPException(
      status_code=status.HTTP_400_BAD_REQUEST,
      detail="Username already taken"
    )

  # Create new user
  user_data.password = get_password_hash(user_data.password)
  user = create_user(db, user_data)

  return user


@router.post("/token", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
  """Login and get access token"""
  user = get_user_by_username(db, username=form_data.username)
  if not user or not verify_password(form_data.password, user.password_hash):
    raise HTTPException(
      status_code=status.HTTP_401_UNAUTHORIZED,
      detail="Incorrect username or password",
      headers={"WWW-Authenticate": "Bearer"},
    )

  if not user.is_active:
    raise HTTPException(
      status_code=status.HTTP_400_BAD_REQUEST,
      detail="Inactive user"
    )

  access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
  access_token = create_access_token(
    data={"sub": user.username, "role": user.role},
    expires_delta=access_token_expires
  )

  return {
    "access_token": access_token,
    "token_type": "bearer",
    "user_id": user.id,
    "username": user.username,
    "role": user.role
  }


@router.get("/me", response_model=UserResponse)
async def read_users_me(
    current_user: User = Depends(get_current_active_user)
):
  """Get current user info"""
  return current_user


@router.put("/me", response_model=UserResponse)
async def update_user_me(
    user_update: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
  """Update current user"""
  if user_update.password:
    user_update.password = get_password_hash(user_update.password)

  updated_user = update_user(db, current_user.id, user_update)
  return updated_user


@router.post("/logout")
async def logout(
    current_user: User = Depends(get_current_active_user)
):
  """Logout user (client should discard token)"""
  return {"message": "Successfully logged out"}


@router.post("/refresh-token", response_model=Token)
async def refresh_token(
    current_user: User = Depends(get_current_active_user)
):
  """Refresh access token"""
  access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
  access_token = create_access_token(
    data={"sub": current_user.username, "role": current_user.role},
    expires_delta=access_token_expires
  )

  return {
    "access_token": access_token,
    "token_type": "bearer",
    "user_id": current_user.id,
    "username": current_user.username,
    "role": current_user.role
  }


@router.post("/change-password")
async def change_password(
    old_password: str,
    new_password: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
  """Change user password"""
  if not verify_password(old_password, current_user.password_hash):
    raise HTTPException(
      status_code=status.HTTP_400_BAD_REQUEST,
      detail="Old password is incorrect"
    )

  current_user.password_hash = get_password_hash(new_password)
  db.commit()
  db.refresh(current_user)

  return {"message": "Password changed successfully"}


@router.get("/users", response_model=list[UserResponse])
async def read_all_users(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
  """Get all users (admin only)"""
  users = get_users(db, skip=skip, limit=limit)
  return users


@router.get("/users/{user_id}", response_model=UserResponse)
async def read_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
  """Get user by ID (admin only)"""
  user = db.query(User).filter(user_id == User.id).first()
  if not user:
    raise HTTPException(
      status_code=status.HTTP_404_NOT_FOUND,
      detail="User not found"
    )
  return user


@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user_admin(
    user_id: int,
    user_update: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
  """Update user (admin only)"""
  if user_update.password:
    user_update.password = get_password_hash(user_update.password)

  updated_user = update_user(db, user_id, user_update)
  if not updated_user:
    raise HTTPException(
      status_code=status.HTTP_404_NOT_FOUND,
      detail="User not found"
    )
  return updated_user


@router.delete("/users/{user_id}")
async def delete_user_admin(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
  """Delete user (admin only)"""
  if current_user.id == user_id:
    raise HTTPException(
      status_code=status.HTTP_400_BAD_REQUEST,
      detail="Cannot delete yourself"
    )

  success = delete_user(db, user_id)
  if not success:
    raise HTTPException(
      status_code=status.HTTP_404_NOT_FOUND,
      detail="User not found"
    )

  return {"message": "User deleted successfully"}