import os
from typing import Mapping
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To, Content
from jinja2 import Environment, FileSystemLoader, select_autoescape
from ..config import SENDGRID_API_KEY, MAIL_FROM, MAIL_REPLY_TO, validate_email_config


TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "templates")
env = Environment(
    loader=FileSystemLoader(TEMPLATE_DIR),
    autoescape=select_autoescape(["html", "xml"])
)

def _render(name: str, ctx: Mapping[str, str]) -> str:
    return env.get_template(name).render(**ctx)

class TransientEmailError(Exception):
    pass

@retry(
    retry=retry_if_exception_type(TransientEmailError),
    wait=wait_exponential(multiplier=1, min=1, max=30),
    stop=stop_after_attempt(5),
    reraise=True,
)

def send_email(to_email: str, subject: str, context: Mapping[str, str],
               txt_template: str = "done.txt", html_template: str = "done.html") -> None:
    validate_email_config()

    html = _render(html_template, context)
    txt  = _render(txt_template, context)

    msg = Mail(
        from_email=Email(MAIL_FROM),
        to_emails=[To(to_email)],
        subject=subject,
        plain_text_content=Content("text/plain", txt),
        html_content=Content("text/html", html),
    )
    if MAIL_REPLY_TO:
        msg.reply_to = Email(MAIL_REPLY_TO)

    try:
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        resp = sg.send(msg)
        if 500 <= resp.status_code < 600:
            raise TransientEmailError(f"SendGrid 5xx: {resp.status_code}")
    except TransientEmailError:
        raise
    except Exception:
        # Non-transient (4xx, bad address, etc.): let it bubble up
        raise