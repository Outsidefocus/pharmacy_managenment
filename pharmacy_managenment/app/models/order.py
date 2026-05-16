from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, ForeignKey, Enum, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
import enum
from datetime import datetime


class OrderStatus(enum.Enum):
  PENDING = "pending"
  CONFIRMED = "confirmed"
  PROCESSING = "processing"
  READY_FOR_PICKUP = "ready_for_pickup"
  OUT_FOR_DELIVERY = "out_for_delivery"
  COMPLETED = "completed"
  CANCELLED = "cancelled"
  REFUNDED = "refunded"


class PaymentStatus(enum.Enum):
  PENDING = "pending"
  PARTIAL = "partial"
  PAID = "paid"
  FAILED = "failed"
  REFUNDED = "refunded"


class OrderType(enum.Enum):
  WALKIN = "walkin"
  ONLINE = "online"
  PRESCRIPTION = "prescription"
  WHOLESALE = "wholesale"


class Order(Base):
  __tablename__ = "orders"

  id = Column(Integer, primary_key=True, index=True)
  order_number = Column(String(100), unique=True, index=True)

  # Customer Information
  customer_id = Column(Integer, ForeignKey("customers.id"))
  customer_name = Column(String(200))
  customer_phone = Column(String(20))

  # Order Details
  order_type = Column(Enum(OrderType), default=OrderType.WALKIN)
  prescription_id = Column(Integer, ForeignKey("prescriptions.id"))

  # Status
  status = Column(Enum(OrderStatus), default=OrderStatus.PENDING)
  payment_status = Column(Enum(PaymentStatus), default=PaymentStatus.PENDING)

  # Financials
  subtotal = Column(Float, default=0.0)
  tax_amount = Column(Float, default=0.0)
  discount_amount = Column(Float, default=0.0)
  shipping_charge = Column(Float, default=0.0)
  total_amount = Column(Float, default=0.0)
  amount_paid = Column(Float, default=0.0)
  amount_due = Column(Float, default=0.0)

  # Payment Information
  payment_method = Column(String(50))
  payment_reference = Column(String(200))

  # Delivery/Pickup
  delivery_address = Column(Text)
  delivery_city = Column(String(100))
  delivery_state = Column(String(100))
  delivery_zip = Column(String(20))
  delivery_instructions = Column(Text)

  pickup_location = Column(String(200))
  estimated_pickup_time = Column(DateTime)
  actual_pickup_time = Column(DateTime)

  # Pharmacy Information
  pharmacy_branch_id = Column(Integer, ForeignKey("pharmacy_branches.id"))
  pharmacist_id = Column(Integer, ForeignKey("users.id"))

  # Prescription Validation
  prescription_verified = Column(Boolean, default=False)
  verified_by = Column(Integer, ForeignKey("users.id"))
  verification_date = Column(DateTime)

  # Dates
  order_date = Column(DateTime(timezone=True), server_default=func.now())
  expected_delivery_date = Column(DateTime)
  completed_date = Column(DateTime)
  cancelled_date = Column(DateTime)

  # Metadata
  notes = Column(Text)
  cancellation_reason = Column(Text)
  internal_notes = Column(Text)

  created_at = Column(DateTime(timezone=True), server_default=func.now())
  updated_at = Column(DateTime(timezone=True), onupdate=func.now())

  # Relationships
  customer = relationship("Customer", back_populates="orders")
  prescription = relationship("Prescription")
  order_items = relationship("OrderItem", back_populates="order")
  payments = relationship("Payment", back_populates="order")
  pharmacy_branch = relationship("PharmacyBranch")
  pharmacist = relationship("User", foreign_keys=[pharmacist_id])
  verifier = relationship("User", foreign_keys=[verified_by])

  def calculate_totals(self):
    """Calculate order totals"""
    self.subtotal = sum(item.subtotal for item in self.order_items)
    self.total_amount = self.subtotal + self.tax_amount + self.shipping_charge - self.discount_amount
    self.amount_due = self.total_amount - self.amount_paid


class OrderItem(Base):
  __tablename__ = "order_items"

  id = Column(Integer, primary_key=True, index=True)
  order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
  product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
  prescription_item_id = Column(Integer, ForeignKey("prescription_items.id"))

  # Product Details
  product_name = Column(String(200))
  product_sku = Column(String(50))
  batch_number = Column(String(100))

  # Pricing
  unit_price = Column(Float, nullable=False)
  quantity = Column(Integer, nullable=False, default=1)
  discount_percentage = Column(Float, default=0.0)
  discount_amount = Column(Float, default=0.0)
  tax_percentage = Column(Float, default=0.0)
  tax_amount = Column(Float, default=0.0)
  subtotal = Column(Float, nullable=False)

  # Inventory Tracking
  inventory_item_id = Column(Integer, ForeignKey("inventory_items.id"))
  picked_quantity = Column(Integer, default=0)
  dispensed_quantity = Column(Integer, default=0)

  # Status
  status = Column(String(50), default="pending")  # pending, picked, dispensed

  # Substitution
  is_substituted = Column(Boolean, default=False)
  original_product_id = Column(Integer, ForeignKey("products.id"))
  substitution_reason = Column(Text)

  created_at = Column(DateTime(timezone=True), server_default=func.now())

  # Relationships
  order = relationship("Order", back_populates="order_items")
  product = relationship("Product", back_populates="order_items", foreign_keys=[product_id])
  prescription_item = relationship("PrescriptionItem")
  inventory_item = relationship("InventoryItem")
  original_product = relationship("Product", foreign_keys=[original_product_id])

  def calculate_subtotal(self):
    """Calculate item subtotal"""
    base_amount = self.unit_price * self.quantity
    self.discount_amount = base_amount * (self.discount_percentage / 100)
    self.tax_amount = (base_amount - self.discount_amount) * (self.tax_percentage / 100)
    self.subtotal = base_amount - self.discount_amount + self.tax_amount
    return self.subtotal


class PharmacyBranch(Base):
  __tablename__ = "pharmacy_branches"

  id = Column(Integer, primary_key=True, index=True)
  branch_code = Column(String(50), unique=True, index=True)
  branch_name = Column(String(200), nullable=False)

  # Contact Information
  address = Column(Text)
  city = Column(String(100))
  state = Column(String(100))
  zip_code = Column(String(20))
  country = Column(String(100))
  phone = Column(String(20))
  email = Column(String(100))

  # Operating Hours
  opening_time = Column(String(10))  # Format: "09:00"
  closing_time = Column(String(10))  # Format: "21:00"
  working_days = Column(JSON)  # List of days: ["Monday", "Tuesday", ...]

  # Services
  services_offered = Column(JSON)  # ["Prescription", "Delivery", "Vaccination", ...]

  # Staff
  pharmacist_in_charge = Column(String(200))
  manager_id = Column(Integer, ForeignKey("users.id"))

  # Status
  is_active = Column(Boolean, default=True)

  # Inventory
  has_inventory = Column(Boolean, default=True)

  created_at = Column(DateTime(timezone=True), server_default=func.now())
  updated_at = Column(DateTime(timezone=True), onupdate=func.now())

  # Relationships
  orders = relationship("Order", back_populates="pharmacy_branch")
  manager = relationship("User", foreign_keys=[manager_id])