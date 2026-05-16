from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, ForeignKey, Enum, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
from app.database import Base
import enum


class UserRole(enum.Enum):
  ADMIN = "admin"
  PHARMACIST = "pharmacist"
  TECHNICIAN = "technician"
  MANAGER = "manager"
  CASHIER = "cashier"
  INVENTORY_MANAGER = "inventory_manager"
  CUSTOMER = "customer"


class User(Base):
  __tablename__ = "users"

  id = Column(Integer, primary_key=True, index=True)
  username = Column(String(50), unique=True, index=True, nullable=False)
  email = Column(String(100), unique=True, index=True, nullable=False)
  password_hash = Column(String(255), nullable=False)

  # Personal Information
  first_name = Column(String(100), nullable=False)
  last_name = Column(String(100), nullable=False)
  phone = Column(String(20))
  mobile = Column(String(20))

  # Address
  address = Column(Text)
  city = Column(String(100))
  state = Column(String(100))
  zip_code = Column(String(20))
  country = Column(String(100))

  # Professional Information
  role = Column(Enum(UserRole), default=UserRole.PHARMACIST)
  employee_id = Column(String(50), unique=True)
  department = Column(String(100))
  designation = Column(String(100))

  # Pharmacy License/Certification
  license_number = Column(String(100))
  license_expiry = Column(DateTime)
  certification = Column(JSON)  # List of certifications

  # Employment Details
  hire_date = Column(DateTime)
  termination_date = Column(DateTime)
  salary = Column(Float)
  employment_type = Column(String(50))  # full_time, part_time, contract

  # Work Schedule
  shift_start = Column(String(10))  # "09:00"
  shift_end = Column(String(10))  # "17:00"
  working_days = Column(JSON)  # ["Monday", "Tuesday", ...]

  # Permissions
  permissions = Column(JSON)  # List of specific permissions

  # Status
  is_active = Column(Boolean, default=True)
  is_verified = Column(Boolean, default=False)
  is_superuser = Column(Boolean, default=False)

  # Security
  last_login = Column(DateTime(timezone=True))
  failed_login_attempts = Column(Integer, default=0)
  locked_until = Column(DateTime(timezone=True))

  # Preferences
  language = Column(String(10), default="en")
  timezone = Column(String(50), default="UTC")
  theme = Column(String(20), default="light")

  # Emergency Contact
  emergency_contact_name = Column(String(200))
  emergency_contact_phone = Column(String(20))
  emergency_contact_relation = Column(String(50))

  # Dates
  date_of_birth = Column(DateTime)
  created_at = Column(DateTime(timezone=True), server_default=func.now())
  updated_at = Column(DateTime(timezone=True), onupdate=func.now())

  # Relationships
  created_orders = relationship("Order", foreign_keys="[Order.pharmacist_id]", back_populates="pharmacist")
  verified_orders = relationship("Order", foreign_keys="[Order.verified_by]", back_populates="verifier")
  collected_payments = relationship("Payment", foreign_keys="[Payment.collected_by]", back_populates="collector")
  verified_payments = relationship("Payment", foreign_keys="[Payment.verified_by]", back_populates="verifier")

  @property
  def full_name(self):
    return f"{self.first_name} {self.last_name}"

  def has_permission(self, permission: str) -> bool:
    """Check if user has specific permission"""
    if self.is_superuser:
      return True

    if self.permissions and permission in self.permissions:
      return True

    # Check role-based permissions
    role_permissions = {
      UserRole.ADMIN: ["all"],
      UserRole.MANAGER: [
        "view_reports", "manage_inventory", "manage_orders",
        "manage_customers", "manage_payments"
      ],
      UserRole.PHARMACIST: [
        "dispense_medication", "verify_prescription",
        "manage_orders", "view_inventory"
      ],
      UserRole.TECHNICIAN: ["prepare_orders", "view_inventory"],
      UserRole.CASHIER: ["process_payments", "create_orders"],
      UserRole.INVENTORY_MANAGER: ["manage_inventory", "view_reports"],
      UserRole.CUSTOMER: ["view_own_orders", "make_payments"]
    }

    return permission in role_permissions.get(self.role, [])

  def is_locked(self) -> bool:
    """Check if user account is locked"""
    if self.locked_until and self.locked_until > datetime.now():
      return True
    return False