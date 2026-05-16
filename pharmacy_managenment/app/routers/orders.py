from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta

from app.database import get_db
from app.models.customer import Customer
from app.models.order import Order, OrderItem, OrderStatus, PaymentStatus, OrderType
from app.models.product import Product
from app.models.inventory import InventoryItem, StockMovement, StockMovementType
from app.schemas.order import (
  OrderCreate, OrderUpdate, OrderResponse,
  OrderItemResponse, OrderStats, OrderSearch
)
from app.utils.security import get_current_user, require_permission
from app.models.user import User
from app.services.notification_service import NotificationService
from app.utils.helpers import generate_order_number
from sqlalchemy.sql import func

router = APIRouter()


@router.get("/", response_model=List[OrderResponse])
async def read_orders(
    skip: int = 0,
    limit: int = 100,
    status: Optional[OrderStatus] = None,
    order_type: Optional[OrderType] = None,
    customer_id: Optional[int] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
  """Get all orders"""
  query = db.query(Order)

  if status:
    query = query.filter(status == Order.status)

  if order_type:
    query = query.filter(order_type == Order.order_type)

  if customer_id:
    query = query.filter(customer_id == Order.customer_id)

  if start_date:
    query = query.filter(Order.order_date >= start_date)

  if end_date:
    query = query.filter(Order.order_date <= end_date)

  orders = query.order_by(Order.order_date.desc()).offset(skip).limit(limit).all()
  return orders


@router.get("/search", response_model=List[OrderResponse])
async def search_orders(
    search_query: OrderSearch = Depends(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
  """Search orders"""
  query = db.query(Order)

  if search_query.search_term:
    query = query.filter(
      (Order.order_number.ilike(f"%{search_query.search_term}%")) |
      (Order.customer_name.ilike(f"%{search_query.search_term}%"))
    )

  if search_query.status:
    query = query.filter(search_query.status == Order.status)

  if search_query.order_type:
    query = query.filter(search_query.order_type == Order.order_type)

  if search_query.customer_id:
    query = query.filter(search_query.customer_id == Order.customer_id)

  if search_query.start_date:
    query = query.filter(Order.order_date >= search_query.start_date)

  if search_query.end_date:
    query = query.filter(Order.order_date <= search_query.end_date)

  if search_query.min_amount:
    query = query.filter(Order.total_amount >= search_query.min_amount)

  if search_query.max_amount:
    query = query.filter(Order.total_amount <= search_query.max_amount)

  # Sorting
  if search_query.sort_by == "amount":
    if search_query.sort_order == "asc":
      query = query.order_by(Order.total_amount.asc())
    else:
      query = query.order_by(Order.total_amount.desc())
  else:  # order_date
    if search_query.sort_order == "asc":
      query = query.order_by(Order.order_date.asc())
    else:
      query = query.order_by(Order.order_date.desc())

  orders = query.all()
  return orders


@router.get("/{order_id}", response_model=OrderResponse)
async def read_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
  """Get order by ID"""
  order = db.query(Order).filter(order_id == Order.id).first()
  if not order:
    raise HTTPException(status_code=404, detail="Order not found")
  return order


@router.post("/", response_model=OrderResponse)
async def create_order(
    order: OrderCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("create_orders"))
):
  """Create new order"""
  # Generate order number
  order_number = generate_order_number(db)

  # Create order
  db_order = Order(
    order_number=order_number,
    pharmacist_id=current_user.id,
    **order.dict(exclude={'items'})
  )

  db.add(db_order)
  db.commit()
  db.refresh(db_order)

  # Add order items
  total_amount = 0
  for item_data in order.items:
    product = db.query(Product).filter(Product.id == item_data['product_id']).first()
    if not product:
      raise HTTPException(status_code=404, detail=f"Product {item_data['product_id']} not found")

    # Calculate item subtotal
    unit_price = item_data.get('unit_price', product.selling_price)
    quantity = item_data['quantity']
    discount_percentage = item_data.get('discount_percentage', 0.0)

    base_amount = unit_price * quantity
    discount_amount = base_amount * (discount_percentage / 100)
    subtotal = base_amount - discount_amount

    order_item = OrderItem(
      order_id=db_order.id,
      product_id=product.id,
      product_name=product.name,
      product_sku=product.sku,
      unit_price=unit_price,
      quantity=quantity,
      discount_percentage=discount_percentage,
      discount_amount=discount_amount,
      subtotal=subtotal,
      prescription_item_id=item_data.get('prescription_item_id')
    )

    db.add(order_item)
    total_amount += subtotal

  # Update order totals
  db_order.subtotal = total_amount
  db_order.total_amount = total_amount  # Assuming no tax/shipping for now
  db_order.amount_due = total_amount

  db.commit()
  db.refresh(db_order)

  # Send order confirmation if customer email exists
  if db_order.customer_id:
    customer = db.query(Customer).filter(db_order.customer_id == Customer.id).first()
    if customer and customer.email:
      background_tasks.add_task(
        NotificationService.send_order_confirmation,
        customer.email,
        customer.full_name,
        {
          'order_number': db_order.order_number,
          'order_date': db_order.order_date,
          'total_amount': db_order.total_amount,
          'items': [
            {
              'name': item.product_name,
              'quantity': item.quantity,
              'price': item.subtotal
            } for item in db_order.order_items
          ]
        }
      )

  return db_order


@router.put("/{order_id}", response_model=OrderResponse)
async def update_order(
    order_id: int,
    order_update: OrderUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("manage_orders"))
):
  """Update order"""
  db_order = db.query(Order).filter(order_id == Order.id).first()
  if not db_order:
    raise HTTPException(status_code=404, detail="Order not found")

  update_data = order_update.dict(exclude_unset=True)

  # Handle status changes
  if 'status' in update_data:
    old_status = db_order.status
    new_status = update_data['status']

    # If order is being cancelled
    if new_status == OrderStatus.CANCELLED and old_status != OrderStatus.CANCELLED:
      update_data['cancelled_date'] = datetime.now()

      # Restore inventory if items were reserved
      for item in db_order.order_items:
        if item.inventory_item_id:
          inventory_item = db.query(InventoryItem).filter(
            InventoryItem.id == item.inventory_item_id
          ).first()
          if inventory_item:
            inventory_item.reserved_quantity -= item.quantity

            # Create stock movement for cancellation
            movement = StockMovement(
              inventory_item_id=inventory_item.id,
              movement_type=StockMovementType.RETURN,
              quantity=item.quantity,
              previous_quantity=inventory_item.quantity,
              new_quantity=inventory_item.quantity,
              reference_id=order_id,
              reference_type="order_cancellation",
              reason="Order cancelled",
              user_id=current_user.id
            )
            db.add(movement)

    # If order is being completed
    elif new_status == OrderStatus.COMPLETED and old_status != OrderStatus.COMPLETED:
      update_data['completed_date'] = datetime.now()

      # Update customer statistics
      if db_order.customer_id:
        customer = db.query(Customer).filter(Customer.id == db_order.customer_id).first()
        if customer:
          customer.update_statistics(db_order.total_amount)

  for field, value in update_data.items():
    setattr(db_order, field, value)

  db.commit()
  db.refresh(db_order)

  return db_order


@router.post("/{order_id}/process")
async def process_order(
    order_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("process_orders"))
):
  """Process order (pick items from inventory)"""
  order = db.query(Order).filter(Order.id == order_id).first()
  if not order:
    raise HTTPException(status_code=404, detail="Order not found")

  if order.status != OrderStatus.CONFIRMED:
    raise HTTPException(
      status_code=400,
      detail=f"Order must be in CONFIRMED status. Current status: {order.status}"
    )

  # Check and reserve inventory for each item
  for order_item in order.order_items:
    # Find available inventory
    inventory_items = db.query(InventoryItem).join(Product).filter(
      Product.id == order_item.product_id,
      InventoryItem.quantity > 0
    ).order_by(
      InventoryItem.created_at.asc()  # FIFO
    ).all()

    if not inventory_items:
      raise HTTPException(
        status_code=400,
        detail=f"Insufficient stock for product: {order_item.product_name}"
      )

    quantity_needed = order_item.quantity
    for inv_item in inventory_items:
      if quantity_needed <= 0:
        break

      available = inv_item.available_quantity
      if available > 0:
        quantity_to_reserve = min(available, quantity_needed)
        inv_item.reserved_quantity += quantity_to_reserve
        quantity_needed -= quantity_to_reserve

        # Link inventory item to order item
        order_item.inventory_item_id = inv_item.id
        order_item.picked_quantity = quantity_to_reserve

    if quantity_needed > 0:
      raise HTTPException(
        status_code=400,
        detail=f"Insufficient stock for product: {order_item.product_name}"
      )

  # Update order status
  order.status = OrderStatus.PROCESSING

  db.commit()

  return {"message": "Order processed successfully", "order_id": order_id}


@router.post("/{order_id}/dispense")
async def dispense_order(
    order_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("dispense_orders"))
):
  """Dispense order (finalize and update inventory)"""
  order = db.query(Order).filter(Order.id == order_id).first()
  if not order:
    raise HTTPException(status_code=404, detail="Order not found")

  if order.status != OrderStatus.PROCESSING:
    raise HTTPException(
      status_code=400,
      detail=f"Order must be in PROCESSING status. Current status: {order.status}"
    )

  # Update inventory and create stock movements
  for order_item in order.order_items:
    if not order_item.inventory_item_id:
      continue

    inventory_item = db.query(InventoryItem).filter(
      InventoryItem.id == order_item.inventory_item_id
    ).first()

    if inventory_item:
      # Update inventory quantities
      inventory_item.quantity -= order_item.picked_quantity
      inventory_item.reserved_quantity -= order_item.picked_quantity
      order_item.dispensed_quantity = order_item.picked_quantity
      order_item.status = "dispensed"

      # Create stock movement
      movement = StockMovement(
        inventory_item_id=inventory_item.id,
        movement_type=StockMovementType.SALE,
        quantity=order_item.picked_quantity,
        previous_quantity=inventory_item.quantity + order_item.picked_quantity,
        new_quantity=inventory_item.quantity,
        reference_id=order_id,
        reference_type="order",
        reason="Order dispensed",
        user_id=current_user.id
      )
      db.add(movement)

  # Update order status
  order.status = OrderStatus.COMPLETED
  order.completed_date = datetime.now()

  # Update customer statistics
  if order.customer_id:
    customer = db.query(Customer).filter(Customer.id == order.customer_id).first()
    if customer:
      customer.update_statistics(order.total_amount)

  db.commit()

  # Send completion notification
  if order.customer_id:
    customer = db.query(Customer).filter(Customer.id == order.customer_id).first()
    if customer and customer.email:
      background_tasks.add_task(
        NotificationService.send_email,
        customer.email,
        f"✅ Order Ready: #{order.order_number}",
        f"Your order #{order.order_number} is ready for pickup. Total amount: ${order.total_amount}"
      )

  return {"message": "Order dispensed successfully", "order_id": order_id}


@router.get("/stats/overview", response_model=OrderStats)
async def get_order_stats(
    period: str = Query("today", description="today, week, month, year"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
  """Get order statistics"""
  from sqlalchemy import func, case
  from datetime import datetime, timedelta

  now = datetime.now()

  # Calculate date ranges
  if period == "today":
    start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
  elif period == "week":
    start_date = now - timedelta(days=now.weekday())
    start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
  elif period == "month":
    start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
  elif period == "year":
    start_date = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
  else:
    start_date = now - timedelta(days=30)

  # Total orders
  total_orders = db.query(func.count(Order.id)).scalar()

  # Total revenue
  total_revenue = db.query(func.sum(Order.total_amount)).filter(
    Order.status == OrderStatus.COMPLETED
  ).scalar() or 0

  # Average order value
  avg_order_value = db.query(func.avg(Order.total_amount)).filter(
    Order.status == OrderStatus.COMPLETED
  ).scalar() or 0

  # Orders by status
  orders_by_status = {}
  status_counts = db.query(
    Order.status,
    func.count(Order.id).label("count")
  ).group_by(Order.status).all()

  for status, count in status_counts:
    orders_by_status[status] = count

  # Orders by type
  orders_by_type = {}
  type_counts = db.query(
    Order.order_type,
    func.count(Order.id).label("count")
  ).group_by(Order.order_type).all()

  for order_type, count in type_counts:
    orders_by_type[order_type] = count

  # Today's orders
  today_orders = db.query(func.count(Order.id)).filter(
    func.date(Order.order_date) == now.date()
  ).scalar()

  # Today's revenue
  today_revenue = db.query(func.sum(Order.total_amount)).filter(
    func.date(Order.order_date) == now.date(),
    Order.status == OrderStatus.COMPLETED
  ).scalar() or 0

  # Pending orders
  pending_orders = db.query(func.count(Order.id)).filter(
    Order.status.in_([OrderStatus.PENDING, OrderStatus.CONFIRMED, OrderStatus.PROCESSING])
  ).scalar()

  # Top products
  top_products = db.query(
    Product.name,
    func.sum(OrderItem.quantity).label("total_sold")
  ).join(OrderItem).join(Order).filter(
    Order.status == OrderStatus.COMPLETED,
    Order.order_date >= start_date
  ).group_by(Product.id).order_by(func.sum(OrderItem.quantity).desc()).limit(5).all()

  top_products_list = [
    {"name": product, "sold": sold} for product, sold in top_products
  ]

  return OrderStats(
    total_orders=total_orders,
    total_revenue=total_revenue,
    average_order_value=avg_order_value,
    orders_by_status=orders_by_status,
    orders_by_type=orders_by_type,
    today_orders=today_orders,
    today_revenue=today_revenue,
    pending_orders=pending_orders,
    top_products=top_products_list
  )


@router.get("/dashboard/summary")
async def get_dashboard_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
  """Get order dashboard summary"""
  from datetime import datetime, timedelta

  now = datetime.now()
  today = now.date()
  yesterday = today - timedelta(days=1)
  week_start = today - timedelta(days=today.weekday())
  month_start = today.replace(day=1)

  # Today's stats
  today_stats = db.query(
    func.count(Order.id).label("count"),
    func.sum(Order.total_amount).label("revenue"),
    func.avg(Order.total_amount).label("avg_order_value")
  ).filter(
    func.date(Order.order_date) == today,
    Order.status == OrderStatus.COMPLETED
  ).first()

  # Yesterday's stats
  yesterday_stats = db.query(
    func.count(Order.id).label("count"),
    func.sum(Order.total_amount).label("revenue")
  ).filter(
    func.date(Order.order_date) == yesterday,
    Order.status == OrderStatus.COMPLETED
  ).first()

  # This week's stats
  week_stats = db.query(
    func.count(Order.id).label("count"),
    func.sum(Order.total_amount).label("revenue")
  ).filter(
    func.date(Order.order_date) >= week_start,
    Order.status == OrderStatus.COMPLETED
  ).first()

  # This month's stats
  month_stats = db.query(
    func.count(Order.id).label("count"),
    func.sum(Order.total_amount).label("revenue")
  ).filter(
    func.date(Order.order_date) >= month_start,
    Order.status == OrderStatus.COMPLETED
  ).first()

  # Recent orders
  recent_orders = db.query(Order).filter(
    Order.status.in_([OrderStatus.PENDING, OrderStatus.CONFIRMED, OrderStatus.PROCESSING])
  ).order_by(Order.order_date.desc()).limit(10).all()

  # Top customers this month
  top_customers = db.query(
    Order.customer_id,
    Customer.first_name,
    Customer.last_name,
    func.count(Order.id).label("order_count"),
    func.sum(Order.total_amount).label("total_spent")
  ).join(Customer).filter(
    func.date(Order.order_date) >= month_start,
    Order.status == OrderStatus.COMPLETED
  ).group_by(Order.customer_id, Customer.first_name, Customer.last_name).order_by(
    func.sum(Order.total_amount).desc()
  ).limit(5).all()

  return {
    "today": {
      "orders": today_stats.count or 0,
      "revenue": today_stats.revenue or 0,
      "avg_order_value": today_stats.avg_order_value or 0
    },
    "yesterday": {
      "orders": yesterday_stats.count or 0,
      "revenue": yesterday_stats.revenue or 0
    },
    "week": {
      "orders": week_stats.count or 0,
      "revenue": week_stats.revenue or 0
    },
    "month": {
      "orders": month_stats.count or 0,
      "revenue": month_stats.revenue or 0
    },
    "recent_orders": [
      {
        "id": order.id,
        "order_number": order.order_number,
        "customer_name": order.customer_name,
        "total_amount": order.total_amount,
        "status": order.status
      } for order in recent_orders
    ],
    "top_customers": [
      {
        "customer_id": cust.customer_id,
        "name": f"{cust.first_name} {cust.last_name}",
        "order_count": cust.order_count,
        "total_spent": cust.total_spent
      } for cust in top_customers
    ]
  }