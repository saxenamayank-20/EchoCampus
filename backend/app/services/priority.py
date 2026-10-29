from backend.app.core.constants import PRIORITY_KEYWORDS
from backend.app.core.enums import Priority


class KeywordPriorityDetector:
    """sets priority from keywords. in phase 4 this stays as the floor under the ai"""

    def __init__(self, keywords: dict[Priority, list[str]] = PRIORITY_KEYWORDS,
                 default: Priority = Priority.LOW):
        self.keywords = keywords
        self.default = default

    def detect(self, title: str, description: str, category: str = "") -> Priority:
        text = f"{title} {description} {category}".lower()
        for level in (Priority.CRITICAL, Priority.HIGH, Priority.MEDIUM):
            if any(word in text for word in self.keywords.get(level, [])):
                return level
        return self.default
