import os
from dotenv import load_dotenv

load_dotenv()

SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
MAIL_FROM = os.getenv("MAIL_FROM", "no-reply@example.com")
MAIL_REPLY_TO = os.getenv("MAIL_REPLY_TO")

def validate_email_config():
    if not SENDGRID_API_KEY:
        raise RuntimeError("Missing SENDGRID_API_KEY")
    if not MAIL_FROM:
        raise RuntimeError("Missing MAIL_FROM")