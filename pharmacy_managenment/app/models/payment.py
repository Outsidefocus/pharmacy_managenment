from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, ForeignKey, Enum, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from sqlalchemy.sql import func
from app.database import Base
import enum


class PaymentMethod(enum.Enum):
  CASH = "cash"
  CREDIT_CARD = "credit_card"
  DEBIT_CARD = "debit_card"
  BANK_TRANSFER = "bank_transfer"
  MOBILE_MONEY = "mobile_money"
  CHEQUE = "cheque"
  INSURANCE = "insurance"
  LOYALTY_POINTS = "loyalty_points"
  ONLINE = "online"


class PaymentStatus(enum.Enum):
  PENDING = "pending"
  COMPLETED = "completed"
  FAILED = "failed"
  REFUNDED = "refunded"
  PARTIALLY_REFUNDED = "partially_refunded"


class Payment(Base):
  __tablename__ = "payments"

  id = Column(Integer, primary_key=True, index=True)
  payment_reference = Column(String(100), unique=True, index=True)

  # Order/Invoice Reference
  order_id = Column(Integer, ForeignKey("orders.id"))
  invoice_id = Column(Integer, ForeignKey("invoices.id"))

  # Customer Information
  customer_id = Column(Integer, ForeignKey("customers.id"))
  customer_name = Column(String(200))

  # Payment Details
  payment_method = Column(Enum(PaymentMethod), nullable=False)
  payment_status = Column(Enum(PaymentStatus), default=PaymentStatus.PENDING)

  # Amounts
  amount = Column(Float, nullable=False)
  currency = Column(String(10), default="USD")
  transaction_fee = Column(Float, default=0.0)
  net_amount = Column(Float, nullable=False)

  # Payment Gateway Details
  gateway_reference = Column(String(200))
  gateway_response = Column(JSON)
  gateway_name = Column(String(100))  # e.g., "Stripe", "PayPal"

  # Card Details (encrypted or masked)
  card_last_four = Column(String(4))
  card_type = Column(String(50))
  card_expiry = Column(String(10))

  # Bank Transfer Details
  bank_name = Column(String(100))
  account_number = Column(String(50))
  transaction_id = Column(String(100))

  # Cheque Details
  cheque_number = Column(String(100))
  cheque_date = Column(DateTime)
  bank_name_cheque = Column(String(100))

  # Insurance Details
  insurance_provider = Column(String(200))
  insurance_policy = Column(String(100))
  claim_number = Column(String(100))
  insurance_amount = Column(Float, default=0.0)
  patient_amount = Column(Float, default=0.0)

  # Dates
  payment_date = Column(DateTime(timezone=True), server_default=func.now())
  processed_date = Column(DateTime(timezone=True))
  refund_date = Column(DateTime(timezone=True))

  # User Information
  collected_by = Column(Integer, ForeignKey("users.id"))
  verified_by = Column(Integer, ForeignKey("users.id"))

  # Status and Notes
  is_verified = Column(Boolean, default=False)
  verification_notes = Column(Text)
  notes = Column(Text)

  # Refund Information
  is_refund = Column(Boolean, default=False)
  original_payment_id = Column(Integer, ForeignKey("payments.id"))
  refund_reason = Column(Text)

  created_at = Column(DateTime(timezone=True), server_default=func.now())
  updated_at = Column(DateTime(timezone=True), onupdate=func.now())

  # Relationships
  order = relationship("Order", back_populates="payments")
  customer = relationship("Customer", back_populates="payments")
  invoice = relationship("Invoice")
  collector = relationship("User", foreign_keys=[collected_by])
  verifier = relationship("User", foreign_keys=[verified_by])
  original_payment = relationship("Payment", remote_side=[id])
  refunds = relationship("Payment", back_populates="original_payment")


class Invoice(Base):
  __tablename__ = "invoices"

  id = Column(Integer, primary_key=True, index=True)
  invoice_number = Column(String(100), unique=True, index=True)

  # References
  order_id = Column(Integer, ForeignKey("orders.id"))
  customer_id = Column(Integer, ForeignKey("customers.id"))

  # Invoice Details
  invoice_date = Column(DateTime(timezone=True), server_default=func.now())
  due_date = Column(DateTime(timezone=True))

  # Amounts
  subtotal = Column(Float, default=0.0)
  tax_amount = Column(Float, default=0.0)
  discount_amount = Column(Float, default=0.0)
  total_amount = Column(Float, default=0.0)
  amount_paid = Column(Float, default=0.0)
  amount_due = Column(Float, default=0.0)

  # Status
  status = Column(String(50), default="pending")  # pending, partially_paid, paid, overdue, cancelled
  is_overdue = Column(Boolean, default=False)

  # Payment Terms
  payment_terms = Column(String(200))
  late_fee_percentage = Column(Float, default=0.0)
  late_fee_amount = Column(Float, default=0.0)

  # Billing Information
  billing_address = Column(Text)
  billing_email = Column(String(100))

  # Notes
  notes = Column(Text)
  terms_and_conditions = Column(Text)

  # Dates
  sent_date = Column(DateTime(timezone=True))
  paid_date = Column(DateTime(timezone=True))
  cancelled_date = Column(DateTime(timezone=True))

  created_at = Column(DateTime(timezone=True), server_default=func.now())
  updated_at = Column(DateTime(timezone=True), onupdate=func.now())

  # Relationships
  order = relationship("Order")
  customer = relationship("Customer")
  payments = relationship("Payment", back_populates="invoice")

  def calculate_due_amount(self):
    """Calculate due amount and update status"""
    self.amount_due = self.total_amount - self.amount_paid

    if self.amount_due <= 0:
      self.status = "paid"
    elif self.amount_paid > 0:
      self.status = "partially_paid"

    # Check if overdue
    if self.due_date and datetime.now() > self.due_date and self.amount_due > 0:
      self.is_overdue = True
      if self.late_fee_percentage > 0:
        self.late_fee_amount = self.amount_due * (self.late_fee_percentage / 100)
        self.total_amount += self.late_fee_amount
        self.amount_due += self.late_fee_amount


class Expense(Base):
  __tablename__ = "expenses"

  id = Column(Integer, primary_key=True, index=True)
  expense_number = Column(String(100), unique=True, index=True)

  # Expense Details
  category = Column(String(100))  # Rent, Utilities, Salary, Supplies, etc.
  description = Column(Text, nullable=False)
  amount = Column(Float, nullable=False)
  currency = Column(String(10), default="USD")

  # Vendor Information
  vendor_name = Column(String(200))
  vendor_contact = Column(String(200))

  # Payment Information
  payment_method = Column(String(50))
  payment_status = Column(String(50), default="pending")
  paid_date = Column(DateTime(timezone=True))

  # Receipt/Invoice
  receipt_number = Column(String(100))
  receipt_image_url = Column(String(500))

  # Approval
  approved_by = Column(Integer, ForeignKey("users.id"))
  approval_date = Column(DateTime(timezone=True))

  # Recurring Expense
  is_recurring = Column(Boolean, default=False)
  recurrence_pattern = Column(String(50))  # daily, weekly, monthly, yearly
  next_due_date = Column(DateTime(timezone=True))

  # Department/Project
  department = Column(String(100))
  project_code = Column(String(100))

  # Status
  is_tax_deductible = Column(Boolean, default=True)
  tax_amount = Column(Float, default=0.0)

  created_at = Column(DateTime(timezone=True), server_default=func.now())
  updated_at = Column(DateTime(timezone=True), onupdate=func.now())

  # Relationships
  approver = relationship("User", foreign_keys=[approved_by])