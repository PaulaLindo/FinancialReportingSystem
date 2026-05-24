"""Optional SMTP email delivery (no-op when SMTP_HOST is unset)."""

from __future__ import annotations

import logging
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

logger = logging.getLogger(__name__)

PREF_MAP = {
    "submission_pending_review": "email_on_submission",
    "submission_pending_cfo": "email_on_approval",
    "submission_approved": "email_on_approval",
    "submission_rejected": "email_on_rejection",
    "workflow_comment": "email_on_comment",
    "sla_warning": "email_on_sla_warning",
}


def is_configured() -> bool:
    return bool(os.getenv("SMTP_HOST") and os.getenv("SMTP_FROM"))


def user_wants_email(user_id: str, message_type: str) -> bool:
    if not is_configured():
        return False
    pref_col = PREF_MAP.get(message_type, "email_on_submission")
    client = None
    try:
        from utils.supabase_service_client import get_service_supabase_client

        client = get_service_supabase_client()
        if client:
            res = (
                client.table("notification_preferences")
                .select(pref_col)
                .eq("user_id", str(user_id))
                .limit(1)
                .execute()
            )
            if res.data:
                return bool(res.data[0].get(pref_col, True))
    except Exception:
        pass
    return True


def _recipient_email(user_id: str) -> Optional[str]:
    try:
        from models.supabase_auth_models import SupabaseAuthModel

        user = SupabaseAuthModel().get_user_by_id(str(user_id))
        if user and user.get("email"):
            return str(user["email"]).strip()
    except Exception:
        pass
    return None


def send_email(to: str, subject: str, body: str, *, html: Optional[str] = None) -> bool:
    if not is_configured() or not to:
        return False
    host = os.getenv("SMTP_HOST", "")
    port = int(os.getenv("SMTP_PORT", "587"))
    user = os.getenv("SMTP_USER", "")
    password = os.getenv("SMTP_PASSWORD", "")
    from_addr = os.getenv("SMTP_FROM", "")
    use_tls = os.getenv("SMTP_USE_TLS", "true").lower() in ("1", "true", "yes")

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject[:500]
    msg["From"] = from_addr
    msg["To"] = to
    msg.attach(MIMEText(body, "plain", "utf-8"))
    if html:
        msg.attach(MIMEText(html, "html", "utf-8"))

    try:
        if use_tls:
            with smtplib.SMTP(host, port, timeout=30) as smtp:
                smtp.ehlo()
                smtp.starttls()
                if user and password:
                    smtp.login(user, password)
                smtp.sendmail(from_addr, [to], msg.as_string())
        else:
            with smtplib.SMTP(host, port, timeout=30) as smtp:
                if user and password:
                    smtp.login(user, password)
                smtp.sendmail(from_addr, [to], msg.as_string())
        return True
    except Exception as exc:
        logger.warning("SMTP send failed to %s: %s", to, exc)
        return False


def notify_user_email(
    user_id: str,
    *,
    message_type: str,
    title: str,
    body: str,
) -> bool:
    if not user_wants_email(user_id, message_type):
        return False
    email = _recipient_email(user_id)
    if not email:
        return False
    return send_email(email, title, body)
