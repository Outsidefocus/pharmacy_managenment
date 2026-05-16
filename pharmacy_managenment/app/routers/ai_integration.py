from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Dict, Any

from app.database import get_db
from app.services.ai_service import AIService
from app.utils.security import get_current_user, require_permission
from app.schemas.user import User
from app.models.product import Product
from app.models.order import Order, OrderItem
from app.models.customer import Customer

router = APIRouter()
ai_service = AIService()


@router.post("/analyze-market")
async def analyze_market_trends(
    category: str = None,
    days: int = 90,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("view_analytics"))
):
  """Analyze market trends based on sales data"""
  from datetime import datetime, timedelta

  start_date = datetime.now() - timedelta(days=days)

  # Fetch product sales data
  query = db.query(
    Product.id,
    Product.name,
    Product.category,
    Product.selling_price,
    Product.cost_price,
    OrderItem.quantity,
    Order.order_date
  ).join(OrderItem).join(Order).filter(
    Order.status == "completed",
    Order.order_date >= start_date
  )

  if category:
    query = query.filter(Product.category == category)

  results = query.limit(500).all()  # Limit to avoid overwhelming

  product_data = []
  for r in results:
    product_data.append({
      "product_id": r.id,
      "name": r.name,
      "category": r.category,
      "price": r.selling_price,
      "cost": r.cost_price,
      "quantity_sold": r.quantity,
      "sale_date": r.order_date.isoformat()
    })

  # Perform analysis in background
  background_tasks.add_task(
    ai_service.analyze_market_trends,
    product_data
  )

  return {"message": "Market analysis started", "data_points": len(product_data)}


@router.post("/predict-demand/{product_id}")
async def predict_demand(
    product_id: int,
    days_ahead: int = 30,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("view_analytics"))
):
  """Predict demand for a specific product"""
  from datetime import datetime, timedelta

  # Fetch historical sales data for the product
  start_date = datetime.now() - timedelta(days=365)

  sales = db.query(
    Order.order_date,
    OrderItem.quantity
  ).join(OrderItem).filter(
    OrderItem.product_id == product_id,
    Order.status == "completed",
    Order.order_date >= start_date
  ).order_by(Order.order_date).all()

  historical_data = [
    {"date": s.order_date.isoformat(), "quantity": s.quantity}
    for s in sales
  ]

  prediction = await ai_service.predict_demand(
    product_id,
    historical_data
  )

  return prediction


@router.post("/optimize-pricing")
async def optimize_pricing(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("manage_pricing"))
):
  """Get pricing optimization recommendations"""
  product = db.query(Product).filter(Product.id == product_id).first()
  if not product:
    raise HTTPException(status_code=404, detail="Product not found")

  # Get competitor/market data (mock)
  market_data = await ai_service.get_google_market_data(product.name)

  optimization = await ai_service.optimize_pricing(
    product_info={
      "id": product.id,
      "name": product.name,
      "category": product.category,
      "current_price": product.selling_price,
      "cost_price": product.cost_price,
      "sales_history": []  # Could add recent sales
    },
    market_data=market_data
  )

  return optimization


@router.post("/customer-insights")
async def customer_insights(
    customer_id: int = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("view_analytics"))
):
  """Generate customer insights and marketing suggestions"""
  if customer_id:
    customers = [db.query(Customer).filter(Customer.id == customer_id).first()]
  else:
    customers = db.query(Customer).limit(50).all()

  customer_data = []
  for c in customers:
    if not c:
      continue
    # Get order summary
    orders = db.query(Order).filter(Order.customer_id == c.id).count()
    spent = c.total_spent
    customer_data.append({
      "id": c.id,
      "name": f"{c.first_name} {c.last_name}",
      "email": c.email,
      "total_orders": orders,
      "total_spent": spent,
      "avg_order_value": c.average_order_value,
      "last_visit": c.last_visit_date.isoformat() if c.last_visit_date else None
    })

  insights = await ai_service.generate_marketing_insights(customer_data)
  return insights