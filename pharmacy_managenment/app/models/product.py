from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, ForeignKey, ColumnElement
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
from datetime import datetime


class Product(Base):
  __tablename__ = "products"

  id = Column(Integer, primary_key=True, index=True)
  name = Column(String(200), nullable=False)
  generic_name = Column(String(200))
  brand = Column(String(100))
  category = Column(String(100))  # e.g., Antibiotics, Pain Relief
  description = Column(Text)
  sku = Column(String(50), unique=True, index=True)
  barcode = Column(String(100), unique=True)
  unit = Column(String(50))  # e.g., tablet, bottle, tube
  package_size = Column(Integer)  # e.g., 10 tablets per package
  requires_prescription = Column(Boolean, default=False)

  # Pricing
  cost_price = Column(Float, nullable=False)
  selling_price = Column(Float, nullable=False)
  discount = Column(Float, default=0.0)

  # Inventory tracking
  min_stock_level = Column(Integer, default=10)
  max_stock_level = Column(Integer, default=100)

  # Supplier info
  supplier_id = Column(Integer, ForeignKey("suppliers.id"))
  manufacturer = Column(String(200))

  # Classification
  drug_schedule = Column(String(50))  # e.g., Schedule H, OTC
  therapeutic_class = Column(String(200))

  # Dates
  created_at = Column(DateTime(timezone=True), server_default=func.now())
  updated_at = Column(DateTime(timezone=True), onupdate=func.now())

  # Relationships
  inventory_items = relationship("InventoryItem", back_populates="product")
  order_items = relationship("OrderItem", back_populates="product")
  batches = relationship("ProductBatch", back_populates="product")
  supplier = relationship("Supplier", back_populates="products")

  def calculate_profit_margin(self) -> float:
    if self.cost_price > 0:
      return ((self.selling_price - self.cost_price) / self.cost_price) * 100
    return 0.0


class ProductBatch(Base):
  __tablename__ = "product_batches"

  id = Column(Integer, primary_key=True, index=True)
  product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
  batch_number = Column(String(100), nullable=False, unique=True)
  manufacturing_date = Column(DateTime)
  expiry_date = Column(DateTime, nullable=False)
  quantity_received = Column(Integer, nullable=False)
  quantity_available = Column(Integer, nullable=False)
  purchase_price = Column(Float, nullable=False)

  # Storage
  storage_location = Column(String(100))
  storage_conditions = Column(String(200))  # e.g., "Store at 2-8°C"

  # Status
  status = Column(String(50), default="active")  # active, expired, recalled

  created_at = Column(DateTime(timezone=True), server_default=func.now())

  # Relationships
  product = relationship("Product", back_populates="batches")

  def is_expired(self) -> ColumnElement[bool]:
    from datetime import datetime
    return datetime.now() > self.expiry_date

  def days_to_expiry(self) -> int:
    from datetime import datetime
    if self.expiry_date:
      delta = self.expiry_date - datetime.now()
      return delta.days
    return 0