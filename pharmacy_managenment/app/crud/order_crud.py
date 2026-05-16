from sqlalchemy.orm import Session
from typing import Optional, List, Any
from app.models.order import Order
from app.schemas.order import OrderCreate, OrderUpdate

def get_order(db: Session, order_id: int) -> Optional[Order]:
    return db.query(Order).filter(order_id == Order.id).first()

def get_order_by_number(db: Session, order_number: str) -> Optional[Order]:
    return db.query(Order).filter(order_number == Order.order_number).first()

def get_orders(db: Session, skip: int = 0, limit: int = 100) -> list[type[Order]]:
    return db.query(Order).offset(skip).limit(limit).all()

def create_order(db: Session, order: OrderCreate) -> Order:
    db_order = Order(**order.dict())
    db.add(db_order)
    db.commit()
    db.refresh(db_order)
    return db_order

def update_order(db: Session, order_id: int, order_update: OrderUpdate) -> Optional[Order]:
    db_order = get_order(db, order_id)
    if not db_order:
        return None
    update_data = order_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_order, field, value)
    db.commit()
    db.refresh(db_order)
    return db_order

def delete_order(db: Session, order_id: int) -> bool:
    db_order = get_order(db, order_id)
    if not db_order:
        return False
    db.delete(db_order)
    db.commit()
    return True