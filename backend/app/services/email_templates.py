# ruff: noqa: E501  (long html lines read better unwrapped)
"""html emails. mail apps ignore <style> blocks and css files, so everything is inline and laid out with tables"""
from html import escape

from backend.app.core.config import settings

LIME = "#b6ff3b"
DARK = "#0b1220"
GREEN = "#3f6212"


def _logo_url() -> str:
    return settings.email_logo_url or f"{settings.frontend_origin}/icon-192.png"


def welcome_email(name: str, student_id: str, email: str) -> tuple[str, str, str]:
    """sent right after the email is verified: (subject, plain text, html)"""
    first = name.split()[0] if name.split() else name
    login_url = f"{settings.frontend_origin}/login?user={student_id}"
    subject = f"Welcome to EchoCampus, {first}! Your student ID is inside"

    text = (
        f"Hi {first},\n\n"
        "Welcome to EchoCampus, your one-stop place for every problem you face on campus.\n"
        "From a broken fan in the hostel to a result that doesn't add up, raise it in a minute,\n"
        "see who is handling it, and close it only when it's really fixed.\n\n"
        f"Your student ID: {student_id}\n"
        "Please save it. You need it with your password every time you sign in.\n\n"
        f"Sign in: {login_url}\n\n"
        "What you can do:\n"
        "- Raise a complaint with photos or PDFs as proof, and track it step by step\n"
        "- Ask the assistant about rules, fees and timings, straight from the student handbook\n"
        "- Back a complaint others already raised with \"I have this issue too\"\n\n"
        "EchoCampus - every campus complaint, heard.\n"
        f"You got this email because {email} was used to register. If that wasn't you, just ignore it."
    )

    n, sid, mail = escape(first), escape(student_id), escape(email)
    features = [
        ("&#128221;", "Raise &amp; track", "Add photos or PDFs as proof and follow every step until it's fixed."),
        ("&#128218;", "Ask the handbook", "Rules, fees, timings: answers straight from the college documents."),
        ("&#129309;", "Stronger together", "Back a complaint others raised with &ldquo;I have this issue too&rdquo;."),
    ]
    rows = "".join(
        f"""<tr><td style="padding:8px 0;vertical-align:top;width:36px;font-size:22px;">{icon}</td>
        <td style="padding:8px 0;"><div style="font-weight:600;color:{DARK};font-size:15px;">{title}</div>
        <div style="color:#475569;font-size:14px;line-height:1.5;">{desc}</div></td></tr>"""
        for icon, title, desc in features
    )

    html = f"""<!doctype html>
<html><body style="margin:0;padding:0;background:#f1f5f9;font-family:Segoe UI,Helvetica,Arial,sans-serif;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f1f5f9;padding:24px 12px;">
<tr><td align="center">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:560px;background:#ffffff;border-radius:16px;overflow:hidden;">

  <tr><td style="background:{DARK};padding:28px 32px;">
    <div style="color:{LIME};font-size:13px;font-weight:600;letter-spacing:2px;text-transform:uppercase;">EchoCampus</div>
    <div style="color:#ffffff;font-size:26px;font-weight:700;margin-top:8px;line-height:1.3;">Welcome aboard, {n}! &#127891;</div>
    <div style="color:#cbd5e1;font-size:15px;margin-top:6px;">Your email is verified and your account is ready.</div>
  </td></tr>
  <tr><td style="height:4px;background:{LIME};font-size:0;line-height:0;">&nbsp;</td></tr>

  <tr><td style="padding:28px 32px 8px;">
    <p style="margin:0;color:#334155;font-size:15px;line-height:1.6;">
      EchoCampus is your <b>one-stop place for every problem you face on campus</b>. From a broken fan in the
      hostel to a result that doesn't add up: raise it in a minute, see exactly who is handling it, and close it
      only when it's really fixed. No more lost complaints, no more running from office to office.
    </p>
  </td></tr>

  <tr><td style="padding:16px 32px;">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0"
      style="background:#f6ffe3;border:2px dashed {GREEN};border-radius:12px;">
      <tr><td align="center" style="padding:22px 16px;">
        <div style="color:{GREEN};font-size:12px;font-weight:700;letter-spacing:2px;text-transform:uppercase;">Your student ID</div>
        <div style="color:{DARK};font-size:38px;font-weight:800;letter-spacing:4px;font-family:Consolas,Menlo,monospace;margin-top:6px;">{sid}</div>
        <div style="color:#475569;font-size:13px;margin-top:8px;">Save it somewhere safe. You need it with your password every time you sign in.</div>
      </td></tr>
    </table>
  </td></tr>

  <tr><td align="center" style="padding:12px 32px 8px;">
    <a href="{escape(login_url)}" style="display:inline-block;background:{LIME};color:{DARK};font-weight:700;font-size:15px;
      text-decoration:none;padding:13px 28px;border-radius:10px;">Sign in to EchoCampus &rarr;</a>
  </td></tr>

  <tr><td style="padding:20px 32px 8px;">
    <div style="color:{DARK};font-size:16px;font-weight:700;margin-bottom:4px;">What you can do</div>
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0">{rows}</table>
  </td></tr>

  <tr><td style="padding:24px 32px 28px;border-top:1px solid #e2e8f0;" align="center">
    <img src="{escape(_logo_url())}" width="56" height="56" alt="EchoCampus" style="display:block;border-radius:12px;margin:0 auto;">
    <div style="color:{DARK};font-weight:700;font-size:16px;margin-top:10px;">EchoCampus</div>
    <div style="color:#64748b;font-size:13px;margin-top:2px;font-style:italic;">Every campus complaint, heard.</div>
    <div style="color:#94a3b8;font-size:12px;margin-top:14px;line-height:1.5;">
      You got this email because {mail} was used to register.<br>If that wasn't you, you can safely ignore it.
    </div>
  </td></tr>

</table>
</td></tr>
</table>
</body></html>"""
    return subject, text, html
