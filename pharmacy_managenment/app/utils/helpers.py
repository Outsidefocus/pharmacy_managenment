import random
import string
from datetime import datetime
from sqlalchemy.orm import Session


def generate_order_number(db: Session) -> str:
  """Generate a unique order number"""
  prefix = "ORD"
  date_str = datetime.now().strftime("%Y%m%d")
  random_part = ''.join(random.choices(string.digits, k=6))
  number = f"{prefix}{date_str}{random_part}"

  # Check uniqueness
  from app.models.order import Order
  while db.query(Order).filter(Order.order_number == number).first():
    random_part = ''.join(random.choices(string.digits, k=6))
    number = f"{prefix}{date_str}{random_part}"

  return number


def generate_payment_reference(db: Session) -> str:
  """Generate a unique payment reference"""
  prefix = "PAY"
  date_str = datetime.now().strftime("%Y%m%d%H%M%S")
  random_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
  reference = f"{prefix}{date_str}{random_part}"

  from app.models.payment import Payment
  while db.query(Payment).filter(Payment.payment_reference == reference).first():
    random_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    reference = f"{prefix}{date_str}{random_part}"

  return reference


def generate_invoice_number(db: Session) -> str:
  """Generate a unique invoice number"""
  prefix = "INV"
  year = datetime.now().strftime("%Y")
  seq = ''.join(random.choices(string.digits, k=6))
  number = f"{prefix}{year}{seq}"

  from app.models.payment import Invoice
  while db.query(Invoice).filter(Invoice.invoice_number == number).first():
    seq = ''.join(random.choices(string.digits, k=6))
    number = f"{prefix}{year}{seq}"

  return number


def generate_customer_code(db: Session) -> str:
  """Generate a unique customer code"""
  prefix = "CUST"
  seq = ''.join(random.choices(string.digits, k=6))
  code = f"{prefix}{seq}"

  from app.models.customer import Customer
  while db.query(Customer).filter(Customer.customer_code == code).first():
    seq = ''.join(random.choices(string.digits, k=6))
    code = f"{prefix}{seq}"

  return code


def generate_prescription_number(db: Session) -> str:
  """Generate a unique prescription number"""
  prefix = "RX"
  date_str = datetime.now().strftime("%Y%m%d")
  seq = ''.join(random.choices(string.digits, k=6))
  number = f"{prefix}{date_str}{seq}"

  from app.models.customer import Prescription
  while db.query(Prescription).filter(Prescription.prescription_number == number).first():
    seq = ''.join(random.choices(string.digits, k=6))
    number = f"{prefix}{date_str}{seq}"

  return number


def format_currency(amount: float, currency: str = "USD") -> str:
  """Format amount as currency string"""
  symbols = {"USD": "$", "EUR": "€", "GBP": "£"}
  symbol = symbols.get(currency, "$")
  return f"{symbol}{amount:.2f}"


def calculate_age(birth_date: datetime) -> int:
  """Calculate age from birth date"""
  today = datetime.now().date()
  if isinstance(birth_date, datetime):
    birth_date = birth_date.date()
  return today.year - birth_date.year - (
      (today.month, today.day) < (birth_date.month, birth_date.day)
  )