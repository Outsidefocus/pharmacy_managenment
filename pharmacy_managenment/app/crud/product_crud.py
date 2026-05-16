from datetime import datetime, timedelta

from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any
from sqlalchemy import or_, func, desc, asc
from app.models.product import Product, ProductBatch
from app.schemas.product import ProductCreate, ProductUpdate, ProductBatchCreate
import logging

logger = logging.getLogger(__name__)


def get_product(db: Session, product_id: int) -> Optional[Product]:
  """Get product by ID"""
  return db.query(Product).filter(product_id == Product.id).first()


def get_product_by_sku(db: Session, sku: str) -> Optional[Product]:
  """Get product by SKU"""
  return db.query(Product).filter(sku == Product.sku).first()


def get_product_by_barcode(db: Session, barcode: str) -> Optional[Product]:
  """Get product by barcode"""
  return db.query(Product).filter(barcode == Product.barcode).first()


def get_products(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    category: Optional[str] = None,
    requires_prescription: Optional[bool] = None,
    search: Optional[str] = None
) -> list[type[Product]]:
  """Get products with filters"""
  query = db.query(Product)

  if category:
    query = query.filter(category == Product.category)

  if requires_prescription is not None:
    query = query.filter(requires_prescription == Product.requires_prescription)

  if search:
    query = query.filter(
      or_(
        Product.name.ilike(f"%{search}%"),
        Product.generic_name.ilike(f"%{search}%"),
        Product.sku.ilike(f"%{search}%"),
        Product.barcode.ilike(f"%{search}%")
      )
    )

  return query.offset(skip).limit(limit).all()


def create_product(db: Session, product: ProductCreate) -> Product:
  """Create new product"""
  db_product = Product(**product.dict())
  db.add(db_product)
  db.commit()
  db.refresh(db_product)
  logger.info(f"Created product: {product.name}")
  return db_product


def update_product(db: Session, product_id: int, product_update: ProductUpdate) -> Optional[Product]:
  """Update product"""
  db_product = get_product(db, product_id)
  if not db_product:
    return None

  update_data = product_update.dict(exclude_unset=True)

  for field, value in update_data.items():
    setattr(db_product, field, value)

  db.commit()
  db.refresh(db_product)
  logger.info(f"Updated product: {db_product.name}")
  return db_product


def delete_product(db: Session, product_id: int) -> bool:
  """Delete product"""
  db_product = get_product(db, product_id)
  if not db_product:
    return False

  db.delete(db_product)
  db.commit()
  logger.info(f"Deleted product: {db_product.name}")
  return True


def create_product_batch(db: Session, batch: ProductBatchCreate) -> ProductBatch:
  """Create new product batch"""
  db_batch = ProductBatch(**batch.dict())
  db.add(db_batch)
  db.commit()
  db.refresh(db_batch)
  logger.info(f"Created batch: {batch.batch_number} for product {batch.product_id}")
  return db_batch


def update_product_batch(db: Session, batch_id: int, batch_update: Dict[str, Any]) -> type[ProductBatch] | None:
  """Update product batch"""
  db_batch = db.query(ProductBatch).filter(batch_id == ProductBatch.id).first()
  if not db_batch:
    return None

  for field, value in batch_update.items():
    setattr(db_batch, field, value)

  db.commit()
  db.refresh(db_batch)
  return db_batch


def get_expiring_products(db: Session, days_threshold: int = 30) -> list[type[ProductBatch]]:
  """Get products expiring within specified days"""
  from datetime import datetime, timedelta
  threshold_date = datetime.now() + timedelta(days=days_threshold)

  return db.query(ProductBatch).filter(
    ProductBatch.expiry_date <= threshold_date,
    ProductBatch.status == "active",
    ProductBatch.quantity_available > 0
  ).all()


def get_low_stock_products(db: Session) -> List[Dict[str, Any]]:
  """Get products with low stock"""
  from app.models.inventory import InventoryItem

  low_stock = db.query(
    Product.id,
    Product.name,
    Product.sku,
    Product.category,
    Product.min_stock_level,
    func.coalesce(func.sum(InventoryItem.quantity), 0).label("current_stock")
  ).outerjoin(InventoryItem).group_by(Product.id).having(
    func.coalesce(func.sum(InventoryItem.quantity), 0) <= Product.min_stock_level
  ).all()

  result = []
  for item in low_stock:
    result.append({
      "product_id": item.id,
      "product_name": item.name,
      "sku": item.sku,
      "category": item.category,
      "min_stock": item.min_stock_level,
      "current_stock": item.current_stock,
      "needed": item.min_stock_level - item.current_stock if item.current_stock < item.min_stock_level else 0
    })

  return result


def get_product_stats(db: Session) -> Dict[str, Any]:
  """Get product statistics"""
  from app.models.inventory import InventoryItem

  total_products = db.query(func.count(Product.id)).scalar()

  # Total inventory value
  total_value = db.query(
    func.sum(InventoryItem.quantity * Product.cost_price)
  ).join(Product).scalar() or 0

  # Categories
  categories = db.query(
    Product.category,
    func.count(Product.id).label("count")
  ).filter(Product.category.isnot(None)).group_by(Product.category).all()

  # Low stock count
  low_stock_count = len(get_low_stock_products(db))

  # Expired batches count
  expired_count = db.query(func.count(ProductBatch.id)).filter(
    ProductBatch.expiry_date < datetime.now(),
    ProductBatch.status == "active"
  ).scalar()

  # Fast moving products (top 5 by sales)
  from app.models.order import OrderItem, Order
  fast_moving = db.query(
    Product.name,
    func.sum(OrderItem.quantity).label("total_sold")
  ).join(OrderItem).join(Order).filter(
    Order.status == "completed",
    Order.order_date >= datetime.now() - timedelta(days=30)
  ).group_by(Product.id).order_by(desc("total_sold")).limit(5).all()

  # Slow moving products (no sales in last 90 days)
  slow_moving = db.query(Product).filter(
    ~Product.id.in_(
      db.query(OrderItem.product_id).join(Order).filter(
        Order.status == "completed",
        Order.order_date >= datetime.now() - timedelta(days=90)
      ).subquery()
    )
  ).limit(5).all()

  return {
    "total_products": total_products,
    "total_value": total_value,
    "categories": [{"name": cat, "count": cnt} for cat, cnt in categories],
    "low_stock_count": low_stock_count,
    "expired_count": expired_count,
    "fast_moving": [{"name": name, "sold": sold} for name, sold in fast_moving],
    "slow_moving": [{"name": p.name, "id": p.id} for p in slow_moving]
  }


def search_products(
    db: Session,
    search_term: str,
    category: Optional[str] = None,
    requires_prescription: Optional[bool] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    in_stock: Optional[bool] = None,
    sort_by: str = "name",
    sort_order: str = "asc",
    skip: int = 0,
    limit: int = 50
) -> list[type[Product]]:
  """Advanced product search"""
  from app.models.inventory import InventoryItem

  query = db.query(Product)

  # Search term
  if search_term:
    query = query.filter(
      or_(
        Product.name.ilike(f"%{search_term}%"),
        Product.generic_name.ilike(f"%{search_term}%"),
        Product.sku.ilike(f"%{search_term}%"),
        Product.barcode.ilike(f"%{search_term}%"),
        Product.description.ilike(f"%{search_term}%")
      )
    )

  # Filters
  if category:
    query = query.filter(category == Product.category)

  if requires_prescription is not None:
    query = query.filter(requires_prescription == Product.requires_prescription)

  if min_price is not None:
    query = query.filter(Product.selling_price >= min_price)

  if max_price is not None:
    query = query.filter(Product.selling_price <= max_price)

  # In stock filter
  if in_stock is not None:
    if in_stock:
      query = query.join(InventoryItem).filter(InventoryItem.quantity > 0)
    else:
      query = query.outerjoin(InventoryItem).filter(
        (InventoryItem.quantity == 0) | (InventoryItem.id.is_(None))
      )

  # Sorting
  if sort_by == "price":
    if sort_order == "asc":
      query = query.order_by(Product.selling_price.asc())
    else:
      query = query.order_by(Product.selling_price.desc())
  elif sort_by == "name":
    if sort_order == "asc":
      query = query.order_by(Product.name.asc())
    else:
      query = query.order_by(Product.name.desc())
  elif sort_by == "created":
    if sort_order == "asc":
      query = query.order_by(Product.created_at.asc())
    else:
      query = query.order_by(Product.created_at.desc())

  return query.offset(skip).limit(limit).all()