import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.core.config import settings

logger = logging.getLogger(__name__)

def send_email(to_email: str, subject: str, message: str):
    """
    Sends an email using SMTP (Gmail).
    Uses environment variables: SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS.
    """
    smtp_host = settings.SMTP_HOST
    smtp_port = settings.SMTP_PORT
    smtp_user = settings.SMTP_USER
    smtp_pass = settings.SMTP_PASS

    if not smtp_user or not smtp_pass:
        logger.warning(f"[Email] Cannot send email to {to_email}: SMTP credentials not configured.")
        return

    msg = MIMEMultipart()
    msg['From'] = smtp_user
    msg['To'] = to_email
    msg['Subject'] = subject

    msg.attach(MIMEText(message, 'plain'))

    try:
        server = smtplib.SMTP(smtp_host, smtp_port)
        server.starttls()
        server.login(smtp_user, smtp_pass)
        server.send_message(msg)
        server.quit()
        logger.info(f"[Email] Successfully sent alert email to {to_email}")
    except Exception as e:
        logger.error(f"[Email] Failed to send email to {to_email}: {e}")
