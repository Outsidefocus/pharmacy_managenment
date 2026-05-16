from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta

from app.database import get_db
from app.models.payment import Payment, PaymentMethod, PaymentStatus, Invoice
from app.models.order import Order, OrderStatus
from app.schemas.payment import (
  PaymentCreate, PaymentUpdate, PaymentResponse,
  InvoiceCreate, InvoiceResponse, PaymentStats
)
from app.utils.security import get_current_user, require_permission
from app.schemas.user import User
from app.services.payment_service import PaymentService
from app.services.notification_service import NotificationService
from app.utils.helpers import generate_payment_reference, generate_invoice_number

router = APIRouter()
payment_service = PaymentService()


@router.get("/", response_model=List[PaymentResponse])
async def read_payments(
    skip: int = 0,
    limit: int = 100,
    payment_method: Optional[PaymentMethod] = None,
    payment_status: Optional[PaymentStatus] = None,
    customer_id: Optional[int] = None,
    order_id: Optional[int] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
  """Get all payments with filters"""
  query = db.query(Payment)

  if payment_method:
    query = query.filter(Payment.payment_method == payment_method)
  if payment_status:
    query = query.filter(Payment.payment_status == payment_status)
  if customer_id:
    query = query.filter(Payment.customer_id == customer_id)
  if order_id:
    query = query.filter(Payment.order_id == order_id)
  if start_date:
    query = query.filter(Payment.payment_date >= start_date)
  if end_date:
    query = query.filter(Payment.payment_date <= end_date)

  payments = query.order_by(Payment.payment_date.desc()).offset(skip).limit(limit).all()
  return payments


@router.get("/{payment_id}", response_model=PaymentResponse)
async def read_payment(
    payment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
  """Get payment by ID"""
  payment = db.query(Payment).filter(Payment.id == payment_id).first()
  if not payment:
    raise HTTPException(status_code=404, detail="Payment not found")
  return payment


@router.post("/", response_model=PaymentResponse)
async def create_payment(
    payment: PaymentCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("process_payments"))
):
  """Create new payment"""
  # Validate order if provided
  if payment.order_id:
    order = db.query(Order).filter(Order.id == payment.order_id).first()
    if not order:
      raise HTTPException(status_code=404, detail="Order not found")
    # Check if payment exceeds due amount
    total_paid = db.query(Payment).filter(
      Payment.order_id == payment.order_id,
      Payment.payment_status == PaymentStatus.COMPLETED
    ).with_entities(Payment.amount).all()
    paid_sum = sum(p.amount for p in total_paid) if total_paid else 0
    remaining = order.total_amount - paid_sum
    if payment.amount > remaining:
      raise HTTPException(status_code=400, detail="Payment amount exceeds remaining balance")

  # Generate reference
  payment_reference = generate_payment_reference(db)

  # Create payment record
  db_payment = Payment(
    payment_reference=payment_reference,
    collected_by=current_user.id,
    **payment.dict()
  )
  db.add(db_payment)
  db.commit()
  db.refresh(db_payment)

  # Process payment (if not manual)
  if payment.payment_method not in [PaymentMethod.CASH, PaymentMethod.CHEQUE]:
    background_tasks.add_task(payment_service.process_payment, db_payment.id)

  # Update order payment status if fully paid
  if payment.order_id:
    order = db.query(Order).filter(Order.id == payment.order_id).first()
    if order:
      total_paid = db.query(Payment).filter(
        Payment.order_id == order.id,
        Payment.payment_status == PaymentStatus.COMPLETED
      ).with_entities(Payment.amount).all()
      paid_sum = sum(p.amount for p in total_paid) if total_paid else 0
      if paid_sum >= order.total_amount:
        order.payment_status = "paid"
        order.amount_paid = order.total_amount
        order.amount_due = 0
        db.commit()

  return db_payment


@router.put("/{payment_id}", response_model=PaymentResponse)
async def update_payment(
    payment_id: int,
    payment_update: PaymentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("manage_payments"))
):
  """Update payment (e.g., mark as verified)"""
  payment = db.query(Payment).filter(Payment.id == payment_id).first()
  if not payment:
    raise HTTPException(status_code=404, detail="Payment not found")

  update_data = payment_update.dict(exclude_unset=True)
  for field, value in update_data.items():
    setattr(payment, field, value)

  if 'is_verified' in update_data and update_data['is_verified']:
    payment.verified_by = current_user.id
    payment.verification_date = datetime.now()

  db.commit()
  db.refresh(payment)

  # If payment is now completed and order exists, update order status
  if payment.payment_status == PaymentStatus.COMPLETED and payment.order_id:
    order = db.query(Order).filter(Order.id == payment.order_id).first()
    if order:
      total_paid = db.query(Payment).filter(
        Payment.order_id == order.id,
        Payment.payment_status == PaymentStatus.COMPLETED
      ).with_entities(Payment.amount).all()
      paid_sum = sum(p.amount for p in total_paid) if total_paid else 0
      if paid_sum >= order.total_amount:
        order.payment_status = "paid"
        order.amount_paid = order.total_amount
        order.amount_due = 0
        db.commit()

  return payment


@router.post("/{payment_id}/refund")
async def refund_payment(
    payment_id: int,
    amount: Optional[float] = None,
    reason: str = "Customer request",
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("process_refunds"))
):
  """Process refund for a payment"""
  payment = db.query(Payment).filter(Payment.id == payment_id).first()
  if not payment:
    raise HTTPException(status_code=404, detail="Payment not found")

  refund_amount = amount if amount else payment.amount

  if refund_amount > payment.amount:
    raise HTTPException(status_code=400, detail="Refund amount exceeds payment amount")

  # Create refund record
  refund_reference = generate_payment_reference(db)
  refund = Payment(
    payment_reference=refund_reference,
    order_id=payment.order_id,
    customer_id=payment.customer_id,
    payment_method=payment.payment_method,
    amount=-refund_amount,  # Negative amount for refund
    payment_status=PaymentStatus.COMPLETED,
    is_refund=True,
    original_payment_id=payment.id,
    refund_reason=reason,
    collected_by=current_user.id
  )
  db.add(refund)

  # Update original payment status
  if refund_amount >= payment.amount:
    payment.payment_status = PaymentStatus.REFUNDED
  else:
    payment.payment_status = PaymentStatus.PARTIALLY_REFUNDED

  db.commit()
  db.refresh(refund)

  return {"message": "Refund processed", "refund_id": refund.id}


@router.get("/stats/overview", response_model=PaymentStats)
async def get_payment_stats(
    period: str = Query("today", description="today, week, month"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
  """Get payment statistics"""
  from sqlalchemy import func

  now = datetime.now()
  if period == "today":
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
  elif period == "week":
    start = now - timedelta(days=now.weekday())
    start = start.replace(hour=0, minute=0, second=0, microsecond=0)
  elif period == "month":
    start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
  else:
    start = now - timedelta(days=30)

  # Total payments and amount
  stats = db.query(
    func.count(Payment.id).label("total_payments"),
    func.sum(Payment.amount).label("total_amount"),
    func.avg(Payment.amount).label("avg_payment")
  ).filter(
    Payment.payment_date >= start,
    Payment.payment_status == PaymentStatus.COMPLETED,
    Payment.is_refund == False
  ).first()

  # By method
  method_totals = db.query(
    Payment.payment_method,
    func.sum(Payment.amount).label("amount"),
    func.count(Payment.id).label("count")
  ).filter(
    Payment.payment_date >= start,
    Payment.payment_status == PaymentStatus.COMPLETED,
    Payment.is_refund == False
  ).group_by(Payment.payment_method).all()

  payments_by_method = {m[0].value if m[0] else "unknown": float(m[1] or 0) for m in method_totals}

  # Outstanding invoices
  invoices_outstanding = db.query(func.count(Invoice.id)).filter(
    Invoice.status.in_(["pending", "partially_paid"]),
    Invoice.due_date < now
  ).scalar() or 0

  outstanding_amount = db.query(func.sum(Invoice.amount_due)).filter(
    Invoice.status.in_(["pending", "partially_paid"])
  ).scalar() or 0

  # Today's payments
  today_payments = db.query(func.count(Payment.id)).filter(
    func.date(Payment.payment_date) == now.date(),
    Payment.payment_status == PaymentStatus.COMPLETED,
    Payment.is_refund == False
  ).scalar() or 0

  today_amount = db.query(func.sum(Payment.amount)).filter(
    func.date(Payment.payment_date) == now.date(),
    Payment.payment_status == PaymentStatus.COMPLETED,
    Payment.is_refund == False
  ).scalar() or 0

  return PaymentStats(
    total_payments=stats.total_payments or 0,
    total_amount=float(stats.total_amount or 0),
    average_payment=float(stats.avg_payment or 0),
    payments_by_method=payments_by_method,
    payments_by_status={},  # Could add if needed
    today_payments=today_payments,
    today_amount=float(today_amount),
    outstanding_invoices=invoices_outstanding,
    outstanding_amount=float(outstanding_amount)
  )


@router.post("/invoices", response_model=InvoiceResponse)
async def create_invoice(
    invoice: InvoiceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("manage_invoices"))
):
  """Create new invoice"""
  # Validate order
  order = db.query(Order).filter(Order.id == invoice.order_id).first()
  if not order:
    raise HTTPException(status_code=404, detail="Order not found")

  # Check if invoice already exists
  existing = db.query(Invoice).filter(Invoice.order_id == invoice.order_id).first()
  if existing:
    raise HTTPException(status_code=400, detail="Invoice already exists for this order")

  invoice_number = generate_invoice_number(db)

  db_invoice = Invoice(
    invoice_number=invoice_number,
    subtotal=order.subtotal,
    tax_amount=order.tax_amount,
    discount_amount=order.discount_amount,
    total_amount=order.total_amount,
    amount_paid=order.amount_paid,
    amount_due=order.amount_due,
    **invoice.dict()
  )
  db.add(db_invoice)
  db.commit()
  db.refresh(db_invoice)

  return db_invoice


@router.get("/invoices/{invoice_id}", response_model=InvoiceResponse)
async def read_invoice(
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
  """Get invoice by ID"""
  invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
  if not invoice:
    raise HTTPException(status_code=404, detail="Invoice not found")
  return invoice