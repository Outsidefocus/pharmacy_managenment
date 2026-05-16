import re
from typing import Optional

def validate_email(email: str) -> bool:
    """Validate email format"""
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return re.match(pattern, email) is not None

def validate_phone(phone: str) -> bool:
    """Validate phone number (simple check)"""
    # Remove common separators
    cleaned = re.sub(r'[\s\-\(\)\+]', '', phone)
    # Allow digits only, length between 10-15
    return cleaned.isdigit() and 10 <= len(cleaned) <= 15

def validate_password_strength(password: str) -> tuple[bool, str]:
    """Check password strength"""
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    if not re.search(r"[A-Z]", password):
        return False, "Password must contain at least one uppercase letter"
    if not re.search(r"[a-z]", password):
        return False, "Password must contain at least one lowercase letter"
    if not re.search(r"[0-9]", password):
        return False, "Password must contain at least one digit"
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        return False, "Password must contain at least one special character"
    return True, "Password is strong"

def validate_barcode(barcode: str) -> bool:
    """Validate barcode format (EAN-13, UPC, etc.)"""
    # Simple check: digits only, length 8-14
    return barcode.isdigit() and 8 <= len(barcode) <= 14

def validate_date_range(start_date: datetime, end_date: datetime) -> bool:
    """Check if start_date <= end_date"""
    return start_date <= end_date

def validate_expiry_date(expiry_date: datetime) -> bool:
    """Check if expiry date is in the future"""
    return expiry_date > datetime.now()

def validate_positive_number(value: float, allow_zero: bool = False) -> bool:
    """Check if number is positive"""
    if allow_zero:
        return value >= 0
    return value > 0