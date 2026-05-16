from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from enum import Enum


class StockMovementType(str, Enum):
  PURCHASE = "purchase"
  SALE = "sale"
  RETURN = "return"
  ADJUSTMENT = "adjustment"
  TRANSFER = "transfer"
  DAMAGE = "damage"
  EXPIRED = "expired"


class InventoryItemBase(BaseModel):
  product_id: int
  batch_id: Optional[int] = None
  quantity: int
  reserved_quantity: Optional[int] = 0
  shelf_location: Optional[str] = None
  warehouse_id: Optional[int] = None


class InventoryItemCreate(InventoryItemBase):
  pass


class InventoryItemUpdate(BaseModel):
  quantity: Optional[int] = None
  reserved_quantity: Optional[int] = None
  shelf_location: Optional[str] = None
  warehouse_id: Optional[int] = None
  is_active: Optional[bool] = None


class InventoryItemResponse(InventoryItemBase):
  id: int
  available_quantity: int
  product_name: Optional[str] = None
  product_sku: Optional[str] = None
  batch_number: Optional[str] = None
  warehouse_name: Optional[str] = None
  is_active: bool
  turnover_rate: Optional[float] = None
  days_in_stock: Optional[int] = None
  created_at: datetime
  updated_at: Optional[datetime] = None

  class Config:
    from_attributes = True


class StockMovementBase(BaseModel):
  inventory_item_id: int
  movement_type: StockMovementType
  quantity: int
  reference_id: Optional[int] = None
  reference_type: Optional[str] = None
  reason: Optional[str] = None
  notes: Optional[str] = None
  user_id: Optional[int] = None


class StockMovementCreate(StockMovementBase):
  pass


class StockMovementResponse(StockMovementBase):
  id: int
  previous_quantity: Optional[int] = None
  new_quantity: Optional[int] = None
  product_name: Optional[str] = None
  user_name: Optional[str] = None
  created_at: datetime

  class Config:
    from_attributes = True


class InventoryAlert(BaseModel):
  type: str  # low_stock, expired, near_expiry, over_stock
  product_id: int
  product_name: str
  current_quantity: int
  threshold: int
  message: str
  severity: str  # low, medium, high, critical
  suggested_action: Optional[str] = None


class InventoryAnalysis(BaseModel):
  total_products: int
  total_inventory_value: float
  low_stock_items: int
  expired_batches: int
  fast_moving_products: List[dict]
  slow_moving_products: List[dict]
  stock_turnover_ratio: Optional[float] = None
  average_stock_level: Optional[float] = None


class ExpiredProductsResponse(BaseModel):
  product_id: int
  product_name: str
  batch_number: str
  expiry_date: datetime
  quantity_available: int
  status: str
  days_to_expiry: int


class StockTransfer(BaseModel):
  from_warehouse_id: int
  to_warehouse_id: int
  inventory_item_id: int
  quantity: int
  reason: Optional[str] = None
  notes: Optional[str] = None