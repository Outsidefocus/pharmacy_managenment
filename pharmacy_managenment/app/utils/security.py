from datetime import datetime, timedelta
from typing import Optional, Union, Any
from jose import jwt, JWTError
from passlib.context import CryptContext
from fastapi.security import OAuth2PasswordBearer
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User, UserRole
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token")


def verify_password(plain_password: str, hashed_password: str) -> bool:
  """Verify password against hash"""
  return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
  """Hash password"""
  return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
  """Create JWT access token"""
  to_encode = data.copy()

  if expires_delta:
    expire = datetime.utcnow() + expires_delta
  else:
    expire = datetime.utcnow() + timedelta(minutes=15)

  to_encode.update({"exp": expire})
  encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
  return encoded_jwt


def verify_token(token: str) -> Optional[dict]:
  """Verify JWT token"""
  try:
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    return payload
  except JWTError as e:
    logger.error(f"Token verification failed: {e}")
    return None


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
  """Get current user from token"""
  credentials_exception = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
  )

  try:
    payload = verify_token(token)
    if payload is None:
      raise credentials_exception

    username: str = payload.get("sub")
    role: str = payload.get("role")

    if username is None:
      raise credentials_exception

    user = db.query(User).filter(User.username == username).first()
    if user is None:
      raise credentials_exception

    # Check if user is active
    if not user.is_active:
      raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Inactive user"
      )

    # Check if user is locked
    if user.is_locked():
      raise HTTPException(
        status_code=status.HTTP_423_LOCKED,
        detail="Account is temporarily locked"
      )

    return user

  except JWTError:
    raise credentials_exception


async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
  """Get current active user"""
  if not current_user.is_active:
    raise HTTPException(status_code=400, detail="Inactive user")
  return current_user


async def get_current_admin_user(current_user: User = Depends(get_current_user)) -> User:
  """Get current admin user"""
  if current_user.role != UserRole.ADMIN:
    raise HTTPException(
      status_code=status.HTTP_403_FORBIDDEN,
      detail="Not enough permissions"
    )
  return current_user


async def get_current_pharmacist_user(current_user: User = Depends(get_current_user)) -> User:
  """Get current pharmacist user"""
  if current_user.role not in [UserRole.PHARMACIST, UserRole.ADMIN, UserRole.MANAGER]:
    raise HTTPException(
      status_code=status.HTTP_403_FORBIDDEN,
      detail="Not enough permissions"
    )
  return current_user


async def get_current_manager_user(current_user: User = Depends(get_current_user)) -> User:
  """Get current manager user"""
  if current_user.role not in [UserRole.MANAGER, UserRole.ADMIN]:
    raise HTTPException(
      status_code=status.HTTP_403_FORBIDDEN,
      detail="Not enough permissions"
    )
  return current_user


def check_permission(user: User, permission: str) -> bool:
  """Check if user has specific permission"""
  if user.is_superuser:
    return True

  # Check user-specific permissions
  if user.permissions and permission in user.permissions:
    return True

  # Role-based permissions
  role_permissions = {
    UserRole.ADMIN: ["all"],
    UserRole.MANAGER: [
      "view_reports", "manage_inventory", "manage_orders",
      "manage_customers", "manage_payments", "manage_users",
      "view_analytics", "export_data"
    ],
    UserRole.PHARMACIST: [
      "dispense_medication", "verify_prescription",
      "manage_orders", "view_inventory", "view_customers",
      "process_payments"
    ],
    UserRole.TECHNICIAN: [
      "prepare_orders", "view_inventory", "view_orders"
    ],
    UserRole.CASHIER: [
      "process_payments", "create_orders", "view_orders",
      "view_customers"
    ],
    UserRole.INVENTORY_MANAGER: [
      "manage_inventory", "view_reports", "order_supplies",
      "manage_suppliers"
    ],
    UserRole.CUSTOMER: ["view_own_orders", "make_payments", "view_profile"]
  }

  return permission in role_permissions.get(user.role, [])


async def require_permission(permission: str, current_user: User = Depends(get_current_user)) -> User:
  """Dependency to require specific permission"""
  if not check_permission(current_user, permission):
    raise HTTPException(
      status_code=status.HTTP_403_FORBIDDEN,
      detail=f"Permission denied: {permission}"
    )
  return current_user


def generate_api_key(user_id: int) -> str:
  """Generate API key for user"""
  data = {
    "user_id": user_id,
    "type": "api_key",
    "exp": datetime.utcnow() + timedelta(days=365)  # 1 year expiry
  }
  return jwt.encode(data, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def verify_api_key(api_key: str) -> Optional[int]:
  """Verify API key and return user ID"""
  try:
    payload = jwt.decode(api_key, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    if payload.get("type") != "api_key":
      return None

    user_id = payload.get("user_id")
    if not user_id:
      return None

    return user_id

  except JWTError:
    return None


def generate_password_reset_token(email: str) -> str:
  """Generate password reset token"""
  expires_delta = timedelta(hours=24)
  data = {"sub": email, "type": "password_reset"}
  return create_access_token(data, expires_delta)


def verify_password_reset_token(token: str) -> Optional[str]:
  """Verify password reset token"""
  try:
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    if payload.get("type") != "password_reset":
      return None

    email = payload.get("sub")
    return email

  except JWTError:
    return None


def generate_email_verification_token(email: str) -> str:
  """Generate email verification token"""
  expires_delta = timedelta(hours=48)
  data = {"sub": email, "type": "email_verification"}
  return create_access_token(data, expires_delta)


def verify_email_verification_token(token: str) -> Optional[str]:
  """Verify email verification token"""
  try:
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    if payload.get("type") != "email_verification":
      return None

    email = payload.get("sub")
    return email

  except JWTError:
    return None