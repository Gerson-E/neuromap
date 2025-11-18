from typing import Mapping
from ..notifications.send import send_email

def send_email_task(to_email: str, subject: str, context: Mapping[str, str]) -> None:
    """
    v0 inline. Later, replace body with Celery: send_email_task_async.delay(...)

    I think this will be the queue portion in the future
    """
    send_email(to_email, subject, context)
