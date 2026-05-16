from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
from datetime import datetime


class Report(Base):
  __tablename__ = "reports"

  id = Column(Integer, primary_key=True, index=True)
  report_code = Column(String(100), unique=True, index=True)

  # Report Details
  report_type = Column(String(100), nullable=False)  # sales, inventory, financial, customer
  title = Column(String(200), nullable=False)
  description = Column(Text)

  # Period
  period_type = Column(String(50))  # daily, weekly, monthly, quarterly, yearly, custom
  start_date = Column(DateTime, nullable=False)
  end_date = Column(DateTime, nullable=False)

  # Generated Data
  data = Column(JSON)  # Store the actual report data
  summary = Column(JSON)  # Key metrics and summary
  charts = Column(JSON)  # Chart configurations and data

  # Filters Applied
  filters = Column(JSON)  # Filters used to generate report

  # Status
  status = Column(String(50), default="generated")  # generating, generated, failed
  generation_progress = Column(Integer, default=0)  # 0-100

  # Format
  format = Column(String(50), default="json")  # json, pdf, excel, csv
  file_url = Column(String(500))  # URL to generated file

  # User Information
  generated_by = Column(Integer, ForeignKey("users.id"))
  generated_for = Column(Integer, ForeignKey("users.id"))

  # Schedule
  is_scheduled = Column(Boolean, default=False)
  schedule_frequency = Column(String(50))  # daily, weekly, monthly
  next_schedule = Column(DateTime)

  # Dates
  generated_at = Column(DateTime(timezone=True), server_default=func.now())
  viewed_at = Column(DateTime(timezone=True))

  created_at = Column(DateTime(timezone=True), server_default=func.now())
  updated_at = Column(DateTime(timezone=True), onupdate=func.now())

  # Relationships
  generator = relationship("User", foreign_keys=[generated_by])
  recipient = relationship("User", foreign_keys=[generated_for])


class Dashboard(Base):
  __tablename__ = "dashboards"

  id = Column(Integer, primary_key=True, index=True)
  name = Column(String(200), nullable=False)
  description = Column(Text)

  # Layout
  layout = Column(JSON)  # Dashboard widget layout
  widgets = Column(JSON)  # List of widget configurations

  # Access Control
  is_public = Column(Boolean, default=False)
  allowed_roles = Column(JSON)  # Roles that can view this dashboard
  allowed_users = Column(JSON)  # Specific users that can view

  # Owner
  created_by = Column(Integer, ForeignKey("users.id"))

  created_at = Column(DateTime(timezone=True), server_default=func.now())
  updated_at = Column(DateTime(timezone=True), onupdate=func.now())

  # Relationships
  owner = relationship("User", foreign_keys=[created_by])


class Widget(Base):
  __tablename__ = "widgets"

  id = Column(Integer, primary_key=True, index=True)
  widget_type = Column(String(100), nullable=False)  # chart, metric, table, list
  title = Column(String(200), nullable=False)

  # Configuration
  config = Column(JSON)  # Widget configuration
  data_source = Column(String(500))  # API endpoint or query
  refresh_interval = Column(Integer)  # Seconds

  # Size and Position
  width = Column(Integer, default=4)  # In grid columns (1-12)
  height = Column(Integer, default=300)  # In pixels

  # Filters
  filters = Column(JSON)

  created_at = Column(DateTime(timezone=True), server_default=func.now())
  updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class AuditLog(Base):
  __tablename__ = "audit_logs"

  id = Column(Integer, primary_key=True, index=True)

  # Action Details
  action = Column(String(100), nullable=False)  # create, update, delete, login, etc.
  entity_type = Column(String(100), nullable=False)  # User, Product, Order, etc.
  entity_id = Column(Integer)  # ID of the affected entity

  # Changes
  old_values = Column(JSON)  # Values before change
  new_values = Column(JSON)  # Values after change

  # User Information
  user_id = Column(Integer, ForeignKey("users.id"))
  user_ip = Column(String(50))
  user_agent = Column(String(500))

  # Location
  location = Column(String(200))

  # Status
  status = Column(String(50), default="success")  # success, failed
  error_message = Column(Text)

  created_at = Column(DateTime(timezone=True), server_default=func.now())

  # Relationships
  user = relationship("User")