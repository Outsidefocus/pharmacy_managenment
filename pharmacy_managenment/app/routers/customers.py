from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta

from app.database import get_db
from app.models.customer import Customer, Prescription, PrescriptionItem
from app.schemas.customer import (
  CustomerCreate, CustomerUpdate, CustomerResponse,
  PrescriptionCreate, PrescriptionResponse,
  PrescriptionItemCreate, PrescriptionItemResponse,
  CustomerStats
)
from app.utils.security import get_current_user, require_permission
from app.schemas.user import User

router = APIRouter()


@router.get("/", response_model=List[CustomerResponse])
async def read_customers(
    skip: int = 0,
    limit: int = 100,
    customer_type: Optional[str] = None,
    search: Optional[str] = None,
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
  """Get all customers"""
  query = db.query(Customer)

  if customer_type:
    query = query.filter(customer_type == Customer.customer_type)

  if is_active is not None:
    query = query.filter(Customer.is_active == is_active)

  if search:
    from sqlalchemy import or_
    query = query.filter(
      or_(
        Customer.first_name.ilike(f"%{search}%"),
        Customer.last_name.ilike(f"%{search}%"),
        Customer.email.ilike(f"%{search}%"),
        Customer.phone.ilike(f"%{search}%"),
        Customer.customer_code.ilike(f"%{search}%")
      )
    )

  customers = query.offset(skip).limit(limit).all()
  return customers


@router.get("/{customer_id}", response_model=CustomerResponse)
async def read_customer(
    customer_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
  """Get customer by ID"""
  customer = db.query(Customer).filter(Customer.id == customer_id).first()
  if not customer:
    raise HTTPException(status_code=404, detail="Customer not found")
  return customer


@router.post("/", response_model=CustomerResponse)
async def create_customer(
    customer: CustomerCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("manage_customers"))
):
  """Create new customer"""
  # Check if email already exists
  if customer.email:
    existing_customer = db.query(Customer).filter(Customer.email == customer.email).first()
    if existing_customer:
      raise HTTPException(
        status_code=400,
        detail="Customer with this email already exists"
      )

  # Generate customer code
  from app.utils.helpers import generate_customer_code
  customer_code = generate_customer_code(db)

  db_customer = Customer(
    customer_code=customer_code,
    **customer.dict()
  )

  db.add(db_customer)
  db.commit()
  db.refresh(db_customer)

  return db_customer


@router.put("/{customer_id}", response_model=CustomerResponse)
async def update_customer(
    customer_id: int,
    customer_update: CustomerUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("manage_customers"))
):
  """Update customer"""
  db_customer = db.query(Customer).filter(Customer.id == customer_id).first()
  if not db_customer:
    raise HTTPException(status_code=404, detail="Customer not found")

  update_data = customer_update.dict(exclude_unset=True)

  # Check if email already exists (if being updated)
  if 'email' in update_data and update_data['email'] != db_customer.email:
    existing_customer = db.query(Customer).filter(
      Customer.email == update_data['email'],
      Customer.id != customer_id
    ).first()
    if existing_customer:
      raise HTTPException(
        status_code=400,
        detail="Customer with this email already exists"
      )

  for field, value in update_data.items():
    setattr(db_customer, field, value)

  db.commit()
  db.refresh(db_customer)

  return db_customer


@router.delete("/{customer_id}")
async def delete_customer(
    customer_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("manage_customers"))
):
  """Delete customer (soft delete)"""
  db_customer = db.query(Customer).filter(Customer.id == customer_id).first()
  if not db_customer:
    raise HTTPException(status_code=404, detail="Customer not found")

  db_customer.is_active = False
  db.commit()

  return {"message": "Customer deactivated successfully"}


@router.get("/{customer_id}/prescriptions", response_model=List[PrescriptionResponse])
async def get_customer_prescriptions(
    customer_id: int,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
  """Get customer prescriptions"""
  query = db.query(Prescription).filter(Prescription.customer_id == customer_id)

  if status:
    query = query.filter(Prescription.status == status)

  prescriptions = query.order_by(Prescription.issue_date.desc()).all()
  return prescriptions


@router.post("/{customer_id}/prescriptions", response_model=PrescriptionResponse)
async def create_prescription(
    customer_id: int,
    prescription: PrescriptionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("manage_prescriptions"))
):
  """Create new prescription for customer"""
  # Verify customer exists
  customer = db.query(Customer).filter(Customer.id == customer_id).first()
  if not customer:
    raise HTTPException(status_code=404, detail="Customer not found")

  # Generate prescription number
  from app.utils.helpers import generate_prescription_number
  prescription_number = generate_prescription_number(db)

  db_prescription = Prescription(
    prescription_number=prescription_number,
    customer_id=customer_id,
    **prescription.dict()
  )

  db.add(db_prescription)
  db.commit()
  db.refresh(db_prescription)

  return db_prescription


@router.post("/prescriptions/{prescription_id}/items", response_model=PrescriptionItemResponse)
async def add_prescription_item(
    prescription_id: int,
    item: PrescriptionItemCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("manage_prescriptions"))
):
  """Add item to prescription"""
  # Verify prescription exists
  prescription = db.query(Prescription).filter(Prescription.id == prescription_id).first()
  if not prescription:
    raise HTTPException(status_code=404, detail="Prescription not found")

  # Verify product exists
  from app.models.product import Product
  product = db.query(Product).filter(Product.id == item.product_id).first()
  if not product:
    raise HTTPException(status_code=404, detail="Product not found")

  db_item = PrescriptionItem(
    prescription_id=prescription_id,
    **item.dict()
  )

  db.add(db_item)
  db.commit()
  db.refresh(db_item)

  return db_item


@router.put("/prescriptions/{prescription_id}/verify")
async def verify_prescription(
    prescription_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("verify_prescription"))
):
  """Verify prescription"""
  prescription = db.query(Prescription).filter(Prescription.id == prescription_id).first()
  if not prescription:
    raise HTTPException(status_code=404, detail="Prescription not found")

  prescription.status = "verified"
  prescription.verification_date = datetime.now()
  prescription.verified_by = current_user.id

  db.commit()

  return {"message": "Prescription verified successfully"}


@router.get("/stats/overview", response_model=CustomerStats)
async def get_customer_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
  """Get customer statistics"""
  from sqlalchemy import func, case

  total_customers = db.query(func.count(Customer.id)).scalar()
  active_customers = db.query(func.count(Customer.id)).filter(Customer.is_active == True).scalar()

  # New customers today
  today = datetime.now().date()
  new_customers_today = db.query(func.count(Customer.id)).filter(
    func.date(Customer.registration_date) == today
  ).scalar()

  # New customers this week
  week_start = today - timedelta(days=today.weekday())
  new_customers_week = db.query(func.count(Customer.id)).filter(
    func.date(Customer.registration_date) >= week_start
  ).scalar()

  # Customers by type
  customers_by_type = {}
  types = db.query(Customer.customer_type, func.count(Customer.id)).group_by(Customer.customer_type).all()
  for type_name, count in types:
    customers_by_type[type_name] = count

  # Average order value
  avg_order_value = db.query(func.avg(Customer.average_order_value)).scalar() or 0

  # Top customers by total spent
  top_customers = db.query(
    Customer.id,
    Customer.first_name,
    Customer.last_name,
    Customer.total_spent,
    Customer.total_orders
  ).order_by(Customer.total_spent.desc()).limit(10).all()

  top_customers_list = [
    {
      "id": cust.id,
      "name": f"{cust.first_name} {cust.last_name}",
      "total_spent": cust.total_spent,
      "total_orders": cust.total_orders
    } for cust in top_customers
  ]

  return CustomerStats(
    total_customers=total_customers,
    active_customers=active_customers,
    new_customers_today=new_customers_today,
    new_customers_this_week=new_customers_week,
    customers_by_type=customers_by_type,
    average_order_value=float(avg_order_value),
    top_customers=top_customers_list
  )


@router.get("/{customer_id}/orders")
async def get_customer_orders(
    customer_id: int,
    status: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
  """Get customer's orders"""
  from app.models.order import Order

  query = db.query(Order).filter(Order.customer_id == customer_id)

  if status:
    query = query.filter(Order.status == status)

  orders = query.order_by(Order.order_date.desc()).limit(limit).all()

  return orders


@router.get("/{customer_id}/history")
async def get_customer_history(
    customer_id: int,
    days: int = Query(90, description="Number of days of history"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
  """Get customer purchase history"""
  from app.models.order import Order, OrderItem
  from sqlalchemy import func

  start_date = datetime.now() - timedelta(days=days)

  # Purchase history
  purchases = db.query(
    Order.id,
    Order.order_number,
    Order.order_date,
    Order.status,
    Order.total_amount,
    func.count(OrderItem.id).label("item_count")
  ).join(OrderItem).filter(
    Order.customer_id == customer_id,
    Order.order_date >= start_date
  ).group_by(Order.id).order_by(Order.order_date.desc()).all()

  # Prescription history
  prescriptions = db.query(Prescription).filter(
    Prescription.customer_id == customer_id,
    Prescription.issue_date >= start_date
  ).order_by(Prescription.issue_date.desc()).all()

  # Payment history
  from app.models.payment import Payment
  payments = db.query(Payment).filter(
    Payment.customer_id == customer_id,
    Payment.payment_date >= start_date
  ).order_by(Payment.payment_date.desc()).all()

  return {
    "purchases": [
      {
        "order_id": p.id,
        "order_number": p.order_number,
        "order_date": p.order_date,
        "status": p.status,
        "total_amount": p.total_amount,
        "item_count": p.item_count
      } for p in purchases
    ],
    "prescriptions": prescriptions,
    "payments": [
      {
        "id": p.id,
        "amount": p.amount,
        "payment_date": p.payment_date,
        "status": p.payment_status
      } for p in payments
    ]
  }