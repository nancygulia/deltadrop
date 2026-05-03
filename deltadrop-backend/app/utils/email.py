"""
email.py — DeltaDrop Email Utility

Sends transactional emails via SMTP.
In development (no SMTP creds set), prints the reset link to the console instead.

To use Mailtrap (recommended for dev):
  1. Sign up at https://mailtrap.io (free)
  2. Go to My Inboxes → SMTP Settings
  3. Add to .env:
       SMTP_USERNAME=<your_username>
       SMTP_USER=<your_username>
       SMTP_PASS=<your_password>

To use Gmail in production:
  1. Enable 2FA on your Google account
  2. Create an App Password at https://myaccount.google.com/apppasswords
  3. Add to .env:
       SMTP_HOST=smtp.gmail.com
       SMTP_PORT=587
       SMTP_USER=youraddress@gmail.com
       SMTP_PASS=<16-char-app-password>
       SMTP_FROM_EMAIL=youraddress@gmail.com
"""

import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from app.core.config import settings

logger = logging.getLogger(__name__)


def _smtp_user() -> str:
    return (settings.SMTP_USER or settings.SMTP_USERNAME or "").strip()


def _smtp_pass() -> str:
    return (settings.SMTP_PASS or settings.SMTP_PASSWORD or "").strip()


def _sender_email() -> str:
    configured = (settings.SMTP_FROM_EMAIL or "").strip()
    smtp_user = _smtp_user()
    if (not configured or configured == "noreply@deltadrop.in") and "@" in smtp_user:
        return smtp_user
    return configured


def _build_alert_html(name: str, product_name: str, current_price: float, target_price: float, product_url: str) -> str:
    return f"""
<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#f4f7fb;font-family:'Inter',Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f4f7fb;padding:40px 0;">
    <tr><td align="center">
      <table width="520" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:16px;overflow:hidden;box-shadow:0 2px 12px rgba(0,0,0,0.08);">
        <!-- Header -->
        <tr>
          <td style="background:linear-gradient(135deg,#ba1a1a,#e53935);padding:32px 40px;">
            <h1 style="margin:0;color:#ffffff;font-size:22px;font-weight:900;letter-spacing:-0.5px;">DeltaDrop 🔔</h1>
            <p style="margin:4px 0 0;color:rgba(255,255,255,0.7);font-size:13px;">Price Target Reached</p>
          </td>
        </tr>
        <!-- Body -->
        <tr>
          <td style="padding:40px;">
            <h2 style="margin:0 0 12px;color:#1f1f1f;font-size:20px;font-weight:700;">Good news, {name}!</h2>
            <p style="margin:0 0 16px;color:#444;font-size:15px;line-height:1.6;">
              The price for <strong>{product_name}</strong> just dropped to <strong>₹{current_price:,.0f}</strong>.
            </p>
            <div style="background:#f9fafb;border-radius:8px;padding:20px;margin-bottom:28px;border:1px solid #eee;">
              <table width="100%">
                <tr>
                  <td><span style="color:#888;font-size:12px;text-transform:uppercase;font-weight:700;">Target Price</span></td>
                  <td><span style="color:#888;font-size:12px;text-transform:uppercase;font-weight:700;">Current Price</span></td>
                </tr>
                <tr>
                  <td><span style="color:#1f1f1f;font-size:18px;font-weight:700;">₹{target_price:,.0f}</span></td>
                  <td><span style="color:#ba1a1a;font-size:18px;font-weight:700;">₹{current_price:,.0f}</span></td>
                </tr>
              </table>
            </div>
            <a href="{product_url}"
               style="display:inline-block;background:linear-gradient(135deg,#003d9b,#0052cc);color:#ffffff;
                      text-decoration:none;padding:14px 32px;border-radius:8px;font-weight:700;font-size:15px;">
              Buy Now
            </a>
          </td>
        </tr>
        <!-- Footer -->
        <tr>
          <td style="background:#f9fafb;padding:20px 40px;border-top:1px solid #eee;">
            <p style="margin:0;color:#bbb;font-size:11px;">
              © 2026 DeltaDrop Precision Ledger · Alerts sent via near real-time polling
            </p>
          </td>
        </tr>
      </table>
    </td></tr>
  </table>
</body>
</html>
"""


def _build_reset_html(reset_url: str, name: str) -> str:
    return f"""
<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#f4f7fb;font-family:'Inter',Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f4f7fb;padding:40px 0;">
    <tr><td align="center">
      <table width="520" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:16px;overflow:hidden;box-shadow:0 2px 12px rgba(0,0,0,0.08);">
        <!-- Header -->
        <tr>
          <td style="background:linear-gradient(135deg,#003d9b,#0052cc);padding:32px 40px;">
            <h1 style="margin:0;color:#ffffff;font-size:22px;font-weight:900;letter-spacing:-0.5px;">DeltaDrop</h1>
            <p style="margin:4px 0 0;color:rgba(255,255,255,0.7);font-size:13px;">The Precision Price Ledger</p>
          </td>
        </tr>
        <!-- Body -->
        <tr>
          <td style="padding:40px;">
            <h2 style="margin:0 0 12px;color:#1f1f1f;font-size:20px;font-weight:700;">Reset your password</h2>
            <p style="margin:0 0 8px;color:#444;font-size:15px;line-height:1.6;">
              Hi {name}, we received a request to reset the password for your DeltaDrop account.
              Click the button below to choose a new password.
            </p>
            <p style="margin:0 0 28px;color:#888;font-size:13px;">This link expires in <strong>30 minutes</strong>.</p>
            <a href="{reset_url}"
               style="display:inline-block;background:linear-gradient(135deg,#003d9b,#0052cc);color:#ffffff;
                      text-decoration:none;padding:14px 32px;border-radius:8px;font-weight:700;font-size:15px;">
              Reset Password
            </a>
            <p style="margin:32px 0 0;color:#aaa;font-size:12px;line-height:1.6;">
              If you didn't request this, you can safely ignore this email — your password will remain unchanged.<br/>
              <br/>
              Or copy this link into your browser:<br/>
              <span style="color:#003d9b;word-break:break-all;">{reset_url}</span>
            </p>
          </td>
        </tr>
        <!-- Footer -->
        <tr>
          <td style="background:#f9fafb;padding:20px 40px;border-top:1px solid #eee;">
            <p style="margin:0;color:#bbb;font-size:11px;">
              © 2026 DeltaDrop Precision Ledger · India Editorial Node
            </p>
          </td>
        </tr>
      </table>
    </td></tr>
  </table>
</body>
</html>
"""


def send_password_reset_email(to_email: str, to_name: str, reset_url: str) -> bool:
    """
    Sends a password reset email.
    Returns True on success, False on failure.
    Falls back to console logging in dev when SMTP creds are not configured.
    """
    smtp_user = _smtp_user()
    smtp_pass = _smtp_pass()
    sender_email = _sender_email()

    # Dev fallback: no SMTP creds configured
    if not smtp_user or not smtp_pass:
        logger.warning("=" * 60)
        logger.warning("SMTP NOT CONFIGURED — SIMULATED EMAIL (dev mode)")
        logger.warning(f"To     : {to_email}")
        logger.warning(f"Subject: Reset your DeltaDrop password")
        logger.warning(f"Link   : {reset_url}")
        logger.warning("=" * 60)
        print(f"\n{'='*60}")
        print(f"📧  PASSWORD RESET EMAIL (dev — no SMTP configured)")
        print(f"    To     : {to_email}")
        print(f"    Name   : {to_name}")
        print(f"    Link   : {reset_url}")
        print(f"{'='*60}\n")
        return True  # Pretend it was sent

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = "Reset your DeltaDrop password"
        msg["From"]    = f"{settings.SMTP_FROM_NAME} <{sender_email}>"
        msg["To"]      = to_email

        html_body = _build_reset_html(reset_url, to_name or to_email.split("@")[0])
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as smtp:
            smtp.ehlo()
            smtp.starttls()
            smtp.login(smtp_user, smtp_pass)
            smtp.sendmail(sender_email, to_email, msg.as_string())

        logger.info(f"Password reset email sent to {to_email}")
        return True

    except Exception as e:
        logger.error(f"Failed to send reset email to {to_email}: {e}")
        return False
def send_price_alert_email(to_email: str, name: str, product_name: str, current_price: float, target_price: float, product_url: str) -> bool:
    """Sends a price drop notification email."""
    smtp_user = _smtp_user()
    smtp_pass = _smtp_pass()
    sender_email = _sender_email()

    if not smtp_user or not smtp_pass:
        logger.warning("=" * 60)
        logger.warning("SMTP NOT CONFIGURED — SIMULATED EMAIL (dev mode)")
        logger.warning(f"To     : {to_email}")
        logger.warning(f"Product: {product_name}")
        logger.warning(f"Price  : ₹{current_price:,.0f} (Target: ₹{target_price:,.0f})")
        logger.warning("=" * 60)
        return True

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"🔔 Price Drop Alert: {product_name}"
        msg["From"]    = f"{settings.SMTP_FROM_NAME} <{sender_email}>"
        msg["To"]      = to_email

        html_body = _build_alert_html(name or to_email.split("@")[0], product_name, current_price, target_price, product_url)
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as smtp:
            smtp.ehlo()
            smtp.starttls()
            smtp.login(smtp_user, smtp_pass)
            smtp.sendmail(sender_email, to_email, msg.as_string())

        logger.info(f"Price alert email sent to {to_email} for {product_name}")
        return True
    except Exception as e:
        logger.error(f"Failed to send alert email to {to_email}: {e}")
        return False
