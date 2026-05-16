from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class CustomerType(str, Enum):
  REGULAR = "regular"
  VIP = "vip"
  WHOLESALE = "wholesale"
  CORPORATE = "corporate"


class CommunicationPreference(str, Enum):
  EMAIL = "email"
  SMS = "sms"
  BOTH = "both"
  NONE = "none"


class CustomerBase(BaseModel):
  first_name: str
  last_name: str
  email: Optional[EmailStr] = None
  phone: Optional[str] = None
  mobile: Optional[str] = None
  address: Optional[str] = None
  city: Optional[str] = None
  state: Optional[str] = None
  zip_code: Optional[str] = None
  country: Optional[str] = "USA"
  date_of_birth: Optional[datetime] = None
  gender: Optional[str] = None
  blood_group: Optional[str] = None
  allergies: Optional[List[str]] = None
  chronic_conditions: Optional[List[str]] = None
  emergency_contact_name: Optional[str] = None
  emergency_contact_phone: Optional[str] = None
  emergency_contact_relation: Optional[str] = None
  primary_physician: Optional[str] = None
  insurance_provider: Optional[str] = None
  insurance_policy_number: Optional[str] = None
  customer_type: CustomerType = CustomerType.REGULAR
  credit_limit: float = 0.0
  preferred_payment_method: Optional[str] = None
  communication_preference: CommunicationPreference = CommunicationPreference.EMAIL
  opt_in_marketing: bool = True


class CustomerCreate(CustomerBase):
  pass


class CustomerUpdate(BaseModel):
  first_name: Optional[str] = None
  last_name: Optional[str] = None
  email: Optional[EmailStr] = None
  phone: Optional[str] = None
  mobile: Optional[str] = None
  address: Optional[str] = None
  city: Optional[str] = None
  state: Optional[str] = None
  zip_code: Optional[str] = None
  date_of_birth: Optional[datetime] = None
  gender: Optional[str] = None
  blood_group: Optional[str] = None
  allergies: Optional[List[str]] = None
  chronic_conditions: Optional[List[str]] = None
  emergency_contact_name: Optional[str] = None
  emergency_contact_phone: Optional[str] = None
  primary_physician: Optional[str] = None
  insurance_provider: Optional[str] = None
  insurance_policy_number: Optional[str] = None
  customer_type: Optional[CustomerType] = None
  credit_limit: Optional[float] = None
  preferred_payment_method: Optional[str] = None
  communication_preference: Optional[CommunicationPreference] = None
  opt_in_marketing: Optional[bool] = None
  is_active: Optional[bool] = None


class CustomerResponse(CustomerBase):
  id: int
  customer_code: str
  age: Optional[int] = None
  loyalty_points: int
  current_balance: float
  is_active: bool
  is_blacklisted: bool
  total_orders: int
  total_spent: float
  average_order_value: float
  last_visit_date: Optional[datetime] = None
  registration_date: datetime
  created_at: datetime
  updated_at: Optional[datetime] = None

  class Config:
    from_attributes = True


class PrescriptionBase(BaseModel):
  customer_id: int
  physician_name: str
  physician_license: Optional[str] = None
  clinic_name: Optional[str] = None
  clinic_address: Optional[str] = None
  diagnosis: Optional[str] = None
  notes: Optional[str] = None
  is_emergency: bool = False
  issue_date: datetime
  expiry_date: datetime


class PrescriptionCreate(PrescriptionBase):
  pass


class PrescriptionUpdate(BaseModel):
  physician_name: Optional[str] = None
  diagnosis: Optional[str] = None
  notes: Optional[str] = None
  status: Optional[str] = None
  verification_date: Optional[datetime] = None
  dispensed_date: Optional[datetime] = None


class PrescriptionResponse(PrescriptionBase):
  id: int
  prescription_number: str
  customer_name: Optional[str] = None
  status: str
  verification_date: Optional[datetime] = None
  verified_by: Optional[int] = None
  verifier_name: Optional[str] = None
  dispensed_date: Optional[datetime] = None
  created_at: datetime
  updated_at: Optional[datetime] = None

  class Config:
    from_attributes = True


class PrescriptionItemBase(BaseModel):
  prescription_id: int
  product_id: int
  dosage: str
  frequency: str
  duration: str
  instructions: Optional[str] = None
  quantity_prescribed: int
  refills_allowed: int = 0
  allow_generic: bool = True
  allow_substitution: bool = False


class PrescriptionItemCreate(PrescriptionItemBase):
  pass


class PrescriptionItemResponse(PrescriptionItemBase):
  id: int
  product_name: Optional[str] = None
  quantity_dispensed: int
  refills_used: int
  status: str
  created_at: datetime

  class Config:
    from_attributes = True


class CustomerStats(BaseModel):
  total_customers: int
  active_customers: int
  new_customers_today: int
  new_customers_this_week: int
  customers_by_type: Dict[str, int]
  average_order_value: float
  top_customers: List[Dict[str, Any]]