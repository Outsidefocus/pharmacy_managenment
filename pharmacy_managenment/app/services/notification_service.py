from typing import List, Dict, Any, Optional
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from twilio.rest import Client
import logging
from app.core.config import settings
from app.models.product import ProductBatch
from app.schemas.inventory import ExpiredProductsResponse

logger = logging.getLogger(__name__)


class NotificationService:

  @staticmethod
  async def send_email(
      to_email: str,
      subject: str,
      body: str,
      html_body: Optional[str] = None
  ) -> bool:
    """Send email notification"""
    try:
      msg = MIMEMultipart()
      msg["From"] = settings.SMTP_USER
      msg["To"] = to_email
      msg["Subject"] = subject

      if html_body:
        msg.attach(MIMEText(html_body, "html"))
      else:
        msg.attach(MIMEText(body, "plain"))

      with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
        server.starttls()
        server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        server.send_message(msg)

      logger.info(f"Email sent to {to_email}")
      return True

    except Exception as e:
      logger.error(f"Failed to send email: {e}")
      return False

  @staticmethod
  async def send_sms(
      to_phone: str,
      message: str
  ) -> bool:
    """Send SMS notification using Twilio"""
    try:
      if not all([settings.TWILIO_ACCOUNT_SID,
                  settings.TWILIO_AUTH_TOKEN,
                  settings.TWILIO_PHONE_NUMBER]):
        logger.warning("Twilio credentials not configured")
        return False

      client = Client(settings.TWILIO_ACCOUNT_SID,
                      settings.TWILIO_AUTH_TOKEN)

      client.messages.create(
        body=message,
        from_=settings.TWILIO_PHONE_NUMBER,
        to=to_phone
      )

      logger.info(f"SMS sent to {to_phone}")
      return True

    except Exception as e:
      logger.error(f"Failed to send SMS: {e}")
      return False

  @staticmethod
  async def send_expiry_notification(
      product: ExpiredProductsResponse,
      notification_type: str = "expired"
  ) -> None:
    """Send notifications for expired products"""
    subject = ""
    message = ""

    if notification_type == "expired":
      subject = f"⚠️ Product Expired: {product.product_name}"
      message = f"""
            Product: {product.product_name}
            Batch: {product.batch_number}
            Expiry Date: {product.expiry_date}
            Quantity: {product.quantity_available}

            This product has expired and should be removed from shelves.
            """
    elif notification_type == "warning":
      subject = f"⚠️ Product Expiring Soon: {product.product_name}"
      message = f"""
            Product: {product.product_name}
            Batch: {product.batch_number}
            Expiry Date: {product.expiry_date}
            Days to Expiry: {product.days_to_expiry}
            Quantity: {product.quantity_available}

            This product will expire soon. Consider promotions or returns.
            """

    # Send to admins/managers
    admin_emails = ["admin@pharmacy.com", "manager@pharmacy.com"]

    for email in admin_emails:
      await NotificationService.send_email(
        to_email=email,
        subject=subject,
        body=message
      )

    # Send SMS to inventory manager
    inventory_manager_phone = "+1234567890"
    sms_message = f"Pharmacy Alert: {subject}"
    await NotificationService.send_sms(inventory_manager_phone, sms_message)

  @staticmethod
  async def send_low_stock_alert(
      product,
      min_stock_level: int
  ) -> None:
    """Send low stock alert"""
    subject = f"📉 Low Stock Alert: {product.name}"
    message = f"""
        Product: {product.name}
        SKU: {product.sku}
        Current Stock: {product.quantity}
        Minimum Stock Level: {min_stock_level}
        Category: {product.category}

        Please reorder this product immediately.
        """

    # Send email to purchasing department
    purchasing_emails = ["purchasing@pharmacy.com", "inventory@pharmacy.com"]

    for email in purchasing_emails:
      await NotificationService.send_email(
        to_email=email,
        subject=subject,
        body=message
      )

  @staticmethod
  async def send_order_confirmation(
      customer_email: str,
      customer_name: str,
      order_details: Dict
  ) -> None:
    """Send order confirmation to customer"""
    subject = f"✅ Order Confirmation: #{order_details['order_number']}"

    html_body = f"""
        <html>
        <body>
            <h2>Order Confirmation</h2>
            <p>Dear {customer_name},</p>
            <p>Thank you for your order!</p>

            <h3>Order Details:</h3>
            <p><strong>Order #:</strong> {order_details['order_number']}</p>
            <p><strong>Date:</strong> {order_details['order_date']}</p>
            <p><strong>Total Amount:</strong> ${order_details['total_amount']}</p>

            <h3>Items:</h3>
            <ul>
        """

    for item in order_details['items']:
      html_body += f"<li>{item['quantity']} x {item['name']} - ${item['price']}</li>"

    html_body += """
            </ul>

            <p>We will notify you when your order is ready for pickup.</p>
            <p>Thank you for choosing our pharmacy!</p>
        </body>
        </html>
        """

    await NotificationService.send_email(
      to_email=customer_email,
      subject=subject,
      html_body=html_body
    )

  @staticmethod
  async def send_payment_reminder(
      customer_email: str,
      customer_name: str,
      invoice_details: Dict
  ) -> None:
    """Send payment reminder"""
    subject = f"💰 Payment Reminder: Invoice #{invoice_details['invoice_number']}"

    message = f"""
        Dear {customer_name},

        This is a reminder that payment is due for Invoice #{invoice_details['invoice_number']}.

        Amount Due: ${invoice_details['amount_due']}
        Due Date: {invoice_details['due_date']}

        Please make payment at your earliest convenience.

        Thank you,
        Pharmacy Management
        """

    await NotificationService.send_email(
      to_email=customer_email,
      subject=subject,
      body=message
    )

  @staticmethod
  async def send_daily_report(
      recipients: List[str],
      report_data: Dict
  ) -> None:
    """Send daily sales/inventory report"""
    subject = f"📊 Daily Pharmacy Report - {datetime.now().strftime('%Y-%m-%d')}"

    html_body = f"""
        <html>
        <body>
            <h2>Daily Pharmacy Report</h2>
            <p><strong>Date:</strong> {datetime.now().strftime('%Y-%m-%d')}</p>

            <h3>Sales Summary:</h3>
            <p>Total Sales: ${report_data.get('total_sales', 0)}</p>
            <p>Transactions: {report_data.get('transaction_count', 0)}</p>
            <p>Average Transaction Value: ${report_data.get('avg_transaction', 0)}</p>

            <h3>Inventory Status:</h3>
            <p>Low Stock Items: {report_data.get('low_stock_items', 0)}</p>
            <p>Expired Products: {report_data.get('expired_products', 0)}</p>

            <h3>Top Selling Products:</h3>
            <ul>
        """

    for product in report_data.get('top_products', [])[:5]:
      html_body += f"<li>{product['name']}: {product['quantity']} sold</li>"

    html_body += """
            </ul>

            <p>This is an automated report generated by the Pharmacy Management System.</p>
        </body>
        </html>
        """

    for recipient in recipients:
      await NotificationService.send_email(
        to_email=recipient,
        subject=subject,
        html_body=html_body
      )