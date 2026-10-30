"""
Data Normalization & Cleaning Utilities
"""
from datetime import datetime, timezone, timedelta
import re

TIMEZONE_OFFSETS = {
    "UTC": timedelta(hours=0),
    "Asia/Kolkata": timedelta(hours=5, minutes=30),
    "Asia/Dubai": timedelta(hours=4),
}

DISPOSITION_MAPPING = {
    "PTP": "PROMISE_TO_PAY",
    "PROMISE_TO_PAY": "PROMISE_TO_PAY",
    "PTP_BROKEN": "PTP_BROKEN",
    "PAID": "PAID",
    "CALLBACK": "CALLBACK",
    "REFUSED": "REFUSED",
    "DISPUTE": "DISPUTE",
    "WRONG_NUMBER": "WRONG_NUMBER",
    "NO_CONTACT": "NO_CONTACT",
}

def parse_and_normalize_timestamp(dt_str: str | None, tz_name: str | None = "UTC") -> datetime | None:
    """
    Parses a string timestamp ('YYYY-MM-DD HH:MM:SS' or 'YYYY-MM-DD')
    and normalizes to a timezone-aware UTC datetime.
    """
    if not dt_str or dt_str.strip().lower() in ("null", "none", "", "nan"):
        return None
    
    dt_str = dt_str.strip()
    dt = None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(dt_str, fmt)
            break
        except ValueError:
            pass
            
    if dt is None:
        return None

    # Apply timezone offset to convert local time to UTC
    tz = tz_name if tz_name in TIMEZONE_OFFSETS else "UTC"
    offset = TIMEZONE_OFFSETS[tz]
    
    # Local time minus offset = UTC time
    utc_dt = dt - offset
    return utc_dt.replace(tzinfo=timezone.utc)

def normalize_disposition_code(raw_code: str | None) -> tuple[str, str | None]:
    """
    Normalizes disposition code to canonical form.
    Returns (canonical_code, raw_code)
    """
    if not raw_code:
        return "UNKNOWN", raw_code
    code_upper = raw_code.strip().upper()
    canonical = DISPOSITION_MAPPING.get(code_upper, code_upper)
    return canonical, raw_code

def clean_phone(phone: str | None) -> str | None:
    if not phone or phone.strip().lower() in ("null", "none", "", "nan"):
        return None
    digits = re.sub(r"\D", "", phone.strip())
    return digits if digits else None

def clean_email(email: str | None) -> str | None:
    if not email or email.strip().lower() in ("null", "none", "", "nan"):
        return None
    cleaned = email.strip().lower()
    return cleaned if "@" in cleaned else None
