from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class WorkHoursBase(BaseModel):
  employee_id: int
  date: datetime
  shift_start: datetime
  shift_end: Optional[datetime] = None
  scheduled_hours: Optional[float] = None


class WorkHoursCreate(WorkHoursBase):
  pass


class WorkHoursUpdate(BaseModel):
  clock_in_time: Optional[datetime] = None
  clock_out_time: Optional[datetime] = None
  break_start: Optional[datetime] = None
  break_end: Optional[datetime] = None
  notes: Optional[str] = None
  is_present: Optional[bool] = None


class WorkHoursResponse(WorkHoursBase):
  id: int
  actual_hours: Optional[float] = None
  break_duration: Optional[float] = None
  is_present: bool
  is_on_break: bool
  is_overtime: bool
  overtime_hours: float
  clock_in_time: Optional[datetime] = None
  clock_out_time: Optional[datetime] = None
  late_minutes: int
  early_departure_minutes: int
  approval_status: str
  employee_name: Optional[str] = None
  created_at: datetime
  updated_at: Optional[datetime] = None

  class Config:
    from_attributes = True


class ClockInRequest(BaseModel):
  notes: Optional[str] = None


class ClockOutRequest(BaseModel):
  notes: Optional[str] = None


class BreakRequest(BaseModel):
  break_type: str  # start, end
  notes: Optional[str] = None