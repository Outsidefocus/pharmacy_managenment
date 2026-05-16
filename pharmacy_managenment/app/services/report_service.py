from sqlalchemy.orm import Session
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import pandas as pd
import json
import os

from app.models.order import Order, OrderItem
from app.models.product import Product
from app.models.customer import Customer
from app.models.payment import Payment
from app.database import get_db


class ReportService:
  async def generate_sales_report(
      self,
      start_date: datetime,
      end_date: datetime,
      group_by: str = "day",
      pharmacy_branch_id: Optional[int] = None,
      db: Session = None
  ) -> Dict[str, Any]:
    """Generate sales report"""
    if db is None:
      db = next(get_db())

    from sqlalchemy import func

    # Base query
    query = db.query(
      Order.order_date,
      Order.total_amount,
      Order.id.label("order_id")
    ).filter(
      Order.status == "completed",
      Order.order_date >= start_date,
      Order.order_date <= end_date
    )

    if pharmacy_branch_id:
      query = query.filter(Order.pharmacy_branch_id == pharmacy_branch_id)

    orders = query.all()

    # Group data
    if group_by == "day":
      grouped = {}
      for order in orders:
        day = order.order_date.date()
        if day not in grouped:
          grouped[day] = {"count": 0, "revenue": 0.0}
        grouped[day]["count"] += 1
        grouped[day]["revenue"] += order.total_amount or 0
    elif group_by == "hour":
      grouped = {}
      for order in orders:
        hour = order.order_date.replace(minute=0, second=0, microsecond=0)
        if hour not in grouped:
          grouped[hour] = {"count": 0, "revenue": 0.0}
        grouped[hour]["count"] += 1
        grouped[hour]["revenue"] += order.total_amount or 0
    else:
      grouped = {"total": {"count": len(orders), "revenue": sum(o.total_amount or 0 for o in orders)}}

    # Top products
    top_products = db.query(
      Product.name,
      func.sum(OrderItem.quantity).label("total_sold"),
      func.sum(OrderItem.subtotal).label("total_revenue")
    ).join(OrderItem).join(Order).filter(
      Order.status == "completed",
      Order.order_date >= start_date,
      Order.order_date <= end_date
    ).group_by(Product.id).order_by(func.sum(OrderItem.quantity).desc()).limit(10).all()

    # Summary
    summary = {
      "total_orders": len(orders),
      "total_revenue": sum(o.total_amount or 0 for o in orders),
      "average_order_value": sum(o.total_amount or 0 for o in orders) / len(orders) if orders else 0,
      "start_date": start_date.isoformat(),
      "end_date": end_date.isoformat(),
    }

    return {
      "summary": summary,
      "grouped_data": {str(k): v for k, v in grouped.items()},
      "top_products": [
        {"name": p.name, "sold": p.total_sold, "revenue": float(p.total_revenue or 0)}
        for p in top_products
      ]
    }

  async def generate_inventory_report(
      self,
      report_type: str = "stock_levels",
      category: Optional[str] = None,
      warehouse_id: Optional[int] = None,
      db: Session = None
  ) -> Dict[str, Any]:
    """Generate inventory report"""
    if db is None:
      db = next(get_db())

    from app.models.inventory import InventoryItem
    from sqlalchemy import func

    query = db.query(
      Product.id,
      Product.name,
      Product.category,
      Product.sku,
      Product.cost_price,
      Product.selling_price,
      Product.min_stock_level,
      func.coalesce(func.sum(InventoryItem.quantity), 0).label("current_stock")
    ).outerjoin(InventoryItem).group_by(Product.id)

    if category:
      query = query.filter(Product.category == category)

    products = query.all()

    # Calculate metrics
    total_value = sum(p.current_stock * (p.cost_price or 0) for p in products)
    retail_value = sum(p.current_stock * (p.selling_price or 0) for p in products)

    low_stock_items = [p for p in products if p.current_stock <= (p.min_stock_level or 0)]

    # Stock by category
    category_stock = {}
    for p in products:
      cat = p.category or "Uncategorized"
      if cat not in category_stock:
        category_stock[cat] = {"quantity": 0, "value": 0.0}
      category_stock[cat]["quantity"] += p.current_stock
      category_stock[cat]["value"] += p.current_stock * (p.cost_price or 0)

    return {
      "report_type": report_type,
      "summary": {
        "total_products": len(products),
        "total_units": sum(p.current_stock for p in products),
        "total_cost_value": float(total_value),
        "total_retail_value": float(retail_value),
        "low_stock_count": len(low_stock_items)
      },
      "category_breakdown": category_stock,
      "low_stock_items": [
        {
          "id": p.id,
          "name": p.name,
          "sku": p.sku,
          "current_stock": p.current_stock,
          "min_stock": p.min_stock_level
        } for p in low_stock_items
      ]
    }

  async def generate_financial_summary(
      self,
      start_date: datetime,
      end_date: datetime,
      db: Session = None
  ) -> Dict[str, Any]:
    """Generate financial summary (profit/loss)"""
    if db is None:
      db = next(get_db())

    from app.models.payment import Payment, Expense
    from sqlalchemy import func

    # Revenue
    revenue = db.query(
      func.sum(Payment.amount).label("total")
    ).filter(
      Payment.payment_status == "completed",
      Payment.is_refund == False,
      Payment.payment_date >= start_date,
      Payment.payment_date <= end_date
    ).scalar() or 0

    # Refunds
    refunds = db.query(
      func.sum(Payment.amount).label("total")
    ).filter(
      Payment.payment_status == "completed",
      Payment.is_refund == True,
      Payment.payment_date >= start_date,
      Payment.payment_date <= end_date
    ).scalar() or 0

    # Expenses
    expenses = db.query(
      func.sum(Expense.amount).label("total")
    ).filter(
      Expense.payment_status == "paid",
      Expense.paid_date >= start_date,
      Expense.paid_date <= end_date
    ).scalar() or 0

    # Gross profit (simplified)
    # Need cost of goods sold
    cost_of_goods = db.query(
      func.sum(OrderItem.quantity * Product.cost_price)
    ).join(OrderItem).join(Order).join(Product).filter(
      Order.status == "completed",
      Order.completed_date >= start_date,
      Order.completed_date <= end_date
    ).scalar() or 0

    gross_profit = revenue - cost_of_goods - refunds
    net_profit = gross_profit - expenses

    return {
      "period": {
        "start": start_date.isoformat(),
        "end": end_date.isoformat()
      },
      "revenue": float(revenue),
      "refunds": float(refunds),
      "cost_of_goods_sold": float(cost_of_goods),
      "gross_profit": float(gross_profit),
      "expenses": float(expenses),
      "net_profit": float(net_profit)
    }

  async def generate_customer_report(
      self,
      start_date: Optional[datetime] = None,
      end_date: Optional[datetime] = None,
      db: Session = None
  ) -> Dict[str, Any]:
    """Generate customer analysis report"""
    if db is None:
      db = next(get_db())

    from sqlalchemy import func

    # Customer acquisition
    total_customers = db.query(func.count(Customer.id)).scalar()

    if start_date and end_date:
      new_customers = db.query(func.count(Customer.id)).filter(
        Customer.registration_date >= start_date,
        Customer.registration_date <= end_date
      ).scalar() or 0
    else:
      new_customers = 0

    # Top customers by spending
    top_customers = db.query(
      Customer.id,
      Customer.first_name,
      Customer.last_name,
      Customer.total_spent,
      Customer.total_orders
    ).order_by(Customer.total_spent.desc()).limit(10).all()

    # Customer segmentation
    vip = db.query(func.count(Customer.id)).filter("vip" == Customer.customer_type).scalar() or 0
    wholesale = db.query(func.count(Customer.id)).filter("wholesale" == Customer.customer_type).scalar() or 0
    regular = total_customers - vip - wholesale

    return {
      "summary": {
        "total_customers": total_customers,
        "new_customers": new_customers,
        "average_order_value": db.query(func.avg(Customer.average_order_value)).scalar() or 0,
        "total_revenue": db.query(func.sum(Customer.total_spent)).scalar() or 0
      },
      "segments": {
        "vip": vip,
        "wholesale": wholesale,
        "regular": regular
      },
      "top_customers": [
        {
          "id": c.id,
          "name": f"{c.first_name} {c.last_name}",
          "total_spent": float(c.total_spent or 0),
          "total_orders": c.total_orders
        } for c in top_customers
      ]
    }