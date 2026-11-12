# ruff: noqa: E501  (long html lines read better unwrapped)
"""html emails. mail apps ignore <style> blocks and css files, so everything is inline and laid out with tables"""
from html import escape

from backend.app.core.config import settings

LIME = "#b6ff3b"
DARK = "#0b1220"
GREEN = "#3f6212"
TAGLINE = "Every campus complaint, heard."


def _logo_url() -> str:
    return settings.email_logo_url or f"{settings.frontend_origin}/icon-192.png"


def _first_name(name: str) -> str:
    return name.split()[0] if name.split() else name


def _layout(heading: str, subheading: str, body: str, footer_note: str) -> str:
    """the shared frame: dark header with a lime line, white card, logo + tagline at the bottom"""
    return f"""<!doctype html>
<html><body style="margin:0;padding:0;background:#f1f5f9;font-family:Segoe UI,Helvetica,Arial,sans-serif;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f1f5f9;padding:24px 12px;">
<tr><td align="center">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:560px;background:#ffffff;border-radius:16px;overflow:hidden;">

  <tr><td style="background:{DARK};padding:28px 32px;">
    <div style="color:{LIME};font-size:13px;font-weight:600;letter-spacing:2px;text-transform:uppercase;">EchoCampus</div>
    <div style="color:#ffffff;font-size:26px;font-weight:700;margin-top:8px;line-height:1.3;">{heading}</div>
    <div style="color:#cbd5e1;font-size:15px;margin-top:6px;">{subheading}</div>
  </td></tr>
  <tr><td style="height:4px;background:{LIME};font-size:0;line-height:0;">&nbsp;</td></tr>

  {body}

  <tr><td style="padding:24px 32px 28px;border-top:1px solid #e2e8f0;" align="center">
    <img src="{escape(_logo_url())}" width="56" height="56" alt="EchoCampus" style="display:block;border-radius:12px;margin:0 auto;">
    <div style="color:{DARK};font-weight:700;font-size:16px;margin-top:10px;">EchoCampus</div>
    <div style="color:#64748b;font-size:13px;margin-top:2px;font-style:italic;">{TAGLINE}</div>
    <div style="color:#94a3b8;font-size:12px;margin-top:14px;line-height:1.5;">{footer_note}</div>
  </td></tr>

</table>
</td></tr>
</table>
</body></html>"""


def _paragraph(html: str) -> str:
    return f"""<tr><td style="padding:28px 32px 8px;">
    <p style="margin:0;color:#334155;font-size:15px;line-height:1.6;">{html}</p>
  </td></tr>"""


def _big_box(label: str, value: str, note: str) -> str:
    """dashed lime box for the student id or a code"""
    return f"""<tr><td style="padding:16px 32px;">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0"
      style="background:#f6ffe3;border:2px dashed {GREEN};border-radius:12px;">
      <tr><td align="center" style="padding:22px 16px;">
        <div style="color:{GREEN};font-size:12px;font-weight:700;letter-spacing:2px;text-transform:uppercase;">{label}</div>
        <div style="color:{DARK};font-size:38px;font-weight:800;letter-spacing:6px;font-family:Consolas,Menlo,monospace;margin-top:6px;">{value}</div>
        <div style="color:#475569;font-size:13px;margin-top:8px;">{note}</div>
      </td></tr>
    </table>
  </td></tr>"""


def _button(url: str, text: str) -> str:
    return f"""<tr><td align="center" style="padding:12px 32px 8px;">
    <a href="{escape(url)}" style="display:inline-block;background:{LIME};color:{DARK};font-weight:700;font-size:15px;
      text-decoration:none;padding:13px 28px;border-radius:10px;">{text}</a>
  </td></tr>"""


def _ignore_note(email: str) -> str:
    return f"You got this email because {escape(email)} has an EchoCampus account.<br>If you didn't ask for this, you can safely ignore it."


def welcome_email(name: str, student_id: str, email: str) -> tuple[str, str, str]:
    """sent right after the email is verified: (subject, plain text, html)"""
    first = _first_name(name)
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
        f"EchoCampus - {TAGLINE}\n"
        f"You got this email because {email} was used to register. If that wasn't you, just ignore it."
    )

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
    body = (
        _paragraph("EchoCampus is your <b>one-stop place for every problem you face on campus</b>. From a broken fan in the "
                   "hostel to a result that doesn't add up: raise it in a minute, see exactly who is handling it, and close it "
                   "only when it's really fixed. No more lost complaints, no more running from office to office.")
        + _big_box("Your student ID", escape(student_id),
                   "Save it somewhere safe. You need it with your password every time you sign in.")
        + _button(login_url, "Sign in to EchoCampus &rarr;")
        + f"""<tr><td style="padding:20px 32px 8px;">
    <div style="color:{DARK};font-size:16px;font-weight:700;margin-bottom:4px;">What you can do</div>
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0">{rows}</table>
  </td></tr>"""
    )
    footer = f"You got this email because {escape(email)} was used to register.<br>If that wasn't you, you can safely ignore it."
    html = _layout(f"Welcome aboard, {escape(first)}! &#127891;", "Your email is verified and your account is ready.", body, footer)
    return subject, text, html


# what each kind of code email says
CODE_TEXT = {
    "verify": {
        "subject": "{code} is your EchoCampus verification code",
        "heading": "Verify your email &#9993;&#65039;",
        "sub": "One quick step and your account is ready.",
        "intro": "Thanks for signing up! Enter this code on the verification page to confirm your email. "
                 "Right after that you'll get your student ID.",
        "label": "Verification code",
    },
    "recovery": {
        "subject": "{code} is your EchoCampus recovery code",
        "heading": "Let's find your account &#128269;",
        "sub": "Someone asked to recover the student ID for this email.",
        "intro": "Enter this recovery code on the <b>Forgot details</b> page and we'll show you your student ID.",
        "label": "Recovery code",
    },
    "login": {
        "subject": "{code} is your EchoCampus login code",
        "heading": "Your one-time login code &#128273;",
        "sub": "Use it instead of your password, just this once.",
        "intro": "Sign in with your student ID and this code. After you're in, please set a new password "
                 "from <b>My account</b> so you can sign in normally next time.",
        "label": "Login code",
    },
}


def code_email(purpose: str, name: str, code: str, email: str) -> tuple[str, str, str]:
    """verification / recovery / login code mail: (subject, plain text, html)"""
    t = CODE_TEXT[purpose]
    first = _first_name(name)
    minutes = settings.otp_expire_minutes
    plain_intro = t["intro"].replace("<b>", "").replace("</b>", "")
    text = (
        f"Hi {first},\n\n{plain_intro}\n\n"
        f"{t['label']}: {code}\n"
        f"It works once and expires in {minutes} minutes. Never share it with anyone, EchoCampus staff will never ask for it.\n\n"
        f"EchoCampus - {TAGLINE}\n"
        f"You got this email because {email} has an EchoCampus account. If you didn't ask for this, just ignore it."
    )
    body = (
        _paragraph(f"Hi {escape(first)}, {t['intro']}")
        + _big_box(t["label"], escape(code),
                   f"Works once and expires in {minutes} minutes. Never share it, EchoCampus staff will never ask for it.")
    )
    html = _layout(t["heading"], t["sub"], body, _ignore_note(email))
    return t["subject"].format(code=code), text, html


def password_changed_email(name: str, email: str) -> tuple[str, str, str]:
    """heads-up after any password change"""
    first = _first_name(name)
    contact = settings.support_contact()
    subject = "Your EchoCampus password was changed"
    text = (
        f"Hi {first},\n\nThe password for your EchoCampus account was just changed.\n"
        f"If this was you, there's nothing else to do.\n"
        f"If it wasn't you, please contact the technical team right away: {contact}\n\n"
        f"EchoCampus - {TAGLINE}"
    )
    body = (
        _paragraph(f"Hi {escape(first)}, the password for your EchoCampus account was just changed. "
                   "If this was you, there's nothing else to do.")
        + f"""<tr><td style="padding:16px 32px;">
    <div style="background:#fef2f2;border:1px solid #fecaca;border-radius:12px;padding:16px;color:#991b1b;font-size:14px;line-height:1.5;">
      <b>Wasn't you?</b> Please contact the technical team right away at <b>{escape(contact)}</b>.
    </div>
  </td></tr>"""
        + _button(f"{settings.frontend_origin}/login", "Sign in to EchoCampus &rarr;")
    )
    html = _layout("Password changed &#128274;", "A quick security heads-up.", body, _ignore_note(email))
    return subject, text, html
