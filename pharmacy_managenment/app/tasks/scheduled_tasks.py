import asyncio
from datetime import datetime, timedelta
import logging
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.product import ProductBatch
from app.models.order import Order, OrderStatus
from app.models.inventory import InventoryItem
from app.models.customer import Customer
from app.services.notification_service import NotificationService
from app.services.report_service import ReportService
from app.core.config import settings

logger = logging.getLogger(__name__)


class ScheduledTasks:
  def __init__(self):
    self.tasks = []
    self.running = False

  async def check_expired_products(self):
    """Check for expired products and send notifications"""
    logger.info("Checking for expired products...")

    try:
      db: Session = next(get_db())

      # Find expired batches
      expired_batches = db.query(ProductBatch).filter(
        ProductBatch.expiry_date < datetime.now(),
        ProductBatch.status == "active",
        ProductBatch.quantity_available > 0
      ).all()

      for batch in expired_batches:
        # Update batch status
        batch.status = "expired"

        # Send notifications
        await NotificationService.send_expiry_notification(
          batch, "expired"
        )

        # Create stock movement for expired items
        from app.models.inventory import StockMovement, StockMovementType
        movement = StockMovement(
          inventory_item_id=None,  # Will need to find actual inventory items
          movement_type=StockMovementType.EXPIRED,
          quantity=batch.quantity_available,
          reference_id=batch.id,
          reference_type="batch_expiry",
          reason="Product expired",
          user_id=None  # System action
        )
        db.add(movement)

      db.commit()

      # Check for products expiring soon (7 days)
      warning_date = datetime.now() + timedelta(days=7)
      expiring_soon = db.query(ProductBatch).filter(
        ProductBatch.expiry_date <= warning_date,
        ProductBatch.expiry_date > datetime.now(),
        ProductBatch.status == "active"
      ).all()

      for batch in expiring_soon:
        days_to_expiry = (batch.expiry_date - datetime.now()).days
        if days_to_expiry <= 7:
          await NotificationService.send_expiry_notification(
            batch, "warning"
          )

      logger.info(f"Expired products check completed. Found {len(expired_batches)} expired batches.")

    except Exception as e:
      logger.error(f"Error checking expired products: {e}")

  async def check_low_stock(self):
    """Check for low stock items"""
    logger.info("Checking for low stock items...")

    try:
      db: Session = next(get_db())

      from app.models.product import Product
      from sqlalchemy import func

      low_stock_items = db.query(
        Product.id,
        Product.name,
        Product.sku,
        Product.min_stock_level,
        func.coalesce(func.sum(InventoryItem.quantity), 0).label("current_stock")
      ).outerjoin(InventoryItem).group_by(Product.id).having(
        func.coalesce(func.sum(InventoryItem.quantity), 0) <= Product.min_stock_level
      ).all()

      for item in low_stock_items:
        product = db.query(Product).filter(Product.id == item.id).first()
        if product:
          await NotificationService.send_low_stock_alert(
            product, item.min_stock_level
          )

      logger.info(f"Low stock check completed. Found {len(low_stock_items)} low stock items.")

    except Exception as e:
      logger.error(f"Error checking low stock: {e}")

  async def process_pending_orders(self):
    """Process pending orders (auto-confirm after certain time)"""
    logger.info("Processing pending orders...")

    try:
      db: Session = next(get_db())

      # Find orders pending for more than 1 hour
      cutoff_time = datetime.now() - timedelta(hours=1)
      pending_orders = db.query(Order).filter(
        Order.status == OrderStatus.PENDING,
        Order.order_date <= cutoff_time
      ).all()

      for order in pending_orders:
        # Auto-confirm order
        order.status = OrderStatus.CONFIRMED

        logger.info(f"Auto-confirmed order #{order.order_number}")

      db.commit()
      logger.info(f"Processed {len(pending_orders)} pending orders.")

    except Exception as e:
      logger.error(f"Error processing pending orders: {e}")

  async def generate_daily_reports(self):
    """Generate daily reports"""
    logger.info("Generating daily reports...")

    try:
      db: Session = next(get_db())
      report_service = ReportService()

      # Generate sales report
      sales_report = await report_service.generate_sales_report(
        start_date=datetime.now() - timedelta(days=1),
        end_date=datetime.now(),
        group_by="hour"
      )

      # Generate inventory report
      inventory_report = await report_service.generate_inventory_report(
        report_type="stock_levels"
      )

      # Generate financial summary
      financial_summary = await report_service.generate_financial_summary(
        start_date=datetime.now() - timedelta(days=1),
        end_date=datetime.now()
      )

      # Send to admins
      admin_emails = ["admin@pharmacy.com", "manager@pharmacy.com"]

      report_data = {
        "sales_report": sales_report.get("summary", {}),
        "inventory_report": inventory_report.get("summary", {}),
        "financial_summary": financial_summary
      }

      for email in admin_emails:
        await NotificationService.send_daily_report(
          [email], report_data
        )

      logger.info("Daily reports generated and sent.")

    except Exception as e:
      logger.error(f"Error generating daily reports: {e}")

  async def update_customer_statistics(self):
    """Update customer statistics and send follow-up reminders"""
    logger.info("Updating customer statistics...")

    try:
      db: Session = next(get_db())

      # Find customers who haven't visited in 30 days
      cutoff_date = datetime.now() - timedelta(days=30)
      inactive_customers = db.query(Customer).filter(
        Customer.is_active == True,
        Customer.last_visit_date <= cutoff_date,
        Customer.total_orders > 0
      ).all()

      for customer in inactive_customers:
        # Send re-engagement email
        await NotificationService.send_email(
          customer.email,
          "We miss you! 🏥",
          f"Dear {customer.first_name},\n\n"
          f"It's been a while since your last visit. "
          f"We have new products and special offers waiting for you!\n\n"
          f"Visit us soon!\n\nBest regards,\nYour Pharmacy Team"
        )

      # Update next follow-up dates
      customers_to_followup = db.query(Customer).filter(
        Customer.next_followup_date <= datetime.now(),
        Customer.is_active == True
      ).all()

      for customer in customers_to_followup:
        # Schedule next follow-up in 90 days
        customer.next_followup_date = datetime.now() + timedelta(days=90)

        # Send follow-up email
        await NotificationService.send_email(
          customer.email,
          "How are you doing? ❤️",
          f"Dear {customer.first_name},\n\n"
          f"We hope you're doing well! "
          f"This is a friendly reminder to schedule your health check-up.\n\n"
          f"Take care!\n\nBest regards,\nYour Pharmacy Team"
        )

      db.commit()
      logger.info(f"Updated statistics for {len(inactive_customers)} customers.")

    except Exception as e:
      logger.error(f"Error updating customer statistics: {e}")

  async def cleanup_old_data(self):
    """Clean up old data (archive, soft delete)"""
    logger.info("Cleaning up old data...")

    try:
      db: Session = next(get_db())

      # Archive orders older than 1 year
      cutoff_date = datetime.now() - timedelta(days=365)
      old_orders = db.query(Order).filter(
        Order.completed_date <= cutoff_date
      ).all()

      # In production, you would move these to an archive table
      # For now, just log them
      logger.info(f"Found {len(old_orders)} orders older than 1 year to archive.")

      # Clean up temporary files
      import os
      import shutil
      temp_dir = "temp"
      if os.path.exists(temp_dir):
        for filename in os.listdir(temp_dir):
          file_path = os.path.join(temp_dir, filename)
          try:
            if os.path.isfile(file_path):
              os.unlink(file_path)
            elif os.path.isdir(file_path):
              shutil.rmtree(file_path)
          except Exception as e:
            logger.error(f"Error deleting {file_path}: {e}")

      logger.info("Data cleanup completed.")

    except Exception as e:
      logger.error(f"Error cleaning up old data: {e}")

  async def run_all_tasks(self):
    """Run all scheduled tasks"""
    logger.info("Starting scheduled tasks...")

    tasks = [
      self.check_expired_products(),
      self.check_low_stock(),
      self.process_pending_orders(),
      self.update_customer_statistics(),
      self.cleanup_old_data()
    ]

    # Run tasks concurrently
    await asyncio.gather(*tasks, return_exceptions=True)

    # Generate daily reports (once per day)
    current_hour = datetime.now().hour
    if current_hour == 8:  # 8 AM
      await self.generate_daily_reports()

    logger.info("Scheduled tasks completed.")


def start_scheduled_tasks():
  """Start scheduled tasks in background"""
  scheduler = ScheduledTasks()

  async def run_periodically():
    while True:
      try:
        await scheduler.run_all_tasks()
      except Exception as e:
        logger.error(f"Error in scheduled tasks: {e}")

      # Wait for 1 hour before next run
      await asyncio.sleep(3600)

  # Start the scheduler
  import asyncio
  loop = asyncio.get_event_loop()
  scheduler_task = loop.create_task(run_periodically())

  logger.info("Scheduled tasks started.")
  return scheduler_task