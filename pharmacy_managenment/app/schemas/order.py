from pydantic import BaseModel, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class OrderStatus(str, Enum):
  PENDING = "pending"
  CONFIRMED = "confirmed"
  PROCESSING = "processing"
  READY_FOR_PICKUP = "ready_for_pickup"
  OUT_FOR_DELIVERY = "out_for_delivery"
  COMPLETED = "completed"
  CANCELLED = "cancelled"
  REFUNDED = "refunded"


class PaymentStatus(str, Enum):
  PENDING = "pending"
  PARTIAL = "partial"
  PAID = "paid"
  FAILED = "failed"
  REFUNDED = "refunded"


class OrderType(str, Enum):
  WALKIN = "walkin"
  ONLINE = "online"
  PRESCRIPTION = "prescription"
  WHOLESALE = "wholesale"


class OrderBase(BaseModel):
  customer_id: Optional[int] = None
  customer_name: Optional[str] = None
  customer_phone: Optional[str] = None
  order_type: OrderType = OrderType.WALKIN
  prescription_id: Optional[int] = None
  delivery_address: Optional[str] = None
  delivery_city: Optional[str] = None
  delivery_state: Optional[str] = None
  delivery_zip: Optional[str] = None
  delivery_instructions: Optional[str] = None
  pickup_location: Optional[str] = None
  pharmacy_branch_id: Optional[int] = None
  pharmacist_id: Optional[int] = None
  notes: Optional[str] = None


class OrderCreate(OrderBase):
  items: List[Dict[str, Any]]


class OrderUpdate(BaseModel):
  status: Optional[OrderStatus] = None
  payment_status: Optional[PaymentStatus] = None
  delivery_address: Optional[str] = None
  delivery_instructions: Optional[str] = None
  pickup_location: Optional[str] = None
  estimated_pickup_time: Optional[datetime] = None
  notes: Optional[str] = None
  cancellation_reason: Optional[str] = None


class OrderItemBase(BaseModel):
  product_id: int
  quantity: int
  unit_price: float
  discount_percentage: Optional[float] = 0.0
  prescription_item_id: Optional[int] = None


class OrderItemCreate(OrderItemBase):
  pass


class OrderItemResponse(OrderItemBase):
  id: int
  order_id: int
  product_name: Optional[str] = None
  product_sku: Optional[str] = None
  batch_number: Optional[str] = None
  discount_amount: float
  tax_amount: float
  subtotal: float
  picked_quantity: int
  dispensed_quantity: int
  status: str
  created_at: datetime

  class Config:
    from_attributes = True


class OrderResponse(OrderBase):
  id: int
  order_number: str
  status: OrderStatus
  payment_status: PaymentStatus
  subtotal: float
  tax_amount: float
  discount_amount: float
  shipping_charge: float
  total_amount: float
  amount_paid: float
  amount_due: float
  payment_method: Optional[str] = None
  prescription_verified: bool = False
  verified_by: Optional[int] = None
  order_date: datetime
  expected_delivery_date: Optional[datetime] = None
  completed_date: Optional[datetime] = None
  cancelled_date: Optional[datetime] = None
  items: List[OrderItemResponse] = []
  customer_info: Optional[Dict[str, Any]] = None
  created_at: datetime
  updated_at: Optional[datetime] = None

  class Config:
    from_attributes = True


class OrderStats(BaseModel):
  total_orders: int
  total_revenue: float
  average_order_value: float
  orders_by_status: Dict[str, int]
  orders_by_type: Dict[str, int]
  today_orders: int
  today_revenue: float
  pending_orders: int
  top_products: List[Dict[str, Any]]


class OrderSearch(BaseModel):
  search_term: Optional[str] = None
  status: Optional[OrderStatus] = None
  order_type: Optional[OrderType] = None
  customer_id: Optional[int] = None
  start_date: Optional[datetime] = None
  end_date: Optional[datetime] = None
  min_amount: Optional[float] = None
  max_amount: Optional[float] = None
  sort_by: Optional[str] = "order_date"
  sort_order: Optional[str] = "desc"