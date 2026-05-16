from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta

from app.database import get_db
from app.models.work_hours import EmployeeWorkHours
from app.models.user import User
from app.schemas.work_hours import (
  WorkHoursCreate, WorkHoursResponse, WorkHoursUpdate,
  ClockInRequest, ClockOutRequest, BreakRequest
)
from app.utils.security import get_current_user, require_permission
from app.schemas.user import User as UserSchema

router = APIRouter()


@router.post("/clock-in", response_model=WorkHoursResponse)
async def clock_in(
    request: ClockInRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
  """Clock in for work"""
  today = datetime.now().date()

  # Check if already clocked in today
  existing_entry = db.query(EmployeeWorkHours).filter(
    EmployeeWorkHours.employee_id == current_user.id,
    EmployeeWorkHours.date == today,
    EmployeeWorkHours.clock_in_time.isnot(None)
  ).first()

  if existing_entry:
    raise HTTPException(
      status_code=400,
      detail="Already clocked in today"
    )

  # Get today's schedule or create new entry
  work_hours = db.query(EmployeeWorkHours).filter(
    EmployeeWorkHours.employee_id == current_user.id,
    EmployeeWorkHours.date == today
  ).first()

  if not work_hours:
    # Create new entry with default schedule
    work_hours = EmployeeWorkHours(
      employee_id=current_user.id,
      date=today,
      shift_start=datetime.now().replace(hour=9, minute=0),  # Default 9 AM
      scheduled_hours=8.0  # Default 8 hours
    )
    db.add(work_hours)

  # Clock in
  work_hours.clock_in_time = datetime.now()
  work_hours.is_present = True

  # Check if late
  if work_hours.shift_start and work_hours.clock_in_time > work_hours.shift_start:
    late_delta = work_hours.clock_in_time - work_hours.shift_start
    work_hours.late_minutes = int(late_delta.total_seconds() / 60)

  work_hours.notes = request.notes

  db.commit()
  db.refresh(work_hours)

  return work_hours


@router.post("/clock-out", response_model=WorkHoursResponse)
async def clock_out(
    request: ClockOutRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
  """Clock out from work"""
  today = datetime.now().date()

  # Get today's entry
  work_hours = db.query(EmployeeWorkHours).filter(
    EmployeeWorkHours.employee_id == current_user.id,
    EmployeeWorkHours.date == today,
    EmployeeWorkHours.clock_in_time.isnot(None),
    EmployeeWorkHours.clock_out_time.is_(None)
  ).first()

  if not work_hours:
    raise HTTPException(
      status_code=400,
      detail="Not clocked in today"
    )

  # Clock out
  work_hours.clock_out_time = datetime.now()

  # Check if leaving early
  if work_hours.shift_end and work_hours.clock_out_time < work_hours.shift_end:
    early_delta = work_hours.shift_end - work_hours.clock_out_time
    work_hours.early_departure_minutes = int(early_delta.total_seconds() / 60)

  # Calculate actual hours
  work_hours.calculate_actual_hours()

  if request.notes:
    work_hours.notes = f"{work_hours.notes or ''}\n{request.notes}".strip()

  db.commit()
  db.refresh(work_hours)

  return work_hours


@router.post("/break", response_model=WorkHoursResponse)
async def manage_break(
    request: BreakRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
  """Start or end a break"""
  today = datetime.now().date()

  work_hours = db.query(EmployeeWorkHours).filter(
    EmployeeWorkHours.employee_id == current_user.id,
    EmployeeWorkHours.date == today,
    EmployeeWorkHours.clock_in_time.isnot(None),
    EmployeeWorkHours.clock_out_time.is_(None)
  ).first()

  if not work_hours:
    raise HTTPException(
      status_code=400,
      detail="Not clocked in today"
    )

  if request.break_type == "start":
    if work_hours.is_on_break:
      raise HTTPException(
        status_code=400,
        detail="Already on break"
      )

    work_hours.break_start = datetime.now()
    work_hours.is_on_break = True

  elif request.break_type == "end":
    if not work_hours.is_on_break:
      raise HTTPException(
        status_code=400,
        detail="Not on break"
      )

    work_hours.break_end = datetime.now()
    work_hours.is_on_break = False

    # Calculate break duration
    if work_hours.break_start:
      break_delta = work_hours.break_end - work_hours.break_start
      work_hours.break_duration = break_delta.total_seconds() / 60

  if request.notes:
    work_hours.notes = f"{work_hours.notes or ''}\n{request.notes}".strip()

  db.commit()
  db.refresh(work_hours)

  return work_hours


@router.get("/my-hours", response_model=List[WorkHoursResponse])
async def get_my_work_hours(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
  """Get work hours for current user"""
  query = db.query(EmployeeWorkHours).filter(
    EmployeeWorkHours.employee_id == current_user.id
  )

  if start_date:
    query = query.filter(EmployeeWorkHours.date >= start_date)

  if end_date:
    query = query.filter(EmployeeWorkHours.date <= end_date)

  work_hours = query.order_by(EmployeeWorkHours.date.desc()).all()

  return work_hours


@router.get("/employee/{employee_id}/hours", response_model=List[WorkHoursResponse])
async def get_employee_work_hours(
    employee_id: int,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("view_work_hours"))
):
  """Get work hours for specific employee (admin/manager only)"""
  query = db.query(EmployeeWorkHours).filter(
    EmployeeWorkHours.employee_id == employee_id
  )

  if start_date:
    query = query.filter(EmployeeWorkHours.date >= start_date)

  if end_date:
    query = query.filter(EmployeeWorkHours.date <= end_date)

  work_hours = query.order_by(EmployeeWorkHours.date.desc()).all()

  return work_hours


@router.get("/summary")
async def get_work_hours_summary(
    period: str = "week",  # week, month
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
  """Get work hours summary"""
  from sqlalchemy import func

  if period == "week":
    start_date = datetime.now() - timedelta(days=7)
  else:  # month
    start_date = datetime.now() - timedelta(days=30)

  # For current user
  summary = db.query(
    func.count(EmployeeWorkHours.id).label("days_worked"),
    func.sum(EmployeeWorkHours.actual_hours).label("total_hours"),
    func.avg(EmployeeWorkHours.actual_hours).label("avg_hours_per_day"),
    func.sum(EmployeeWorkHours.overtime_hours).label("total_overtime")
  ).filter(
    EmployeeWorkHours.employee_id == current_user.id,
    EmployeeWorkHours.date >= start_date,
    EmployeeWorkHours.clock_out_time.isnot(None)
  ).first()

  # Late arrivals
  late_days = db.query(func.count(EmployeeWorkHours.id)).filter(
    EmployeeWorkHours.employee_id == current_user.id,
    EmployeeWorkHours.date >= start_date,
    EmployeeWorkHours.late_minutes > 0
  ).scalar() or 0

  return {
    "period": period,
    "days_worked": summary.days_worked or 0,
    "total_hours": float(summary.total_hours or 0),
    "average_hours_per_day": float(summary.avg_hours_per_day or 0),
    "total_overtime_hours": float(summary.total_overtime or 0),
    "late_days": late_days
  }