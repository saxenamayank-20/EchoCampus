import smtplib
from email.message import EmailMessage

from backend.app.core.config import settings


class EmailSender:
    """sends mail over smtp. without smtp settings it prints the mail instead (dev mode)"""

    def send(self, to: str, subject: str, body: str) -> None:
        if not settings.smtp_host:
            print(f"[EMAIL dev] to={to} | {subject} | {body}")
            return

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
        except (smtplib.SMTPException, OSError) as e:
            # a failed mail shouldn't break the request, just log it
            print(f"[EMAIL error] to={to} | {subject} | {e}")


def status_change_mail(sender: EmailSender, to: str, ticket_id: str, status: str, remark: str | None) -> None:
    body = f"Your complaint {ticket_id} is now: {status}."
    if remark:
        body += f"\n\nNote from the manager: {remark}"
    sender.send(to, f"EchoCampus: {ticket_id} is {status}", body)
