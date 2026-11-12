import io
import json
import urllib.error

import backend.app.services.email_service as email_module
from backend.app.core.config import settings
from backend.app.services.email_service import BREVO_URL, EmailSender


class FakeResponse:
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def test_brevo_key_sends_over_https(monkeypatch):
    sent = []
    monkeypatch.setattr(settings, "brevo_api_key", "test-key")
    monkeypatch.setattr(settings, "smtp_from", "portal@example.com")
    monkeypatch.setattr(email_module.urllib.request, "urlopen",
                        lambda req, timeout: sent.append(req) or FakeResponse())

    EmailSender().send("student@example.com", "Your code", "123456")

    req = sent[0]
    body = json.loads(req.data)
    assert req.full_url == BREVO_URL and req.get_method() == "POST"
    assert req.get_header("Api-key") == "test-key"
    assert body["sender"]["email"] == "portal@example.com"
    assert body["to"] == [{"email": "student@example.com"}]
    assert body["subject"] == "Your code" and body["textContent"] == "123456"


def test_brevo_error_is_logged_not_raised(monkeypatch, capsys):
    def fail(req, timeout):
        raise urllib.error.HTTPError(BREVO_URL, 400, "Bad Request", {}, io.BytesIO(b'{"message":"sender not valid"}'))

    monkeypatch.setattr(settings, "brevo_api_key", "test-key")
    monkeypatch.setattr(email_module.urllib.request, "urlopen", fail)

    EmailSender().send("student@example.com", "Your code", "123456")   # must not raise
    assert "brevo 400" in capsys.readouterr().out


def test_no_settings_prints_the_mail(monkeypatch, capsys):
    monkeypatch.setattr(settings, "brevo_api_key", "")
    monkeypatch.setattr(settings, "smtp_host", "")
    EmailSender().send("student@example.com", "Your code", "123456")
    assert "[EMAIL dev]" in capsys.readouterr().out
