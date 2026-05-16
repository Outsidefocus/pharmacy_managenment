import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from typing import List, Optional, Dict, Any
import logging
from jinja2 import Template
import os

from app.core.config import settings

logger = logging.getLogger(__name__)


class EmailService:
  def __init__(self):
    self.smtp_host = settings.SMTP_HOST
    self.smtp_port = settings.SMTP_PORT
    self.smtp_user = settings.SMTP_USER
    self.smtp_password = settings.SMTP_PASSWORD

    # Load email templates
    self.templates = self._load_templates()

  def _load_templates(self) -> Dict[str, Template]:
    """Load email templates from files"""
    templates = {}
    templates_dir = "templates/emails"

    if os.path.exists(templates_dir):
      for filename in os.listdir(templates_dir):
        if filename.endswith('.html'):
          template_name = filename.replace('.html', '')
          with open(os.path.join(templates_dir, filename), 'r') as f:
            templates[template_name] = Template(f.read())

    # Default templates
    default_templates = {
      'order_confirmation': """
            <html>
            <body>
                <h2>Order Confirmation</h2>
                <p>Dear {{customer_name}},</p>
                <p>Thank you for your order!</p>
                <p><strong>Order #:</strong> {{order_number}}</p>
                <p><strong>Date:</strong> {{order_date}}</p>
                <p><strong>Total:</strong> ${{total_amount}}</p>
                <p>We will notify you when your order is ready for pickup.</p>
            </body>
            </html>
            """,
      'payment_received': """
            <html>
            <body>
                <h2>Payment Received</h2>
                <p>Dear {{customer_name}},</p>
                <p>Thank you for your payment!</p>
                <p><strong>Amount:</strong> ${{amount}}</p>
                <p><strong>Date:</strong> {{payment_date}}</p>
                <p><strong>Reference:</strong> {{reference}}</p>
            </body>
            </html>
            """,
      'password_reset': """
            <html>
            <body>
                <h2>Password Reset</h2>
                <p>Click the link below to reset your password:</p>
                <p><a href="{{reset_link}}">Reset Password</a></p>
                <p>This link will expire in 24 hours.</p>
            </body>
            </html>
            """
    }

    for name, template_str in default_templates.items():
      templates[name] = Template(template_str)

    return templates

  async def send_email(
      self,
      to_email: str,
      subject: str,
      body: str,
      html_body: Optional[str] = None,
      attachments: Optional[List[Dict[str, Any]]] = None,
      template_name: Optional[str] = None,
      template_data: Optional[Dict[str, Any]] = None
  ) -> bool:
    """Send email with optional template and attachments"""
    try:
      # Use template if provided
      if template_name and template_name in self.templates and template_data:
        template = self.templates[template_name]
        html_body = template.render(**template_data)

      msg = MIMEMultipart()
      msg["From"] = self.smtp_user
      msg["To"] = to_email
      msg["Subject"] = subject

      # Add text body
      if body:
        msg.attach(MIMEText(body, "plain"))

      # Add HTML body
      if html_body:
        msg.attach(MIMEText(html_body, "html"))

      # Add attachments
      if attachments:
        for attachment in attachments:
          if 'filename' in attachment and 'content' in attachment:
            part = MIMEApplication(
              attachment['content'],
              Name=attachment['filename']
            )
            part['Content-Disposition'] = f'attachment; filename="{attachment["filename"]}"'
            msg.attach(part)

      # Send email
      with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
        server.starttls()
        server.login(self.smtp_user, self.smtp_password)
        server.send_message(msg)

      logger.info(f"Email sent to {to_email}")
      return True

    except Exception as e:
      logger.error(f"Failed to send email to {to_email}: {e}")
      return False

  async def send_bulk_emails(
      self,
      emails: List[Dict[str, Any]],
      batch_size: int = 50
  ) -> Dict[str, int]:
    """Send bulk emails in batches"""
    results = {"success": 0, "failed": 0}

    for i in range(0, len(emails), batch_size):
      batch = emails[i:i + batch_size]

      for email_data in batch:
        success = await self.send_email(
          to_email=email_data.get('to'),
          subject=email_data.get('subject'),
          body=email_data.get('body'),
          html_body=email_data.get('html_body'),
          attachments=email_data.get('attachments')
        )

        if success:
          results["success"] += 1
        else:
          results["failed"] += 1

      # Delay between batches to avoid rate limiting
      import asyncio
      await asyncio.sleep(1)

    logger.info(f"Bulk emails sent: {results['success']} success, {results['failed']} failed")
    return results

  async def send_template_email(
      self,
      to_email: str,
      template_name: str,
      template_data: Dict[str, Any],
      subject: Optional[str] = None,
      attachments: Optional[List[Dict[str, Any]]] = None
  ) -> bool:
    """Send email using a template"""
    if template_name not in self.templates:
      logger.error(f"Template not found: {template_name}")
      return False

    # Get subject from template data or use default
    if not subject:
      subject = template_data.get('subject', 'Notification')

    # Render template
    template = self.templates[template_name]
    html_body = template.render(**template_data)

    # Send email
    return await self.send_email(
      to_email=to_email,
      subject=subject,
      body="",  # Empty plain text body
      html_body=html_body,
      attachments=attachments
    )

  async def send_welcome_email(self, user_data: Dict[str, Any]) -> bool:
    """Send welcome email to new user"""
    template_data = {
      "user_name": user_data.get('name'),
      "login_url": user_data.get('login_url', '#'),
      "support_email": "support@pharmacy.com"
    }

    return await self.send_template_email(
      to_email=user_data['email'],
      template_name='welcome',
      template_data=template_data,
      subject=f"Welcome to {settings.PROJECT_NAME}!"
    )

  async def send_password_reset_email(self, email: str, reset_token: str) -> bool:
    """Send password reset email"""
    reset_link = f"{settings.FRONTEND_URL}/reset-password?token={reset_token}"

    template_data = {
      "reset_link": reset_link
    }

    return await self.send_template_email(
      to_email=email,
      template_name='password_reset',
      template_data=template_data,
      subject="Password Reset Request"
    )

  async def send_order_status_email(self, order_data: Dict[str, Any]) -> bool:
    """Send order status update email"""
    template_data = {
      "customer_name": order_data.get('customer_name'),
      "order_number": order_data.get('order_number'),
      "order_status": order_data.get('status'),
      "order_date": order_data.get('order_date'),
      "total_amount": order_data.get('total_amount'),
      "update_message": order_data.get('message', 'Your order status has been updated.')
    }

    return await self.send_template_email(
      to_email=order_data['customer_email'],
      template_name='order_status',
      template_data=template_data,
      subject=f"Order #{order_data['order_number']} Status Update"
    )

  async def send_inventory_alert_email(self, alert_data: Dict[str, Any]) -> bool:
    """Send inventory alert email"""
    recipients = alert_data.get('recipients', [])
    if not recipients:
      return False

    template_data = {
      "alert_type": alert_data.get('type'),
      "product_name": alert_data.get('product_name'),
      "current_stock": alert_data.get('current_stock'),
      "threshold": alert_data.get('threshold'),
      "message": alert_data.get('message'),
      "suggested_action": alert_data.get('suggested_action')
    }

    success_count = 0
    for recipient in recipients:
      success = await self.send_template_email(
        to_email=recipient,
        template_name='inventory_alert',
        template_data=template_data,
        subject=f"Inventory Alert: {alert_data.get('product_name')}"
      )
      if success:
        success_count += 1

    return success_count > 0


# Global email service instance
email_service = EmailService()