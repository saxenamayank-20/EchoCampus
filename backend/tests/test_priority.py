import pytest

from backend.app.core.enums import Priority
from backend.app.services.priority import KeywordPriorityDetector

detector = KeywordPriorityDetector()


@pytest.mark.parametrize("title,description,expected", [
    ("Ragging in hostel", "seniors are troubling us", Priority.CRITICAL),
    ("Need help", "I feel unsafe, it is an EMERGENCY", Priority.CRITICAL),
    ("Exam result missing", "my marks are not shown", Priority.HIGH),
    ("Projector broken", "room 204", Priority.HIGH),
    ("Wifi slow", "in block C", Priority.MEDIUM),
    ("Water cooler", "please clean it", Priority.LOW),
])
def test_keyword_priority(title, description, expected):
    assert detector.detect(title, description) == expected


def test_highest_level_wins():
    # has a high word (exam) and a critical word (harassment)
    assert detector.detect("Exam hall", "harassment by invigilator") == Priority.CRITICAL


def test_category_is_part_of_the_text():
    assert detector.detect("Food", "too oily", "Canteen") == Priority.MEDIUM
