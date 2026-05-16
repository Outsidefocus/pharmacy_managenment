from sqlalchemy.orm import Session
from typing import Optional, List, Any
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate
from app.utils.security import get_password_hash
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def get_user(db: Session, user_id: int) -> Optional[User]:
  """Get user by ID"""
  return db.query(User).filter(user_id == User.id).first()


def get_user_by_email(db: Session, email: str) -> Optional[User]:
  """Get user by email
  :rtype: Optional[User]
  """
  return db.query(User).filter(email == User.email).first()


def get_user_by_username(db: Session, username: str) -> Optional[User]:
  """Get user by username"""
  return db.query(User).filter(username == User.username).first()


def get_users(db: Session, skip: int = 0, limit: int = 100) -> list[type[User]]:
  """Get all users with pagination"""
  return db.query(User).offset(skip).limit(limit).all()


def create_user(db: Session, user: UserCreate) -> User:
  """Create new user"""
  db_user = User(
    username=user.username,
    email=user.email,
    password_hash=get_password_hash(user.password),
    first_name=user.first_name,
    last_name=user.last_name,
    phone=user.phone,
    role=user.role
  )
  db.add(db_user)
  db.commit()
  db.refresh(db_user)
  logger.info(f"Created user: {user.username}")
  return db_user


def update_user(db: Session, user_id: int, user_update: UserUpdate) -> Optional[User]:
  """Update user"""
  db_user = get_user(db, user_id)
  if not db_user:
    return None

  update_data = user_update.dict(exclude_unset=True)

  if 'password' in update_data:
    update_data['password_hash'] = get_password_hash(update_data.pop('password'))

  for field, value in update_data.items():
    setattr(db_user, field, value)

  db.commit()
  db.refresh(db_user)
  logger.info(f"Updated user: {db_user.username}")
  return db_user


def delete_user(db: Session, user_id: int) -> bool:
  """Delete user"""
  db_user = get_user(db, user_id)
  if not db_user:
    return False

  db.delete(db_user)
  db.commit()
  logger.info(f"Deleted user: {db_user.username}")
  return True


def update_user_last_login(db: Session, user_id: int):
  """Update user's last login timestamp"""
  db_user = get_user(db, user_id)
  if db_user:
    db_user.last_login = datetime.now()
    db_user.failed_login_attempts = 0
    db_user.locked_until = None
    db.commit()
    db.refresh(db_user)


def increment_failed_login(db: Session, user_id: int):
  """Increment failed login attempts"""
  db_user = get_user(db, user_id)
  if db_user:
    db_user.failed_login_attempts += 1

    # Lock account after 5 failed attempts
    if db_user.failed_login_attempts >= 5:
      from datetime import datetime, timedelta
      db_user.locked_until = datetime.now() + timedelta(hours=1)

    db.commit()


def get_users_by_role(db: Session, role: str) -> list[type[User]]:
  """Get users by role"""
  return db.query(User).filter(role == User.role, True == User.is_active).all()


def search_users(db: Session, search_term: str, skip: int = 0, limit: int = 50) -> list[type[User]]:
  """Search users by name, email, or username"""
  return db.query(User).filter(
    (User.first_name.ilike(f"%{search_term}%")) |
    (User.last_name.ilike(f"%{search_term}%")) |
    (User.email.ilike(f"%{search_term}%")) |
    (User.username.ilike(f"%{search_term}%"))
  ).offset(skip).limit(limit).all()


def get_user_stats(db: Session) -> dict:
  """Get user statistics"""
  from sqlalchemy import func, case

  total_users = db.query(func.count(User.id)).scalar()
  active_users = db.query(func.count(User.id)).filter(True == User.is_active).scalar()

  # Users by role
  users_by_role = {}
  roles = db.query(User.role, func.count(User.id)).group_by(User.role).all()
  for role, count in roles:
    users_by_role[role] = count

  # New users today
  from datetime import datetime, timedelta
  today = datetime.now().date()
  new_users_today = db.query(func.count(User.id)).filter(
    today == func.date(User.created_at)
  ).scalar()

  # New users this week
  week_start = today - timedelta(days=today.weekday())
  new_users_week = db.query(func.count(User.id)).filter(
    func.date(User.created_at) >= week_start
  ).scalar()

  return {
    "total_users": total_users,
    "active_users": active_users,
    "users_by_role": users_by_role,
    "new_users_today": new_users_today,
    "new_users_this_week": new_users_week
  }