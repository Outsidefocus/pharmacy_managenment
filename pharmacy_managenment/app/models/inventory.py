from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey, Enum, Text, ColumnElement
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
import enum


class StockMovementType(enum.Enum):
  PURCHASE = "purchase"
  SALE = "sale"
  RETURN = "return"
  ADJUSTMENT = "adjustment"
  TRANSFER = "transfer"
  DAMAGE = "damage"
  EXPIRED = "expired"


class InventoryItem(Base):
  __tablename__ = "inventory_items"

  id = Column(Integer, primary_key=True, index=True)
  product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
  batch_id = Column(Integer, ForeignKey("product_batches.id"))
  quantity = Column(Integer, nullable=False, default=0)
  reserved_quantity = Column(Integer, default=0)  # For pending orders

  # Location tracking
  shelf_location = Column(String(100))
  warehouse_id = Column(Integer, ForeignKey("warehouses.id"))

  # Status
  is_active = Column(Boolean, default=True)
  last_restocked = Column(DateTime)
  next_restock_date = Column(DateTime)

  # Metrics
  turnover_rate = Column(Float, default=0.0)  # Annual turnover rate
  days_in_stock = Column(Integer, default=0)

  created_at = Column(DateTime(timezone=True), server_default=func.now())
  updated_at = Column(DateTime(timezone=True), onupdate=func.now())

  # Relationships
  product = relationship("Product", back_populates="inventory_items")
  batch = relationship("ProductBatch")
  warehouse = relationship("Warehouse")
  movements = relationship("StockMovement", back_populates="inventory_item")

  @property
  def available_quantity(self) -> ColumnElement[int]:
    return self.quantity - self.reserved_quantity

  def update_turnover_rate(self, sales_quantity: int, period_days: int = 365):
    """Update turnover rate based on sales"""
    avg_inventory = self.quantity / 2 if self.quantity > 0 else 1
    self.turnover_rate = (sales_quantity / avg_inventory) * (365 / period_days)


class StockMovement(Base):
  __tablename__ = "stock_movements"

  id = Column(Integer, primary_key=True, index=True)
  inventory_item_id = Column(Integer, ForeignKey("inventory_items.id"), nullable=False)
  movement_type = Column(Enum(StockMovementType), nullable=False)
  quantity = Column(Integer, nullable=False)
  previous_quantity = Column(Integer)
  new_quantity = Column(Integer)

  # Reference
  reference_id = Column(Integer)  # Order ID, Purchase ID, etc.
  reference_type = Column(String(50))

  # Details
  reason = Column(String(500))
  notes = Column(Text)

  # User who made the movement
  user_id = Column(Integer, ForeignKey("users.id"))

  created_at = Column(DateTime(timezone=True), server_default=func.now())

  # Relationships
  inventory_item = relationship("InventoryItem", back_populates="movements")
  user = relationship("User")


class Warehouse(Base):
  __tablename__ = "warehouses"

  id = Column(Integer, primary_key=True, index=True)
  name = Column(String(100), nullable=False)
  code = Column(String(50), unique=True)
  location = Column(String(200))
  address = Column(Text)
  contact_person = Column(String(100))
  contact_phone = Column(String(20))
  contact_email = Column(String(100))

  # Capacity
  total_capacity = Column(Integer)  # in units or cubic meters
  used_capacity = Column(Integer)

  is_active = Column(Boolean, default=True)

  # Relationships
  inventory_items = relationship("InventoryItem", back_populates="warehouse")