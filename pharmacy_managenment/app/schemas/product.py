from pydantic import BaseModel, validator
from typing import Optional, List
from datetime import datetime
from decimal import Decimal


class ProductBase(BaseModel):
  name: str
  generic_name: Optional[str] = None
  brand: Optional[str] = None
  category: Optional[str] = None
  description: Optional[str] = None
  sku: str
  barcode: Optional[str] = None
  unit: Optional[str] = None
  package_size: Optional[int] = 1
  requires_prescription: bool = False
  cost_price: float
  selling_price: float
  discount: float = 0.0
  min_stock_level: int = 10
  max_stock_level: int = 100
  supplier_id: Optional[int] = None
  manufacturer: Optional[str] = None
  drug_schedule: Optional[str] = None
  therapeutic_class: Optional[str] = None


class ProductCreate(ProductBase):
  pass


class ProductUpdate(BaseModel):
  name: Optional[str] = None
  generic_name: Optional[str] = None
  brand: Optional[str] = None
  category: Optional[str] = None
  description: Optional[str] = None
  barcode: Optional[str] = None
  unit: Optional[str] = None
  package_size: Optional[int] = None
  requires_prescription: Optional[bool] = None
  cost_price: Optional[float] = None
  selling_price: Optional[float] = None
  discount: Optional[float] = None
  min_stock_level: Optional[int] = None
  max_stock_level: Optional[int] = None
  supplier_id: Optional[int] = None
  manufacturer: Optional[str] = None


class ProductResponse(ProductBase):
  id: int
  profit_margin: Optional[float] = None
  created_at: datetime
  updated_at: Optional[datetime] = None

  class Config:
    from_attributes = True


class ProductBatchBase(BaseModel):
  product_id: int
  batch_number: str
  manufacturing_date: Optional[datetime] = None
  expiry_date: datetime
  quantity_received: int
  quantity_available: int
  purchase_price: float
  storage_location: Optional[str] = None
  storage_conditions: Optional[str] = None
  status: Optional[str] = "active"


class ProductBatchCreate(ProductBatchBase):
  pass


class ProductBatchUpdate(BaseModel):
  quantity_available: Optional[int] = None
  storage_location: Optional[str] = None
  storage_conditions: Optional[str] = None
  status: Optional[str] = None


class ProductBatchResponse(ProductBatchBase):
  id: int
  product_name: Optional[str] = None
  days_to_expiry: Optional[int] = None
  is_expired: Optional[bool] = None
  created_at: datetime

  class Config:
    from_attributes = True


class ProductStats(BaseModel):
  total_products: int
  total_value: float
  categories: List[dict]
  low_stock_count: int
  expired_count: int
  fast_moving: List[dict]
  slow_moving: List[dict]


class ProductSearch(BaseModel):
  search_term: Optional[str] = None
  category: Optional[str] = None
  requires_prescription: Optional[bool] = None
  min_price: Optional[float] = None
  max_price: Optional[float] = None
  in_stock: Optional[bool] = None
  sort_by: Optional[str] = "name"
  sort_order: Optional[str] = "asc"