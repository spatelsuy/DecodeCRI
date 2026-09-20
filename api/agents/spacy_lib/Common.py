import json
import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import spacy
import dateparser

# ==========================================================
# CONFIG
# ==========================================================
# Bare unit words (no digit attached) that spaCy/dateparser often mislabel as DATE/TIME even when they're just ordinary nouns
# (e.g. "meeting minutes", "see you in a few days").

CMN_GENERIC_UNIT_WORDS = {
    "second", "seconds",
    "minute", "minutes",
    "hour", "hours",
    "day", "days",
    "week", "weeks",
    "month", "months",
    "year", "years",
}

CMN_NUMBER_WORD_RE = re.compile(
    r"^(a|an|one|two|three|four|five|six|seven|eight|nine|ten|\d+)$", re.IGNORECASE
)
 
CMN_CORRECTION_MARKERS = [
    "no no",
    "actually",
    "instead",
    "wait",
    "correction",
    "i mean"
]

# Phrases that signal "what follows is a date", used to safely accept a bare N/N numeric pattern as a date rather than a fraction/score/
# ratio (e.g. "1/2 cup", "the score was 7/20"). Longer/more specific phrases first so a substring match like "by" inside "due by" doesn't
# fire before the fuller phrase is checked.
CMN_DATE_ANCHOR_PHRASES = [
    "week of", "weeks of",
    "due by", "due on", "due before",
    "before", "after", "since", "until", "from",
    "by", "on",
]
 
CMN_DATE_SLASH_RE = re.compile(
    r"\b(1[0-2]|0?[1-9])/(3[01]|[12]\d|0?[1-9])(?:/\d{2,4})?\b"
)

CMN_DATE_WORD_RE = re.compile(
    r"\b(today|tomorrow|tonight|yesterday|monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b", re.IGNORECASE
)

CMN_DAYPART_TIMES = {
    "morning": (9, 0), "afternoon": (15, 0), "after lunch": (14, 0),
    "evening": (18, 0), "night": (21, 0), "noon": (12, 0), "midnight": (0, 0),
}

CMN_WEEKDAY_RE = re.compile(
    r"\b(?:(this|next|coming)\s+)?"
    r"(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b",
    re.IGNORECASE
)

CMN_WEEKDAY_QUALIFIED_DAYPART_RE = re.compile(
    r"\b(this|next|coming)\s+"
    r"(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\s+"
    r"(morning|afternoon|evening|night)\b",
    re.IGNORECASE
)

CMN_WEEKDAY_DAYPART_RE = re.compile(
    r"(?<!this )(?<!next )(?<!coming )\b"
    r"(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\s+"
    r"(morning|afternoon|evening|night|noon|midnight)\b",
    re.IGNORECASE
)

CMN_WEEKDAY_QUALIFIER_RE = re.compile(
    r"\b(this|next|coming)\s+"
    r"(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b"
    r"(?!\s+(morning|afternoon|evening|night|noon|midnight))",
    re.IGNORECASE
)

DEFAULT_TIMEZONE = "America/New_York"

