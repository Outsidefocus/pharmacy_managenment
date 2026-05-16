from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
from datetime import datetime


class Notification(Base):
  __tablename__ = "notifications"

  id = Column(Integer, primary_key=True, index=True)

  # Recipient
  user_id = Column(Integer, ForeignKey("users.id"))
  customer_id = Column(Integer, ForeignKey("customers.id"))

  # Notification Details
  notification_type = Column(String(100), nullable=False)  # system, email, sms, push
  category = Column(String(100))  # stock, expiry, order, payment, system
  priority = Column(String(20), default="medium")  # low, medium, high, critical

  # Content
  title = Column(String(200), nullable=False)
  message = Column(Text, nullable=False)
  data = Column(JSON)  # Additional data for the notification

  # Delivery Status
  status = Column(String(50), default="pending")  # pending, sent, delivered, read, failed
  delivery_method = Column(String(50))  # email, sms, in_app, push
  delivery_status = Column(JSON)  # Delivery provider response

  # Reference
  reference_type = Column(String(100))  # Order, Product, Payment, etc.
  reference_id = Column(Integer)

  # Read Status
  is_read = Column(Boolean, default=False)
  read_at = Column(DateTime(timezone=True))

  # Scheduled Send
  scheduled_for = Column(DateTime(timezone=True))
  sent_at = Column(DateTime(timezone=True))

  # Retry Logic
  retry_count = Column(Integer, default=0)
  max_retries = Column(Integer, default=3)
  next_retry = Column(DateTime(timezone=True))

  created_at = Column(DateTime(timezone=True), server_default=func.now())
  updated_at = Column(DateTime(timezone=True), onupdate=func.now())

  # Relationships
  user = relationship("User")
  customer = relationship("Customer")


class NotificationTemplate(Base):
  __tablename__ = "notification_templates"

  id = Column(Integer, primary_key=True, index=True)
  template_code = Column(String(100), unique=True, index=True)

  # Template Details
  name = Column(String(200), nullable=False)
  description = Column(Text)

  # Content
  subject = Column(String(500))
  body = Column(Text, nullable=False)
  html_body = Column(Text)

  # Variables
  variables = Column(JSON)  # List of variables that can be used in template

  # Settings
  notification_type = Column(String(100), nullable=False)
  category = Column(String(100))
  is_active = Column(Boolean, default=True)

  # Delivery
  delivery_methods = Column(JSON)  # ["email", "sms", "push"]
  priority = Column(String(20), default="medium")

  created_at = Column(DateTime(timezone=True), server_default=func.now())
  updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class NotificationPreference(Base):
  __tablename__ = "notification_preferences"

  id = Column(Integer, primary_key=True, index=True)
  user_id = Column(Integer, ForeignKey("users.id"), unique=True)

  # Email Preferences
  email_notifications = Column(Boolean, default=True)
  email_categories = Column(JSON)  # ["stock", "expiry", "order", "payment"]

  # SMS Preferences
  sms_notifications = Column(Boolean, default=False)
  sms_categories = Column(JSON)  # ["urgent", "reminder"]

  # Push Preferences
  push_notifications = Column(Boolean, default=True)
  push_categories = Column(JSON)

  # Quiet Hours
  quiet_hours_enabled = Column(Boolean, default=False)
  quiet_start = Column(String(10))  # "22:00"
  quiet_end = Column(String(10))  # "08:00"

  # Frequency
  digest_frequency = Column(String(20), default="daily")  # realtime, hourly, daily, weekly

  created_at = Column(DateTime(timezone=True), server_default=func.now())
  updated_at = Column(DateTime(timezone=True), onupdate=func.now())

  # Relationships
  user = relationship("User")