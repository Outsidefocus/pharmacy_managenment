from fastapi import Depends, Query
from sqlalchemy.orm import Session
from typing import Optional
from app.models.user import User
from app.database import get_db
from app.routers.auth import router
from app.utils.security import get_current_user


@router.get("/most-sold-items")
async def get_most_sold_items(
    days: int = Query(30, description="Number of days to analyze"),
    limit: int = Query(10, description="Number of items to return"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
  """Get most sold items in a period"""
  from app.models.order import Order, OrderItem
  from app.models.product import Product
  from sqlalchemy import func, desc
  from datetime import datetime, timedelta

  start_date = datetime.now() - timedelta(days=days)

  most_sold = db.query(
    Product.id,
    Product.name,
    Product.category,
    func.sum(OrderItem.quantity).label("total_sold"),
    func.sum(OrderItem.subtotal).label("total_revenue"),
    func.avg(OrderItem.unit_price).label("avg_price")
  ).join(OrderItem).join(Order).filter(
    "completed" == Order.status,
    Order.order_date >= start_date
  ).group_by(
    Product.id, Product.name, Product.category
  ).order_by(
    desc("total_sold")
  ).limit(limit).all()

  result = []
  for item in most_sold:
    result.append({
      "product_id": item.id,
      "product_name": item.name,
      "category": item.category,
      "total_sold": item.total_sold or 0,
      "total_revenue": float(item.total_revenue or 0),
      "average_price": float(item.avg_price or 0),
      "percentage_of_sales": 0  # Will calculate below
    })

  # Calculate total sales for percentage
  total_sales = sum(item["total_revenue"] for item in result)
  if total_sales > 0:
    for item in result:
      item["percentage_of_sales"] = round((item["total_revenue"] / total_sales) * 100, 2)

  return result


@router.get("/average-items-per-order")
async def get_average_items_per_order(
    days: int = Query(30, description="Number of days to analyze"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
  """Get average items per order"""
  from app.models.order import Order, OrderItem
  from sqlalchemy import func
  from datetime import datetime, timedelta

  start_date = datetime.now() - timedelta(days=days)

  # Get statistics
  stats = db.query(
    func.count(Order.id).label("total_orders"),
    func.sum(OrderItem.quantity).label("total_items"),
    func.avg(OrderItem.quantity).label("avg_items_per_order"),
    func.min(OrderItem.quantity).label("min_items"),
    func.max(OrderItem.quantity).label("max_items")
  ).join(OrderItem).filter(
    "completed" == Order.status,
    Order.order_date >= start_date
  ).first()

  # Get most common number of items
  item_counts = db.query(
    OrderItem.quantity,
    func.count(OrderItem.id).label("frequency")
  ).join(Order).filter(
    "completed" == Order.status,
    Order.order_date >= start_date
  ).group_by(
    OrderItem.quantity
  ).order_by(
    func.count(OrderItem.quantity).desc()
  ).limit(5).all()

  return {
    "period_days": days,
    "total_orders": stats.total_orders or 0,
    "total_items_sold": stats.total_items or 0,
    "average_items_per_order": float(stats.avg_items_per_order or 0),
    "minimum_items_in_order": stats.min_items or 0,
    "maximum_items_in_order": stats.max_items or 0,
    "most_common_item_counts": [
      {"quantity": count, "frequency": freq}
      for count, freq in item_counts
    ]
  }


@router.get("/product-performance")
async def get_product_performance(
    product_id: Optional[int] = None,
    category: Optional[str] = None,
    days: int = Query(30, description="Number of days to analyze"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
  """Get detailed product performance metrics"""
  from app.models.order import Order, OrderItem
  from app.models.product import Product
  from sqlalchemy import func, case, desc
  from datetime import datetime, timedelta

  start_date = datetime.now() - timedelta(days=days)

  # Base query
  query = db.query(
    Product.id,
    Product.name,
    Product.category,
    Product.selling_price,
    Product.cost_price,
    func.count(OrderItem.id).label("times_sold"),
    func.sum(OrderItem.quantity).label("total_quantity_sold"),
    func.sum(OrderItem.subtotal).label("total_revenue"),
    func.avg(OrderItem.quantity).label("avg_quantity_per_sale"),
    (func.sum(OrderItem.subtotal) / func.sum(OrderItem.quantity)).label("effective_price")
  ).join(OrderItem).join(Order).filter(
    "completed" == Order.status,
    Order.order_date >= start_date
  )

  # Apply filters
  if product_id:
    query = query.filter(product_id == Product.id)

  if category:
    query = query.filter(category == Product.category)

  products = query.group_by(
    Product.id, Product.name, Product.category,
    Product.selling_price, Product.cost_price
  ).order_by(desc("total_revenue")).all()

  result = []
  for p in products:
    profit_margin = 0
    if p.cost_price and p.cost_price > 0:
      effective_price = p.effective_price or p.selling_price
      profit_margin = ((effective_price - p.cost_price) / p.cost_price) * 100

    result.append({
      "product_id": p.id,
      "product_name": p.name,
      "category": p.category,
      "times_sold": p.times_sold or 0,
      "total_quantity_sold": p.total_quantity_sold or 0,
      "total_revenue": float(p.total_revenue or 0),
      "average_quantity_per_sale": float(p.avg_quantity_per_sale or 0),
      "selling_price": float(p.selling_price or 0),
      "cost_price": float(p.cost_price or 0),
      "effective_price": float(p.effective_price or p.selling_price or 0),
      "profit_margin_percentage": round(profit_margin, 2),
      "total_profit": float((p.total_revenue or 0) - ((p.cost_price or 0) * (p.total_quantity_sold or 0)))
    })

  return result