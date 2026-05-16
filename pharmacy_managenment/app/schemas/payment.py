from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class PaymentMethod(str, Enum):
  CASH = "cash"
  CREDIT_CARD = "credit_card"
  DEBIT_CARD = "debit_card"
  BANK_TRANSFER = "bank_transfer"
  MOBILE_MONEY = "mobile_money"
  CHEQUE = "cheque"
  INSURANCE = "insurance"
  LOYALTY_POINTS = "loyalty_points"
  ONLINE = "online"


class PaymentStatus(str, Enum):
  PENDING = "pending"
  COMPLETED = "completed"
  FAILED = "failed"
  REFUNDED = "refunded"
  PARTIALLY_REFUNDED = "partially_refunded"


class PaymentBase(BaseModel):
  order_id: Optional[int] = None
  invoice_id: Optional[int] = None
  customer_id: Optional[int] = None
  payment_method: PaymentMethod
  amount: float
  currency: str = "USD"
  gateway_reference: Optional[str] = None
  gateway_name: Optional[str] = None
  card_last_four: Optional[str] = None
  card_type: Optional[str] = None
  bank_name: Optional[str] = None
  account_number: Optional[str] = None
  transaction_id: Optional[str] = None
  cheque_number: Optional[str] = None
  cheque_date: Optional[datetime] = None
  insurance_provider: Optional[str] = None
  insurance_policy: Optional[str] = None
  claim_number: Optional[str] = None
  notes: Optional[str] = None


class PaymentCreate(PaymentBase):
  pass


class PaymentUpdate(BaseModel):
  payment_status: Optional[PaymentStatus] = None
  is_verified: Optional[bool] = None
  verification_notes: Optional[str] = None
  processed_date: Optional[datetime] = None


class PaymentResponse(PaymentBase):
  id: int
  payment_reference: str
  payment_status: PaymentStatus
  transaction_fee: float
  net_amount: float
  customer_name: Optional[str] = None
  order_number: Optional[str] = None
  invoice_number: Optional[str] = None
  is_verified: bool
  collected_by: Optional[int] = None
  collector_name: Optional[str] = None
  verified_by: Optional[int] = None
  verifier_name: Optional[str] = None
  is_refund: bool
  original_payment_id: Optional[int] = None
  payment_date: datetime
  processed_date: Optional[datetime] = None
  refund_date: Optional[datetime] = None
  created_at: datetime
  updated_at: Optional[datetime] = None

  class Config:
    from_attributes = True


class InvoiceBase(BaseModel):
  order_id: int
  customer_id: int
  due_date: datetime
  payment_terms: Optional[str] = None
  late_fee_percentage: Optional[float] = 0.0
  billing_address: Optional[str] = None
  billing_email: Optional[str] = None
  notes: Optional[str] = None
  terms_and_conditions: Optional[str] = None


class InvoiceCreate(InvoiceBase):
  pass


class InvoiceResponse(InvoiceBase):
  id: int
  invoice_number: str
  invoice_date: datetime
  subtotal: float
  tax_amount: float
  discount_amount: float
  total_amount: float
  amount_paid: float
  amount_due: float
  status: str
  is_overdue: bool
  late_fee_amount: float
  customer_name: Optional[str] = None
  order_number: Optional[str] = None
  sent_date: Optional[datetime] = None
  paid_date: Optional[datetime] = None
  cancelled_date: Optional[datetime] = None
  created_at: datetime
  updated_at: Optional[datetime] = None

  class Config:
    from_attributes = True


class PaymentStats(BaseModel):
  total_payments: int
  total_amount: float
  average_payment: float
  payments_by_method: Dict[str, float]
  payments_by_status: Dict[str, int]
  today_payments: int
  today_amount: float
  outstanding_invoices: int
  outstanding_amount: float


class ExpenseBase(BaseModel):
  category: str
  description: str
  amount: float
  currency: str = "USD"
  vendor_name: Optional[str] = None
  vendor_contact: Optional[str] = None
  payment_method: Optional[str] = None
  receipt_number: Optional[str] = None
  department: Optional[str] = None
  project_code: Optional[str] = None
  is_tax_deductible: bool = True
  tax_amount: float = 0.0


class ExpenseCreate(ExpenseBase):
  pass


class ExpenseResponse(ExpenseBase):
  id: int
  expense_number: str
  payment_status: str
  approved_by: Optional[int] = None
  approver_name: Optional[str] = None
  approval_date: Optional[datetime] = None
  is_recurring: bool
  recurrence_pattern: Optional[str] = None
  next_due_date: Optional[datetime] = None
  paid_date: Optional[datetime] = None
  created_at: datetime
  updated_at: Optional[datetime] = None

  class Config:
    from_attributes = True