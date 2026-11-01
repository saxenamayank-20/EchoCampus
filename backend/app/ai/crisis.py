"""Self-harm / crisis check. Plain keywords on purpose: this must work even when the ai is down."""
import re

from backend.app.core.config import settings

CRISIS_PATTERNS = [
    r"suicid\w*", r"kill (myself|me)", r"end (it all|my life)", r"want to die", r"self[- ]?harm\w*",
    r"hurt(ing)? myself", r"cut(ting)? myself", r"no reason to live", r"mental health", r"depress\w*",
]
_crisis = re.compile(r"\b(" + "|".join(CRISIS_PATTERNS) + r")\b", re.IGNORECASE)


def is_crisis(*texts: str) -> bool:
    return bool(_crisis.search(" ".join(texts)))


def support_message() -> dict:
    return {
        "message": ("You are not alone, and it's okay to ask for help. Your complaint is marked Critical and "
                    "a manager will reach out quickly. If you feel unsafe right now, please talk to someone today."),
        "counsellor": settings.counsellor_contact,
        "helpline": settings.crisis_helpline,
    }
