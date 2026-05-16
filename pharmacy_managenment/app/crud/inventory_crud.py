from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta

from app.models.inventory import InventoryItem, StockMovement, Warehouse
from app.models.product import Product, ProductBatch
from app.schemas.inventory import InventoryItemCreate, InventoryItemUpdate, StockMovementCreate


def get_inventory_items(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    category: Optional[str] = None,
    low_stock: Optional[bool] = None,
    expired: Optional[bool] = None,
    warehouse_id: Optional[int] = None
) -> list[type[InventoryItem]]:
  """Get inventory items with filters"""
  query = db.query(InventoryItem)

  if category:
    query = query.join(InventoryItem.product).filter(category == Product.category)

  if low_stock:
    query = query.join(InventoryItem.product).filter(
      InventoryItem.quantity <= Product.min_stock_level
    )

  if warehouse_id:
    query = query.filter(warehouse_id == InventoryItem.warehouse_id)

  # Expired filter would require joining batches
  if expired:
    query = query.join(InventoryItem.batch).filter(
      ProductBatch.expiry_date < datetime.now()
    )

  return query.offset(skip).limit(limit).all()


def get_inventory_item(db: Session, item_id: int) -> Optional[InventoryItem]:
  return db.query(InventoryItem).filter(item_id == InventoryItem.id).first()


def create_inventory_item(db: Session, item: InventoryItemCreate) -> InventoryItem:
  db_item = InventoryItem(**item.dict())
  db.add(db_item)
  db.commit()
  db.refresh(db_item)
  return db_item


def update_inventory_item(db: Session, item_id: int, item_update: InventoryItemUpdate) -> Optional[InventoryItem]:
  db_item = get_inventory_item(db, item_id)
  if not db_item:
    return None
  update_data = item_update.dict(exclude_unset=True)
  for field, value in update_data.items():
    setattr(db_item, field, value)
  db.commit()
  db.refresh(db_item)
  return db_item


def delete_inventory_item(db: Session, item_id: int) -> bool:
  db_item = get_inventory_item(db, item_id)
  if not db_item:
    return False
  db.delete(db_item)
  db.commit()
  return True


def create_stock_movement(db: Session, movement: StockMovementCreate) -> StockMovement:
  # Get current quantity
  inv_item = db.query(InventoryItem).filter(movement.inventory_item_id == InventoryItem.id).first()
  previous_quantity = inv_item.quantity if inv_item else 0

  # Calculate new quantity based on movement type
  if movement.movement_type in ["purchase", "return"]:
    new_quantity = previous_quantity + movement.quantity
  elif movement.movement_type in ["sale", "damage", "expired"]:
    new_quantity = previous_quantity - movement.quantity
  else:
    new_quantity = previous_quantity  # adjustment

  # Update inventory item
  if inv_item:
    inv_item.quantity = new_quantity

  db_movement = StockMovement(
    previous_quantity=previous_quantity,
    new_quantity=new_quantity,
    **movement.dict()
  )
  db.add(db_movement)
  db.commit()
  db.refresh(db_movement)
  return db_movement