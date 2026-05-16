from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
from datetime import datetime


class Customer(Base):
  __tablename__ = "customers"

  id = Column(Integer, primary_key=True, index=True)
  customer_code = Column(String(50), unique=True, index=True)
  first_name = Column(String(100), nullable=False)
  last_name = Column(String(100), nullable=False)
  email = Column(String(100), unique=True, index=True)
  phone = Column(String(20))
  mobile = Column(String(20))

  # Address
  address = Column(Text)
  city = Column(String(100))
  state = Column(String(100))
  zip_code = Column(String(20))
  country = Column(String(100))

  # Personal Information
  date_of_birth = Column(DateTime)
  gender = Column(String(10))  # male, female, other
  blood_group = Column(String(5))
  allergies = Column(JSON)  # List of allergies
  chronic_conditions = Column(JSON)  # List of conditions

  # Emergency Contact
  emergency_contact_name = Column(String(200))
  emergency_contact_phone = Column(String(20))
  emergency_contact_relation = Column(String(50))

  # Pharmacy Details
  primary_physician = Column(String(200))
  insurance_provider = Column(String(200))
  insurance_policy_number = Column(String(100))

  # Customer Classification
  customer_type = Column(String(50), default="regular")  # regular, vip, wholesale
  loyalty_points = Column(Integer, default=0)
  credit_limit = Column(Float, default=0.0)
  current_balance = Column(Float, default=0.0)

  # Status
  is_active = Column(Boolean, default=True)
  is_blacklisted = Column(Boolean, default=False)
  blacklist_reason = Column(Text)

  # Preferences
  preferred_payment_method = Column(String(50))
  communication_preference = Column(String(50), default="email")  # email, sms, both
  opt_in_marketing = Column(Boolean, default=True)

  # Dates
  registration_date = Column(DateTime(timezone=True), server_default=func.now())
  last_visit_date = Column(DateTime(timezone=True))
  next_followup_date = Column(DateTime(timezone=True))

  # Statistics
  total_orders = Column(Integer, default=0)
  total_spent = Column(Float, default=0.0)
  average_order_value = Column(Float, default=0.0)
  last_order_amount = Column(Float, default=0.0)

  created_at = Column(DateTime(timezone=True), server_default=func.now())
  updated_at = Column(DateTime(timezone=True), onupdate=func.now())

  # Relationships
  prescriptions = relationship("Prescription", back_populates="customer")
  orders = relationship("Order", back_populates="customer")
  payments = relationship("Payment", back_populates="customer")
  medical_history = relationship("MedicalHistory", back_populates="customer")

  @property
  def full_name(self):
    return f"{self.first_name} {self.last_name}"

  @property
  def age(self):
    if self.date_of_birth:
      today = datetime.now()
      return today.year - self.date_of_birth.year - (
          (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day)
      )
    return None

  def update_statistics(self, order_amount: float):
    """Update customer statistics after an order"""
    self.total_orders += 1
    self.total_spent += order_amount
    self.average_order_value = self.total_spent / self.total_orders if self.total_orders > 0 else 0
    self.last_order_amount = order_amount
    self.last_visit_date = datetime.now()


class Prescription(Base):
  __tablename__ = "prescriptions"

  id = Column(Integer, primary_key=True, index=True)
  customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
  prescription_number = Column(String(100), unique=True, index=True)
  physician_name = Column(String(200))
  physician_license = Column(String(100))
  clinic_name = Column(String(200))
  clinic_address = Column(Text)

  # Prescription Details
  diagnosis = Column(Text)
  notes = Column(Text)
  is_emergency = Column(Boolean, default=False)

  # Status
  status = Column(String(50), default="pending")  # pending, verified, dispensed, expired, cancelled
  verification_date = Column(DateTime(timezone=True))
  verification_by = Column(Integer, ForeignKey("users.id"))

  # Dates
  issue_date = Column(DateTime(timezone=True))
  expiry_date = Column(DateTime(timezone=True))
  dispensed_date = Column(DateTime(timezone=True))

  # Digital Prescription
  prescription_image_url = Column(String(500))
  digital_signature = Column(Text)

  created_at = Column(DateTime(timezone=True), server_default=func.now())
  updated_at = Column(DateTime(timezone=True), onupdate=func.now())

  # Relationships
  customer = relationship("Customer", back_populates="prescriptions")
  prescription_items = relationship("PrescriptionItem", back_populates="prescription")
  verifier = relationship("User", foreign_keys=[verification_by])


class PrescriptionItem(Base):
  __tablename__ = "prescription_items"

  id = Column(Integer, primary_key=True, index=True)
  prescription_id = Column(Integer, ForeignKey("prescriptions.id"), nullable=False)
  product_id = Column(Integer, ForeignKey("products.id"), nullable=False)

  # Dosage Information
  dosage = Column(String(100))  # e.g., "500mg"
  frequency = Column(String(100))  # e.g., "twice daily"
  duration = Column(String(100))  # e.g., "7 days"
  instructions = Column(Text)  # e.g., "Take with food"

  # Quantity
  quantity_prescribed = Column(Integer, nullable=False)
  quantity_dispensed = Column(Integer, default=0)

  # Refills
  refills_allowed = Column(Integer, default=0)
  refills_used = Column(Integer, default=0)

  # Substitution
  allow_generic = Column(Boolean, default=True)
  allow_substitution = Column(Boolean, default=False)

  # Status
  status = Column(String(50), default="pending")  # pending, dispensed, partially_dispensed

  created_at = Column(DateTime(timezone=True), server_default=func.now())

  # Relationships
  prescription = relationship("Prescription", back_populates="prescription_items")
  product = relationship("Product")


class MedicalHistory(Base):
  __tablename__ = "medical_history"

  id = Column(Integer, primary_key=True, index=True)
  customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)

  # History Type
  history_type = Column(String(100))  # allergy, condition, surgery, vaccination

  # Details
  description = Column(Text, nullable=False)
  severity = Column(String(50))  # mild, moderate, severe
  onset_date = Column(DateTime)
  resolved_date = Column(DateTime)
  is_chronic = Column(Boolean, default=False)

  # Treatment
  treatment = Column(Text)
  medications = Column(JSON)  # List of medications used

  # Doctor Information
  doctor_name = Column(String(200))
  hospital_name = Column(String(200))

  # Notes
  notes = Column(Text)

  created_at = Column(DateTime(timezone=True), server_default=func.now())
  updated_at = Column(DateTime(timezone=True), onupdate=func.now())

  # Relationships
  customer = relationship("Customer", back_populates="medical_history")