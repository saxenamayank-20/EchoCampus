import json
import smtplib
import urllib.error
import urllib.request
from email.message import EmailMessage

from backend.app.core.config import settings

BREVO_URL = "https://api.brevo.com/v3/smtp/email"


class EmailSender:
    """sends mail with brevo (https) or smtp. with neither set it prints the mail instead (dev mode)"""

    def send(self, to: str, subject: str, body: str) -> bool:
        """False when the mail couldn't go out (the reason is in the log)"""
        if settings.brevo_api_key:
            return self._send_brevo(to, subject, body)
        if settings.smtp_host:
            return self._send_smtp(to, subject, body)
        print(f"[EMAIL dev] to={to} | {subject} | {body}")
        return True

    def _send_brevo(self, to: str, subject: str, body: str) -> bool:
        # render free plan blocks the smtp ports, https (443) is fine
        payload = {
            "sender": {"name": "EchoCampus", "email": settings.smtp_from or settings.smtp_user},
            "to": [{"email": to}],
            "subject": subject,
            "textContent": body,
        }
        req = urllib.request.Request(
            BREVO_URL, data=json.dumps(payload).encode(), method="POST",
            headers={"api-key": settings.brevo_api_key, "Content-Type": "application/json",
                     "Accept": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=10):
                return True
        except urllib.error.HTTPError as e:
            # brevo says why in the body, e.g. sender not verified
            print(f"[EMAIL error] to={to} | {subject} | brevo {e.code}: {e.read().decode(errors='replace')[:200]}")
        except OSError as e:
            print(f"[EMAIL error] to={to} | {subject} | {e}")
        return False

    def _send_smtp(self, to: str, subject: str, body: str) -> bool:
        msg = EmailMessage()
        msg["From"] = settings.smtp_from or settings.smtp_user
        msg["To"] = to
        msg["Subject"] = subject
        msg.set_content(body)
        try:
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as server:
                server.starttls()
                server.login(settings.smtp_user, settings.smtp_password)
                server.send_message(msg)
            return True
        except (smtplib.SMTPException, OSError) as e:
            # a failed mail shouldn't break the request, just log it
            print(f"[EMAIL error] to={to} | {subject} | {e}")
            return False


def status_change_mail(sender: EmailSender, to: str, ticket_id: str, status: str, remark: str | None) -> None:
    body = f"Your complaint {ticket_id} is now: {status}."
    if remark:
        body += f"\n\nNote from the manager: {remark}"
    sender.send(to, f"EchoCampus: {ticket_id} is {status}", body)
