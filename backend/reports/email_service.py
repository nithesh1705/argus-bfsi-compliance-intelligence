"""
ARGUS — Email Delivery Service (backend/reports/email_service.py)
Phase 15: Outbound Compliance Report Dispatch via SMTP & Elastic Connectors
"""

import os
import re
import asyncio
import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List, Dict, Any, Optional, Tuple
import httpx

logger = logging.getLogger("argus.reports.email")

EMAIL_REGEX = re.compile(
    r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
)


class EmailServiceError(Exception):
    """Controlled exception for email delivery failures."""
    def __init__(self, message: str, error_code: str = "EMAIL_SEND_FAILED", status_code: int = 502):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.status_code = status_code


class RecipientValidationError(Exception):
    """Validation failure on email recipients."""
    def __init__(self, message: str, error_code: str = "INVALID_RECIPIENT", status_code: int = 422):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.status_code = status_code


def get_smtp_config() -> Optional[Dict[str, Any]]:
    """Resolve SMTP server credentials from environment."""
    host = os.getenv("SMTP_HOST", "").strip()
    user = os.getenv("SMTP_USER", "").strip()
    password = os.getenv("SMTP_PASSWORD", "").strip()
    if not host or not user or not password:
        return None

    port = int(os.getenv("SMTP_PORT", "587"))
    use_tls = os.getenv("SMTP_USE_TLS", "true").lower() in ("true", "1", "yes")
    from_email = os.getenv("SMTP_FROM_EMAIL", user).strip()
    from_name = os.getenv("SMTP_FROM_NAME", "ARGUS Compliance Platform").strip()

    return {
        "host": host,
        "port": port,
        "user": user,
        "password": password,
        "use_tls": use_tls,
        "from_email": from_email,
        "from_name": from_name,
    }


def get_kibana_config() -> Dict[str, Any]:
    """Resolve Kibana email connector configuration from environment."""
    es_url = os.getenv("ELASTICSEARCH_URL", "").strip().rstrip("/")
    default_kb_url = ""
    if es_url:
        default_kb_url = es_url.replace(".es.", ".kb.").replace(":443", "")

    kibana_base_url = os.getenv("KIBANA_BASE_URL", default_kb_url).strip().rstrip("/")
    connector_id = os.getenv("KIBANA_CONNECTOR_ID", "argus-mail").strip()
    api_key = os.getenv("ELASTIC_API_KEY") or os.getenv("ELASTICSEARCH_API_KEY", "")
    timeout_seconds = float(os.getenv("EMAIL_REQUEST_TIMEOUT_SECONDS", "20"))
    max_recipients = int(os.getenv("MAX_REPORT_RECIPIENTS", "5"))
    internal_domains = [
        d.strip().lower()
        for d in os.getenv("ARGUS_INTERNAL_EMAIL_DOMAINS", "argus.com,gmail.com").split(",")
        if d.strip()
    ]

    return {
        "kibana_base_url": kibana_base_url,
        "connector_id": connector_id,
        "api_key": api_key.strip(),
        "timeout_seconds": timeout_seconds,
        "max_recipients": max_recipients,
        "internal_domains": internal_domains,
    }


def validate_recipients(recipients: Optional[List[str]]) -> Tuple[List[str], str]:
    """Validate, sanitize, and classify email recipients."""
    config = get_kibana_config()
    max_recipients = config["max_recipients"]
    internal_domains = config["internal_domains"]

    if not recipients or not isinstance(recipients, list):
        raise RecipientValidationError("At least one recipient email address is required.", error_code="RECIPIENT_REQUIRED")

    cleaned: List[str] = []
    seen = set()
    has_external = False

    for item in recipients:
        if not item or not isinstance(item, str):
            continue

        if "\r" in item or "\n" in item or "%0a" in item.lower() or "%0d" in item.lower():
            logger.warning(f"CRLF control character detected in recipient: {repr(item)}")
            raise RecipientValidationError("Invalid email recipient: Control characters are not allowed.", error_code="INVALID_RECIPIENT")

        normalized = item.strip().lower()
        if not normalized:
            continue

        if not EMAIL_REGEX.match(normalized):
            raise RecipientValidationError(f"Invalid email address syntax: '{item}'.", error_code="INVALID_RECIPIENT")

        if normalized not in seen:
            seen.add(normalized)
            cleaned.append(normalized)

            domain = normalized.split("@")[-1]
            if domain not in internal_domains:
                has_external = True

    if not cleaned:
        raise RecipientValidationError("At least one valid recipient email is required.", error_code="RECIPIENT_REQUIRED")

    if len(cleaned) > max_recipients:
        raise RecipientValidationError(
            f"Recipient list exceeds maximum allowed limit of {max_recipients} recipients.",
            error_code="MAX_RECIPIENTS_EXCEEDED"
        )

    domain_class = "external" if has_external else "internal"
    return cleaned, domain_class


def sanitize_header_text(text: str) -> str:
    """Sanitize subject and header fields to prevent CRLF injection."""
    if not text:
        return ""
    cleaned = text.replace("\r", " ").replace("\n", " ").strip()
    return re.sub(r"\s+", " ", cleaned)


def _send_smtp_sync(
    smtp_cfg: Dict[str, Any],
    recipients: List[str],
    subject: str,
    html_body: str,
    plain_text: Optional[str] = None
) -> Dict[str, Any]:
    """Synchronous SMTP delivery helper executed in worker thread."""
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    from_name = smtp_cfg.get("from_name")
    from_email = smtp_cfg["from_email"]
    msg["From"] = f"{from_name} <{from_email}>" if from_name else from_email
    msg["To"] = ", ".join(recipients)

    if plain_text:
        msg.attach(MIMEText(plain_text, "plain", "utf-8"))
    if html_body:
        msg.attach(MIMEText(html_body, "html", "utf-8"))

    host = smtp_cfg["host"]
    port = smtp_cfg["port"]
    user = smtp_cfg["user"]
    password = smtp_cfg["password"]
    use_tls = smtp_cfg["use_tls"]

    if port == 465:
        server = smtplib.SMTP_SSL(host, port, timeout=25)
    else:
        server = smtplib.SMTP(host, port, timeout=25)
        if use_tls:
            server.starttls()

    try:
        if user and password:
            server.login(user, password)
        server.sendmail(from_email, recipients, msg.as_string())
    finally:
        try:
            server.quit()
        except Exception:
            pass

    return {
        "success": True,
        "recipients": recipients,
        "status": "SENT",
        "provider": "SMTP",
    }


async def send_email(
    recipients: List[str],
    subject: str,
    html_body: str,
    plain_text: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Send email through SMTP (Gmail / SendGrid / TLS) or Elastic Kibana connector.
    """
    clean_recipients, domain_class = validate_recipients(recipients)
    clean_subject = sanitize_header_text(subject)

    # 1. Primary path: SMTP if configured
    smtp_cfg = get_smtp_config()
    if smtp_cfg:
        logger.info(
            f"[Email] Dispatching via SMTP ({smtp_cfg['host']}:{smtp_cfg['port']}) "
            f"to {clean_recipients}"
        )
        try:
            return await asyncio.to_thread(
                _send_smtp_sync, smtp_cfg, clean_recipients, clean_subject, html_body, plain_text
            )
        except Exception as smtp_err:
            logger.exception(f"[Email] SMTP dispatch failed: {smtp_err}")
            raise EmailServiceError(f"SMTP delivery failed: {smtp_err}")

    # 2. Secondary path: Kibana action connector
    config = get_kibana_config()
    kibana_base_url = config["kibana_base_url"]
    connector_id = config["connector_id"]
    api_key = config["api_key"]
    timeout_sec = config["timeout_seconds"]

    if kibana_base_url and api_key:
        endpoint = f"{kibana_base_url}/api/actions/connector/{connector_id}/_execute"
        headers = {
            "Content-Type": "application/json",
            "kbn-xsrf": "true",
            "Authorization": f"ApiKey {api_key}",
        }
        payload = {
            "params": {
                "to": clean_recipients,
                "subject": clean_subject,
                "message": plain_text or "Please view the HTML version of this compliance report.",
                "messageHTML": html_body,
            }
        }

        try:
            async with httpx.AsyncClient(timeout=timeout_sec) as client:
                response = await client.post(endpoint, headers=headers, json=payload)
            if response.status_code != 200:
                raise EmailServiceError(f"Kibana connector returned status {response.status_code}.")
            return {
                "success": True,
                "recipients": clean_recipients,
                "status": "SENT",
                "provider": "KIBANA",
            }
        except Exception as kb_err:
            logger.exception(f"[Email] Kibana connector dispatch failed: {kb_err}")
            raise EmailServiceError(f"Kibana email dispatch failed: {kb_err}")

    # Neither configured
    raise EmailServiceError(
        "No email delivery provider is configured. Please configure SMTP_HOST/SMTP_USER/SMTP_PASSWORD in Cloud Run."
    )
