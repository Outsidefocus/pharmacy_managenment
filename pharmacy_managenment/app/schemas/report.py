from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class ReportType(str, Enum):
  SALES = "sales"
  INVENTORY = "inventory"
  FINANCIAL = "financial"
  CUSTOMER = "customer"
  PROFIT_LOSS = "profit_loss"
  EXPIRY = "expiry"
  STAFF_PERFORMANCE = "staff_performance"


class PeriodType(str, Enum):
  DAILY = "daily"
  WEEKLY = "weekly"
  MONTHLY = "monthly"
  QUARTERLY = "quarterly"
  YEARLY = "yearly"
  CUSTOM = "custom"


class ReportBase(BaseModel):
  report_type: ReportType
  title: str
  description: Optional[str] = None
  period_type: PeriodType
  start_date: datetime
  end_date: datetime
  filters: Optional[Dict[str, Any]] = None


class ReportCreate(ReportBase):
  pass


class ReportResponse(ReportBase):
  id: int
  report_code: str
  data: Dict[str, Any]
  summary: Dict[str, Any]
  charts: Optional[Dict[str, Any]] = None
  status: str
  generation_progress: int
  format: str
  file_url: Optional[str] = None
  generated_by: Optional[int] = None
  generator_name: Optional[str] = None
  generated_for: Optional[int] = None
  recipient_name: Optional[str] = None
  is_scheduled: bool
  schedule_frequency: Optional[str] = None
  next_schedule: Optional[datetime] = None
  generated_at: datetime
  viewed_at: Optional[datetime] = None
  created_at: datetime
  updated_at: Optional[datetime] = None

  class Config:
    from_attributes = True


class SalesReportRequest(BaseModel):
  start_date: datetime
  end_date: datetime
  group_by: str = "day"  # day, week, month, product, category
  include_details: bool = False
  pharmacy_branch_id: Optional[int] = None


class InventoryReportRequest(BaseModel):
  report_type: str = "stock_levels"  # stock_levels, expiry, turnover, valuation
  category: Optional[str] = None
  warehouse_id: Optional[int] = None
  include_zero_stock: bool = False


class FinancialReportRequest(BaseModel):
  report_type: str = "profit_loss"  # profit_loss, cash_flow, balance_sheet
  start_date: datetime
  end_date: datetime
  include_comparison: bool = False


class CustomerReportRequest(BaseModel):
  report_type: str = "segmentation"  # segmentation, retention, acquisition
  start_date: Optional[datetime] = None
  end_date: Optional[datetime] = None
  customer_type: Optional[str] = None


class ReportStats(BaseModel):
  total_reports: int
  reports_by_type: Dict[str, int]
  scheduled_reports: int
  recent_reports: List[Dict[str, Any]]


class DashboardBase(BaseModel):
  name: str
  description: Optional[str] = None
  layout: Dict[str, Any]
  widgets: List[Dict[str, Any]]
  is_public: bool = False
  allowed_roles: Optional[List[str]] = None
  allowed_users: Optional[List[int]] = None


class DashboardCreate(DashboardBase):
  pass


class DashboardResponse(DashboardBase):
  id: int
  created_by: int
  owner_name: Optional[str] = None
  created_at: datetime
  updated_at: Optional[datetime] = None

  class Config:
    from_attributes = True


class WidgetBase(BaseModel):
  widget_type: str
  title: str
  config: Dict[str, Any]
  data_source: str
  refresh_interval: Optional[int] = None
  width: int = 4
  height: int = 300
  filters: Optional[Dict[str, Any]] = None


class WidgetCreate(WidgetBase):
  pass


class WidgetResponse(WidgetBase):
  id: int
  created_at: datetime
  updated_at: Optional[datetime] = None

  class Config:
    from_attributes = True


class AuditLogResponse(BaseModel):
  id: int
  action: str
  entity_type: str
  entity_id: Optional[int] = None
  old_values: Optional[Dict[str, Any]] = None
  new_values: Optional[Dict[str, Any]] = None
  user_id: Optional[int] = None
  user_name: Optional[str] = None
  user_ip: Optional[str] = None
  status: str
  error_message: Optional[str] = None
  created_at: datetime

  class Config:
    from_attributes = True