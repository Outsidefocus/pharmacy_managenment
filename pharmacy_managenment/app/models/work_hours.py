from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
from datetime import datetime


class EmployeeWorkHours(Base):
  __tablename__ = "employee_work_hours"

  id = Column(Integer, primary_key=True, index=True)
  employee_id = Column(Integer, ForeignKey("users.id"), nullable=False)
  date = Column(DateTime, nullable=False)

  # Working hours
  shift_start = Column(DateTime, nullable=False)
  shift_end = Column(DateTime)
  scheduled_hours = Column(Float)  # Scheduled hours for the day
  actual_hours = Column(Float)  # Actual hours worked

  # Breaks
  break_start = Column(DateTime)
  break_end = Column(DateTime)
  break_duration = Column(Float)  # In minutes

  # Status
  is_present = Column(Boolean, default=True)
  is_on_break = Column(Boolean, default=False)
  is_overtime = Column(Boolean, default=False)
  overtime_hours = Column(Float, default=0.0)

  # Attendance
  clock_in_time = Column(DateTime)
  clock_out_time = Column(DateTime)
  late_minutes = Column(Integer, default=0)
  early_departure_minutes = Column(Integer, default=0)

  # Notes
  notes = Column(String(500))

  # Approval
  approved_by = Column(Integer, ForeignKey("users.id"))
  approval_status = Column(String(50), default="pending")  # pending, approved, rejected
  approval_notes = Column(String(500))

  created_at = Column(DateTime(timezone=True), server_default=func.now())
  updated_at = Column(DateTime(timezone=True), onupdate=func.now())

  # Relationships
  employee = relationship("User", foreign_keys=[employee_id])
  approver = relationship("User", foreign_keys=[approved_by])

  def calculate_actual_hours(self):
    """Calculate actual hours worked"""
    if self.clock_in_time and self.clock_out_time:
      delta = self.clock_out_time - self.clock_in_time
      hours = delta.total_seconds() / 3600

      # Subtract break duration
      if self.break_duration:
        hours -= (self.break_duration / 60)

      self.actual_hours = round(hours, 2)

      # Check for overtime
      if self.scheduled_hours and hours > self.scheduled_hours:
        self.is_overtime = True
        self.overtime_hours = round(hours - self.scheduled_hours, 2)

      return self.actual_hours
    return 0