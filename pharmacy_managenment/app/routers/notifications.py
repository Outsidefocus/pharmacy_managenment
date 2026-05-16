from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from app.database import get_db
from app.models.notification import Notification, NotificationTemplate, NotificationPreference
from app.schemas.notification import (
  NotificationResponse, NotificationCreate, NotificationTemplateCreate,
  NotificationTemplateResponse, NotificationPreferenceUpdate, NotificationPreferenceResponse
)
from app.utils.security import get_current_user
from app.schemas.user import User
from app.services.notification_service import NotificationService

router = APIRouter()


@router.get("/", response_model=List[NotificationResponse])
async def get_my_notifications(
    skip: int = 0,
    limit: int = 50,
    unread_only: bool = False,
    category: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
  """Get notifications for current user"""
  query = db.query(Notification).filter(
    (Notification.user_id == current_user.id) | (Notification.customer_id == None)
  )

  if unread_only:
    query = query.filter(Notification.is_read == False)

  if category:
    query = query.filter(Notification.category == category)

  notifications = query.order_by(Notification.created_at.desc()).offset(skip).limit(limit).all()
  return notifications


@router.get("/unread-count")
async def get_unread_count(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
  """Get count of unread notifications"""
  count = db.query(Notification).filter(
    Notification.user_id == current_user.id,
    Notification.is_read == False
  ).count()
  return {"unread_count": count}


@router.post("/{notification_id}/read")
async def mark_as_read(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
  """Mark notification as read"""
  notification = db.query(Notification).filter(
    Notification.id == notification_id,
    Notification.user_id == current_user.id
  ).first()
  if not notification:
    raise HTTPException(status_code=404, detail="Notification not found")

  notification.is_read = True
  notification.read_at = datetime.now()
  db.commit()

  return {"message": "Notification marked as read"}


@router.post("/mark-all-read")
async def mark_all_read(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
  """Mark all notifications as read"""
  db.query(Notification).filter(
    Notification.user_id == current_user.id,
    Notification.is_read == False
  ).update({"is_read": True, "read_at": datetime.now()})
  db.commit()

  return {"message": "All notifications marked as read"}


@router.delete("/{notification_id}")
async def delete_notification(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
  """Delete a notification"""
  notification = db.query(Notification).filter(
    Notification.id == notification_id,
    Notification.user_id == current_user.id
  ).first()
  if not notification:
    raise HTTPException(status_code=404, detail="Notification not found")

  db.delete(notification)
  db.commit()

  return {"message": "Notification deleted"}


@router.get("/preferences", response_model=NotificationPreferenceResponse)
async def get_preferences(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
  """Get user notification preferences"""
  pref = db.query(NotificationPreference).filter(
    NotificationPreference.user_id == current_user.id
  ).first()
  if not pref:
    pref = NotificationPreference(user_id=current_user.id)
    db.add(pref)
    db.commit()
    db.refresh(pref)
  return pref


@router.put("/preferences", response_model=NotificationPreferenceResponse)
async def update_preferences(
    pref_update: NotificationPreferenceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
  """Update notification preferences"""
  pref = db.query(NotificationPreference).filter(
    NotificationPreference.user_id == current_user.id
  ).first()
  if not pref:
    pref = NotificationPreference(user_id=current_user.id)
    db.add(pref)
    db.commit()
    db.refresh(pref)

  update_data = pref_update.dict(exclude_unset=True)
  for field, value in update_data.items():
    setattr(pref, field, value)

  db.commit()
  db.refresh(pref)
  return pref


# Admin endpoints for templates
@router.get("/templates", response_model=List[NotificationTemplateResponse])
async def get_templates(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
  """Get all notification templates (admin only)"""
  # In a real app, add admin permission check
  templates = db.query(NotificationTemplate).all()
  return templates


@router.post("/templates", response_model=NotificationTemplateResponse)
async def create_template(
    template: NotificationTemplateCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
  """Create notification template (admin only)"""
  db_template = NotificationTemplate(**template.dict())
  db.add(db_template)
  db.commit()
  db.refresh(db_template)
  return db_template


@router.put("/templates/{template_id}", response_model=NotificationTemplateResponse)
async def update_template(
    template_id: int,
    template_update: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
  """Update notification template (admin only)"""
  db_template = db.query(NotificationTemplate).filter(
    NotificationTemplate.id == template_id
  ).first()
  if not db_template:
    raise HTTPException(status_code=404, detail="Template not found")

  for field, value in template_update.items():
    if hasattr(db_template, field):
      setattr(db_template, field, value)

  db.commit()
  db.refresh(db_template)
  return db_template


@router.post("/test-email")
async def test_email(
    email: str,
    current_user: User = Depends(get_current_user)
):
  """Send test email to verify configuration"""
  success = await NotificationService.send_email(
    to_email=email,
    subject="Test Email from Pharmacy System",
    body="This is a test email to verify email configuration."
  )
  if success:
    return {"message": "Test email sent"}
  else:
    raise HTTPException(status_code=500, detail="Failed to send test email")