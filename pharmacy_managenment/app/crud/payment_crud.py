from sqlalchemy.orm import Session
from typing import Optional, List, Any
from app.models.payment import Payment
from app.schemas.payment import PaymentCreate, PaymentUpdate

def get_payment(db: Session, payment_id: int) -> Optional[Payment]:
    return db.query(Payment).filter(payment_id == Payment.id).first()

def get_payment_by_reference(db: Session, reference: str) -> Optional[Payment]:
    return db.query(Payment).filter(reference == Payment.payment_reference).first()

def get_payments(db: Session, skip: int = 0, limit: int = 100) -> list[type[Payment]]:
    return db.query(Payment).offset(skip).limit(limit).all()

def create_payment(db: Session, payment: PaymentCreate) -> Payment:
    db_payment = Payment(**payment.dict())
    db.add(db_payment)
    db.commit()
    db.refresh(db_payment)
    return db_payment

def update_payment(db: Session, payment_id: int, payment_update: PaymentUpdate) -> Optional[Payment]:
    db_payment = get_payment(db, payment_id)
    if not db_payment:
        return None
    update_data = payment_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_payment, field, value)
    db.commit()
    db.refresh(db_payment)
    return db_payment