import asyncio
import logging
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.email_service import EmailService
from app.services.sms_service import SMSService
from app.services.ai_service import AIService
from app.services.report_service import ReportService

logger = logging.getLogger(__name__)


class BackgroundTaskManager:
  def __init__(self):
    self.tasks = []
    self.ai_service = AIService()
    self.email_service = EmailService()
    self.sms_service = SMSService()
    self.report_service = ReportService()

  async def process_bulk_emails(self, emails: List[Dict[str, Any]]):
    """Process bulk email sending"""
    logger.info(f"Processing {len(emails)} bulk emails...")

    success_count = 0
    failure_count = 0

    for email_data in emails:
      try:
        success = await self.email_service.send_email(
          to_email=email_data['to'],
          subject=email_data['subject'],
          body=email_data['body'],
          html_body=email_data.get('html_body')
        )

        if success:
          success_count += 1
        else:
          failure_count += 1

        # Delay to avoid rate limiting
        await asyncio.sleep(0.1)

      except Exception as e:
        logger.error(f"Error sending email to {email_data.get('to')}: {e}")
        failure_count += 1

    logger.info(f"Bulk emails processed: {success_count} success, {failure_count} failures")
    return {"success": success_count, "failures": failure_count}

  async def process_bulk_sms(self, messages: List[Dict[str, Any]]):
    """Process bulk SMS sending"""
    logger.info(f"Processing {len(messages)} bulk SMS...")

    success_count = 0
    failure_count = 0

    for message_data in messages:
      try:
        success = await self.sms_service.send_sms(
          to_phone=message_data['to'],
          message=message_data['message']
        )

        if success:
          success_count += 1
        else:
          failure_count += 1

        # Delay to avoid rate limiting
        await asyncio.sleep(0.5)

      except Exception as e:
        logger.error(f"Error sending SMS to {message_data.get('to')}: {e}")
        failure_count += 1

    logger.info(f"Bulk SMS processed: {success_count} success, {failure_count} failures")
    return {"success": success_count, "failures": failure_count}

  async def generate_ai_insights(self, data_type: str, data: Dict[str, Any]):
    """Generate AI insights for data"""
    logger.info(f"Generating AI insights for {data_type}...")

    try:
      if data_type == "sales":
        insights = await self.ai_service.analyze_market_trends(
          data.get('sales_data', [])
        )
      elif data_type == "inventory":
        insights = await self.ai_service.predict_demand(
          data.get('product_id'),
          data.get('historical_data', [])
        )
      elif data_type == "customer":
        insights = await self.ai_service.generate_marketing_insights(
          data.get('customer_data', [])
        )
      elif data_type == "pricing":
        insights = await self.ai_service.optimize_pricing(
          data.get('product_info', {}),
          data.get('market_data', {})
        )
      else:
        insights = {"error": f"Unknown data type: {data_type}"}

      logger.info(f"AI insights generated for {data_type}")
      return insights

    except Exception as e:
      logger.error(f"Error generating AI insights: {e}")
      return {"error": str(e)}

  async def export_data(self, export_type: str, filters: Dict[str, Any], format: str = "excel"):
    """Export data in various formats"""
    logger.info(f"Exporting {export_type} data in {format} format...")

    try:
      db: Session = next(get_db())

      if export_type == "products":
        from app.models.product import Product
        query = db.query(Product)

        if filters.get('category'):
          query = query.filter(Product.category == filters['category'])

        if filters.get('requires_prescription') is not None:
          query = query.filter(
            Product.requires_prescription == filters['requires_prescription']
          )

        data = query.all()

      elif export_type == "orders":
        from app.models.order import Order
        query = db.query(Order)

        if filters.get('start_date'):
          query = query.filter(Order.order_date >= filters['start_date'])

        if filters.get('end_date'):
          query = query.filter(Order.order_date <= filters['end_date'])

        if filters.get('status'):
          query = query.filter(Order.status == filters['status'])

        data = query.all()

      elif export_type == "customers":
        from app.models.customer import Customer
        query = db.query(Customer)

        if filters.get('customer_type'):
          query = query.filter(Customer.customer_type == filters['customer_type'])

        if filters.get('is_active') is not None:
          query = query.filter(Customer.is_active == filters['is_active'])

        data = query.all()

      elif export_type == "inventory":
        from app.models.inventory import InventoryItem
        from app.models.product import Product

        query = db.query(
          InventoryItem, Product
        ).join(Product).filter(
          InventoryItem.quantity > 0
        )

        if filters.get('warehouse_id'):
          query = query.filter(InventoryItem.warehouse_id == filters['warehouse_id'])

        data = query.all()

      else:
        return {"error": f"Unknown export type: {export_type}"}

      # Convert to export format
      if format == "excel":
        result = await self._export_to_excel(data, export_type)
      elif format == "csv":
        result = await self._export_to_csv(data, export_type)
      elif format == "pdf":
        result = await self._export_to_pdf(data, export_type)
      else:
        result = await self._export_to_json(data, export_type)

      logger.info(f"Exported {len(data)} {export_type} records")
      return result

    except Exception as e:
      logger.error(f"Error exporting data: {e}")
      return {"error": str(e)}

  async def _export_to_excel(self, data: List, data_type: str) -> Dict[str, Any]:
    """Export data to Excel format"""
    try:
      import pandas as pd
      from io import BytesIO
      import base64

      # Convert data to DataFrame
      if data_type == "products":
        df_data = []
        for item in data:
          df_data.append({
            "ID": item.id,
            "Name": item.name,
            "SKU": item.sku,
            "Category": item.category,
            "Cost Price": item.cost_price,
            "Selling Price": item.selling_price,
            "Stock Level": item.min_stock_level,
            "Requires Prescription": item.requires_prescription
          })
      elif data_type == "orders":
        df_data = []
        for item in data:
          df_data.append({
            "Order Number": item.order_number,
            "Customer": item.customer_name,
            "Date": item.order_date,
            "Status": item.status,
            "Total Amount": item.total_amount,
            "Payment Status": item.payment_status
          })
      else:
        # Generic export
        df_data = [item.__dict__ for item in data]

      df = pd.DataFrame(df_data)

      # Create Excel file in memory
      output = BytesIO()
      with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Data', index=False)

      excel_data = output.getvalue()

      # Encode to base64
      excel_base64 = base64.b64encode(excel_data).decode('utf-8')

      return {
        "format": "excel",
        "filename": f"{data_type}_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
        "data": excel_base64,
        "record_count": len(data)
      }

    except Exception as e:
      logger.error(f"Error exporting to Excel: {e}")
      return {"error": str(e)}

  async def _export_to_csv(self, data: List, data_type: str) -> Dict[str, Any]:
    """Export data to CSV format"""
    try:
      import pandas as pd
      from io import StringIO

      # Convert data to DataFrame (similar to Excel export)
      df_data = [item.__dict__ for item in data]
      df = pd.DataFrame(df_data)

      # Create CSV in memory
      output = StringIO()
      df.to_csv(output, index=False)
      csv_data = output.getvalue()

      return {
        "format": "csv",
        "filename": f"{data_type}_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        "data": csv_data,
        "record_count": len(data)
      }

    except Exception as e:
      logger.error(f"Error exporting to CSV: {e}")
      return {"error": str(e)}

  async def backup_database(self):
    """Create database backup"""
    logger.info("Creating database backup...")

    try:
      import subprocess
      import os
      from datetime import datetime

      # Create backup directory if it doesn't exist
      backup_dir = "backups"
      os.makedirs(backup_dir, exist_ok=True)

      # Generate backup filename
      timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
      backup_file = os.path.join(backup_dir, f"pharmacy_backup_{timestamp}.sql")

      # Get database configuration
      from app.core.config import settings
      db_url = settings.DATABASE_URL

      # Extract connection info
      # Note: This is a simplified example. In production, use proper database backup tools
      import re
      match = re.match(r"postgresql\+asyncpg://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)", db_url)

      if match:
        username, password, host, port, database = match.groups()

        # Set environment variables for pg_dump
        env = os.environ.copy()
        env['PGPASSWORD'] = password

        # Run pg_dump
        cmd = [
          'pg_dump',
          '-h', host,
          '-p', port,
          '-U', username,
          '-d', database,
          '-f', backup_file
        ]

        result = subprocess.run(cmd, env=env, capture_output=True, text=True)

        if result.returncode == 0:
          logger.info(f"Database backup created: {backup_file}")

          # Compress backup
          import gzip
          with open(backup_file, 'rb') as f_in:
            with gzip.open(f"{backup_file}.gz", 'wb') as f_out:
              f_out.writelines(f_in)

          # Remove uncompressed backup
          os.remove(backup_file)

          return {
            "success": True,
            "backup_file": f"{backup_file}.gz",
            "size": os.path.getsize(f"{backup_file}.gz")
          }
        else:
          logger.error(f"Database backup failed: {result.stderr}")
          return {"success": False, "error": result.stderr}
      else:
        logger.error("Could not parse database URL")
        return {"success": False, "error": "Invalid database URL"}

    except Exception as e:
      logger.error(f"Error creating database backup: {e}")
      return {"success": False, "error": str(e)}

  async def sync_with_external_systems(self):
    """Sync data with external systems (e.g., inventory suppliers, payment gateways)"""
    logger.info("Syncing with external systems...")

    try:
      # Sync inventory with suppliers
      await self._sync_inventory_with_suppliers()

      # Sync payments with payment gateway
      await self._sync_payments()

      # Sync prescriptions with healthcare providers
      await self._sync_prescriptions()

      logger.info("External systems sync completed.")
      return {"success": True}

    except Exception as e:
      logger.error(f"Error syncing with external systems: {e}")
      return {"success": False, "error": str(e)}

  async def _sync_inventory_with_suppliers(self):
    """Sync inventory levels with suppliers"""
    # This would integrate with supplier APIs
    # For now, just log
    logger.info("Syncing inventory with suppliers...")
    await asyncio.sleep(1)  # Simulate API call

  async def _sync_payments(self):
    """Sync payment status with payment gateway"""
    logger.info("Syncing payments with payment gateway...")
    await asyncio.sleep(1)  # Simulate API call

  async def _sync_prescriptions(self):
    """Sync prescriptions with healthcare providers"""
    logger.info("Syncing prescriptions with healthcare providers...")
    await asyncio.sleep(1)  # Simulate API call


# Global background task manager instance
background_task_manager = BackgroundTaskManager()