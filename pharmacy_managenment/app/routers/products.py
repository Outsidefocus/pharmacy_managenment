from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
from sqlalchemy.sql import func
from datetime import datetime

from app.database import get_db
from app.models.product import Product, ProductBatch
from app.schemas.product import (
  ProductCreate, ProductUpdate, ProductResponse,
  ProductBatchCreate, ProductBatchResponse,
  ProductStats, ProductSearch
)
from app.crud.product_crud import (
  get_product, get_products, create_product,
  update_product, delete_product, create_product_batch,
  update_product_batch, get_expiring_products,
  get_low_stock_products, get_product_stats,
  search_products
)
from app.utils.security import get_current_user, require_permission
from app.models.user import User
from app.services.notification_service import NotificationService

router = APIRouter()


@router.get("/", response_model=List[ProductResponse])
async def read_products(
    skip: int = 0,
    limit: int = 100,
    category: Optional[str] = None,
    requires_prescription: Optional[bool] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
  """Get all products"""
  products = get_products(
    db, skip=skip, limit=limit,
    category=category,
    requires_prescription=requires_prescription,
    search=search
  )
  return products


@router.get("/search", response_model=List[ProductResponse])
async def search_products_advanced(
    search_query: ProductSearch = Depends(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
  """Advanced product search"""
  products = search_products(
    db,
    search_term=search_query.search_term,
    category=search_query.category,
    requires_prescription=search_query.requires_prescription,
    min_price=search_query.min_price,
    max_price=search_query.max_price,
    in_stock=search_query.in_stock,
    sort_by=search_query.sort_by,
    sort_order=search_query.sort_order
  )
  return products


@router.get("/{product_id}", response_model=ProductResponse)
async def read_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
  """Get product by ID"""
  product = get_product(db, product_id)
  if not product:
    raise HTTPException(status_code=404, detail="Product not found")
  return product


@router.post("/", response_model=ProductResponse)
async def create_new_product(
    product: ProductCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("manage_inventory"))
):
  """Create new product"""
  # Check if SKU already exists
  existing_product = db.query(Product).filter(product.sku == Product.sku).first()
  if existing_product:
    raise HTTPException(
      status_code=400,
      detail="Product with this SKU already exists"
    )

  # Check if barcode already exists
  if product.barcode:
    existing_barcode = db.query(Product).filter(product.barcode == Product.barcode).first()
    if existing_barcode:
      raise HTTPException(
        status_code=400,
        detail="Product with this barcode already exists"
      )

  db_product = create_product(db, product)
  return db_product


@router.put("/{product_id}", response_model=ProductResponse)
async def update_existing_product(
    product_id: int,
    product_update: ProductUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("manage_inventory"))
):
  """Update product"""
  db_product = update_product(db, product_id, product_update)
  if not db_product:
    raise HTTPException(status_code=404, detail="Product not found")
  return db_product


@router.delete("/{product_id}")
async def delete_existing_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("manage_inventory"))
):
  """Delete product"""
  success = delete_product(db, product_id)
  if not success:
    raise HTTPException(status_code=404, detail="Product not found")
  return {"message": "Product deleted successfully"}


@router.get("/{product_id}/batches", response_model=List[ProductBatchResponse])
async def read_product_batches(
    product_id: int,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
  """Get batches for a product"""
  query = db.query(ProductBatch).filter(ProductBatch.product_id == product_id)

  if status:
    query = query.filter(ProductBatch.status == status)

  batches = query.all()
  return batches


@router.post("/{product_id}/batches", response_model=ProductBatchResponse)
async def create_new_batch(
    product_id: int,
    batch: ProductBatchCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("manage_inventory"))
):
  """Create new batch for product"""
  # Verify product exists
  product = get_product(db, product_id)
  if not product:
    raise HTTPException(status_code=404, detail="Product not found")

  # Check if batch number already exists
  existing_batch = db.query(ProductBatch).filter(
    ProductBatch.batch_number == batch.batch_number
  ).first()
  if existing_batch:
    raise HTTPException(
      status_code=400,
      detail="Batch number already exists"
    )

  # Set product ID
  batch_dict = batch.dict()
  batch_dict["product_id"] = product_id

  db_batch = create_product_batch(db, batch)

  # Check if batch is expiring soon
  if db_batch.days_to_expiry() <= 30:
    background_tasks.add_task(
      NotificationService.send_expiry_notification,
      db_batch, "warning"
    )

  return db_batch


@router.put("/batches/{batch_id}", response_model=ProductBatchResponse)
async def update_batch(
    batch_id: int,
    batch_update: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("manage_inventory"))
):
  """Update product batch"""
  db_batch = update_product_batch(db, batch_id, batch_update)
  if not db_batch:
    raise HTTPException(status_code=404, detail="Batch not found")
  return db_batch


@router.get("/stats/overview", response_model=ProductStats)
async def get_products_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
  """Get product statistics"""
  stats = get_product_stats(db)
  return stats


@router.get("/low-stock", response_model=List[dict])
async def get_low_stock(
    threshold: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
  """Get low stock products"""
  low_stock = get_low_stock_products(db)

  if threshold:
    low_stock = [item for item in low_stock if item["current_stock"] <= threshold]

  return low_stock


@router.get("/expiring", response_model=List[dict])
async def get_expiring(
    days: int = Query(30, description="Days threshold for expiry"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
  """Get expiring products"""
  expiring = get_expiring_products(db, days)

  result = []
  for batch in expiring:
    product = get_product(db, batch.product_id)
    if product:
      result.append({
        "product_id": product.id,
        "product_name": product.name,
        "batch_id": batch.id,
        "batch_number": batch.batch_number,
        "expiry_date": batch.expiry_date,
        "quantity_available": batch.quantity_available,
        "days_to_expiry": batch.days_to_expiry()
      })

  return result


@router.get("/categories", response_model=List[dict])
async def get_categories(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
  """Get product categories"""
  from sqlalchemy import func

  categories = db.query(
    Product.category,
    func.count(Product.id).label("count")
  ).filter(Product.category.isnot(None)).group_by(
    Product.category
  ).order_by(func.count(Product.id).desc()).all()

  return [{"name": cat, "count": cnt} for cat, cnt in categories]


@router.get("/{product_id}/history", response_model=List[dict])
async def get_product_history(
    product_id: int,
    days: int = Query(30, description="Number of days of history"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
  """Get product sales and movement history"""
  from app.models.order import OrderItem, Order
  from app.models.inventory import StockMovement
  from datetime import datetime, timedelta

  start_date = datetime.now() - timedelta(days=days)

  # Sales history
  sales = db.query(
    func.date(Order.order_date).label("date"),
    func.sum(OrderItem.quantity).label("quantity_sold"),
    func.sum(OrderItem.subtotal).label("revenue")
  ).join(OrderItem).filter(
    OrderItem.product_id == product_id,
    Order.status == "completed",
    Order.order_date >= start_date
  ).group_by(func.date(Order.order_date)).order_by(
    func.date(Order.order_date)
  ).all()

  # Stock movements
  movements = db.query(
    StockMovement.movement_type,
    func.sum(StockMovement.quantity).label("quantity"),
    func.date(StockMovement.created_at).label("date")
  ).join(Product).filter(
    Product.id == product_id,
    StockMovement.created_at >= start_date
  ).group_by(
    StockMovement.movement_type,
    func.date(StockMovement.created_at)
  ).order_by(func.date(StockMovement.created_at)).all()

  result = {
    "sales_history": [
      {
        "date": sale.date,
        "quantity_sold": sale.quantity_sold or 0,
        "revenue": sale.revenue or 0
      } for sale in sales
    ],
    "movement_history": [
      {
        "date": movement.date,
        "type": movement.movement_type,
        "quantity": movement.quantity
      } for movement in movements
    ]
  }

  return result