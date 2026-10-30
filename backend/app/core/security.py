"""
Security & PII Data Protection Utilities
Requirement: Mask borrower phone numbers and email addresses in dashboard and logs.
"""
import re

def mask_phone(phone: str | None) -> str:
    """
    Masks a phone number, preserving the first 2 and last 4 digits.
    Example: '9912497306' -> '99****7306'
    """
    if not phone:
        return "N/A"
    clean = re.sub(r"\D", "", str(phone))
    if len(clean) <= 4:
        return "****"
    if len(clean) <= 6:
        return clean[:1] + "*" * (len(clean) - 2) + clean[-1:]
    prefix = clean[:2]
    suffix = clean[-4:]
    masked_middle = "*" * (len(clean) - 6)
    return f"{prefix}{masked_middle}{suffix}"

def mask_email(email: str | None) -> str:
    """
    Masks an email address, concealing the middle of the local part.
    Example: 'user8943@example.com' -> 'u***3@example.com'
    """
    if not email or "@" not in email:
        return "N/A"
    parts = email.split("@", 1)
    user, domain = parts[0], parts[1]
    if len(user) <= 2:
        masked_user = user[:1] + "*"
    else:
        masked_user = user[0] + "*" * (len(user) - 2) + user[-1]
    return f"{masked_user}@{domain}"
