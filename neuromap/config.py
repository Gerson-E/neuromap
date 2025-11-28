import os
from dotenv import load_dotenv

load_dotenv()

SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
MAIL_FROM = os.getenv("MAIL_FROM", "no-reply@example.com")
MAIL_REPLY_TO = os.getenv("MAIL_REPLY_TO")

def is_email_configured():
    """Check if email configuration is available."""
    return bool(SENDGRID_API_KEY and MAIL_FROM)

def validate_email_config():
    """Validate email configuration, raising error if not configured."""
    if not SENDGRID_API_KEY:
        raise RuntimeError("Missing SENDGRID_API_KEY")
    if not MAIL_FROM:
        raise RuntimeError("Missing MAIL_FROM")