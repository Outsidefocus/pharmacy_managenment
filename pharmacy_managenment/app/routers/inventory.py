from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta
import asyncio

from app.database import get_db
from app.models.inventory import InventoryItem, StockMovement, StockMovementType
from app.models.product import Product, ProductBatch
from app.schemas.inventory import (
  InventoryItemCreate, InventoryItemUpdate, InventoryItemResponse,
  StockMovementCreate, StockMovementResponse,
  InventoryAlert, InventoryAnalysis,
  ExpiredProductsResponse
)
from app.crud.inventory_crud import (
  get_inventory_items, get_inventory_item,
  create_inventory_item, update_inventory_item,
  delete_inventory_item, create_stock_movement
)
from app.services.notification_service import NotificationService
from app.utils.security import get_current_user
from app.schemas.user import User

router = APIRouter()


@router.get("/", response_model=List[InventoryItemResponse])
async def read_inventory_items(
    skip: int = 0,
    limit: int = 100,
    category: Optional[str] = None,
    low_stock: Optional[bool] = None,
    expired: Optional[bool] = None,
    warehouse_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
  """Get all inventory items with filters"""
  items = get_inventory_items(
    db, skip=skip, limit=limit,
    category=category, low_stock=low_stock,
    expired=expired, warehouse_id=warehouse_id
  )
  return items


@router.get("/{item_id}", response_model=InventoryItemResponse)
async def read_inventory_item(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
  """Get specific inventory item"""
  item = get_inventory_item(db, item_id)
  if not item:
    raise HTTPException(status_code=404, detail="Inventory item not found")
  return item


@router.post("/", response_model=InventoryItemResponse)
async def create_inventory(
    item: InventoryItemCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
  """Create new inventory item"""
  # Check if product exists
  product = db.query(Product).filter(Product.id == item.product_id).first()
  if not product:
    raise HTTPException(status_code=404, detail="Product not found")

  # Check batch if provided
  if item.batch_id:
    batch = db.query(ProductBatch).filter(ProductBatch.id == item.batch_id).first()
    if not batch:
      raise HTTPException(status_code=404, detail="Batch not found")

  db_item = create_inventory_item(db, item)

  # Create initial stock movement
  movement_data = StockMovementCreate(
    inventory_item_id=db_item.id,
    movement_type=StockMovementType.PURCHASE,
    quantity=item.quantity,
    reference_id=None,
    reference_type="initial_stock",
    reason="Initial stock",
    user_id=current_user.id
  )
  create_stock_movement(db, movement_data)

  # Check if stock is low
  if db_item.quantity <= product.min_stock_level:
    background_tasks.add_task(
      NotificationService.send_low_stock_alert,
      db_item, product.min_stock_level
    )

  return db_item


@router.put("/{item_id}", response_model=InventoryItemResponse)
async def update_inventory(
    item_id: int,
    item_update: InventoryItemUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
  """Update inventory item"""
  db_item = update_inventory_item(db, item_id, item_update)
  if not db_item:
    raise HTTPException(status_code=404, detail="Inventory item not found")
  return db_item


@router.delete("/{item_id}")
async def delete_inventory(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
  """Delete inventory item"""
  success = delete_inventory_item(db, item_id)
  if not success:
    raise HTTPException(status_code=404, detail="Inventory item not found")
  return {"message": "Inventory item deleted successfully"}


@router.post("/movements/", response_model=StockMovementResponse)
async def create_movement(
    movement: StockMovementCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
  """Create stock movement"""
  db_movement = create_stock_movement(db, movement)
  return db_movement


@router.get("/analysis/dashboard", response_model=InventoryAnalysis)
async def get_inventory_analysis(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
  """Get inventory analysis for dashboard"""
  from sqlalchemy import func

  # Total products
  total_products = db.query(func.count(Product.id)).scalar()

  # Total inventory value
  total_value = db.query(
    func.sum(InventoryItem.quantity * Product.cost_price)
  ).join(Product).scalar() or 0

  # Low stock items
  low_stock_items = db.query(InventoryItem).join(Product).filter(
    InventoryItem.quantity <= Product.min_stock_level
  ).count()

  # Expired batches
  expired_batches = db.query(ProductBatch).filter(
    ProductBatch.expiry_date < datetime.now(),
    ProductBatch.status == "active"
  ).count()

  # Fast moving products (top 10 by turnover)
  fast_moving = db.query(
    Product.name,
    InventoryItem.turnover_rate
  ).join(InventoryItem).order_by(
    InventoryItem.turnover_rate.desc()
  ).limit(10).all()

  # Slow moving products
  slow_moving = db.query(
    Product.name,
    InventoryItem.days_in_stock
  ).join(InventoryItem).order_by(
    InventoryItem.days_in_stock.desc()
  ).limit(10).all()

  return InventoryAnalysis(
    total_products=total_products,
    total_inventory_value=total_value,
    low_stock_items=low_stock_items,
    expired_batches=expired_batches,
    fast_moving_products=[{"name": item[0], "turnover_rate": item[1]} for item in fast_moving],
    slow_moving_products=[{"name": item[0], "days_in_stock": item[1]} for item in slow_moving]
  )


@router.get("/expired/", response_model=List[ExpiredProductsResponse])
async def get_expired_products(
    days_threshold: int = Query(30, description="Days threshold for expiry warning"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
  """Get expired or soon-to-expire products"""
  current_date = datetime.now()
  warning_date = current_date + timedelta(days=days_threshold)

  expired_batches = db.query(ProductBatch).join(Product).filter(
    ProductBatch.expiry_date < current_date,
    ProductBatch.status == "active"
  ).all()

  expiring_soon = db.query(ProductBatch).join(Product).filter(
    ProductBatch.expiry_date.between(current_date, warning_date),
    ProductBatch.status == "active"
  ).all()

  result = []

  for batch in expired_batches:
    result.append(ExpiredProductsResponse(
      product_id=batch.product_id,
      product_name=batch.product.name,
      batch_number=batch.batch_number,
      expiry_date=batch.expiry_date,
      quantity_available=batch.quantity_available,
      status="expired",
      days_to_expiry=0
    ))

  for batch in expiring_soon:
    days = (batch.expiry_date - current_date).days
    result.append(ExpiredProductsResponse(
      product_id=batch.product_id,
      product_name=batch.product.name,
      batch_number=batch.batch_number,
      expiry_date=batch.expiry_date,
      quantity_available=batch.quantity_available,
      status="expiring_soon",
      days_to_expiry=days
    ))

  return result


@router.post("/check-expiry/", response_model=dict)
async def check_and_notify_expiry(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
  """Check for expired products and send notifications"""
  expired_products = await get_expired_products(db=db, current_user=current_user)

  for product in expired_products:
    if product.status == "expired":
      # Send notifications for expired products
      background_tasks.add_task(
        NotificationService.send_expiry_notification,
        product, "expired"
      )
    elif product.status == "expiring_soon" and product.days_to_expiry <= 7:
      # Send warning for products expiring within 7 days
      background_tasks.add_task(
        NotificationService.send_expiry_notification,
        product, "warning"
      )

  return {
    "message": f"Checked {len(expired_products)} products for expiry",
    "notifications_sent": len(expired_products)
  }


@router.get("/stock-levels/", response_model=List[dict])
async def get_stock_levels(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
  """Get stock levels for all products"""
  items = db.query(
    Product.id,
    Product.name,
    Product.category,
    Product.min_stock_level,
    Product.max_stock_level,
    func.coalesce(func.sum(InventoryItem.quantity), 0).label("current_stock")
  ).outerjoin(InventoryItem).group_by(
    Product.id
  ).all()

  result = []
  for item in items:
    stock_percentage = (item.current_stock / item.max_stock_level * 100) if item.max_stock_level > 0 else 0
    status = "normal"
    if item.current_stock <= item.min_stock_level:
      status = "low"
    elif item.current_stock >= item.max_stock_level * 0.9:
      status = "high"

    result.append({
      "product_id": item.id,
      "product_name": item.name,
      "category": item.category,
      "min_stock": item.min_stock_level,
      "max_stock": item.max_stock_level,
      "current_stock": item.current_stock,
      "stock_percentage": stock_percentage,
      "status": status,
      "needs_restock": item.current_stock <= item.min_stock_level
    })

  return result


@router.get("/turnover-analysis/", response_model=List[dict])
async def turnover_analysis(
    days: int = Query(365, description="Analysis period in days"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
  """Analyze product turnover rates"""
  from sqlalchemy import func, extract

  # Calculate sales in the period
  sales_subquery = db.query(
    OrderItem.product_id,
    func.sum(OrderItem.quantity).label("total_sold")
  ).join(Order).filter(
    Order.order_date >= datetime.now() - timedelta(days=days),
    Order.status == "completed"
  ).group_by(OrderItem.product_id).subquery()

  # Get inventory data
  products = db.query(
    Product.id,
    Product.name,
    Product.category,
    func.avg(InventoryItem.quantity).label("avg_inventory"),
    func.coalesce(sales_subquery.c.total_sold, 0).label("total_sold")
  ).outerjoin(InventoryItem).outerjoin(
    sales_subquery, Product.id == sales_subquery.c.product_id
  ).group_by(Product.id).all()

  result = []
  for product in products:
    avg_inventory = product.avg_inventory or 1
    turnover_rate = (product.total_sold / avg_inventory) * (365 / days)

    classification = "slow"
    if turnover_rate > 12:
      classification = "fast"
    elif turnover_rate > 6:
      classification = "medium"

    result.append({
      "product_id": product.id,
      "product_name": product.name,
      "category": product.category,
      "avg_inventory": avg_inventory,
      "total_sold": product.total_sold,
      "turnover_rate": round(turnover_rate, 2),
      "classification": classification,
      "suggested_action": "Increase stock" if classification == "fast" else "Review stock"
    })

  return sorted(result, key=lambda x: x["turnover_rate"], reverse=True)