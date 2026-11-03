from backend.app.core.constants import CATEGORY_MIN_PRIORITY, PRIORITY_KEYWORDS
from backend.app.core.enums import Priority


class KeywordPriorityDetector:
    """sets priority from keywords. in phase 4 this stays as the floor under the ai"""

    def __init__(self, keywords: dict[Priority, list[str]] = PRIORITY_KEYWORDS,
                 default: Priority = Priority.LOW):
        self.keywords = keywords
        self.default = default

    def detect(self, title: str, description: str, category: str = "") -> Priority:
        text = f"{title} {description} {category}".lower()
        found = self.default
        for level in (Priority.CRITICAL, Priority.HIGH, Priority.MEDIUM):
            if any(word in text for word in self.keywords.get(level, [])):
                found = level
                break
        # the category's own minimum wins if it's higher (harassment is always critical)
        floor = CATEGORY_MIN_PRIORITY.get(category)
        order = [Priority.LOW, Priority.MEDIUM, Priority.HIGH, Priority.CRITICAL]
        if floor and order.index(floor) > order.index(found):
            return floor
        return found
