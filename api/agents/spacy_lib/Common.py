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
_GENERIC_UNIT_WORDS = {
    "second", "seconds",
    "minute", "minutes",
    "hour", "hours",
    "day", "days",
    "week", "weeks",
    "month", "months",
    "year", "years",
}

_NUMBER_WORD_RE = re.compile(
    r"^(a|an|one|two|three|four|five|six|seven|eight|nine|ten|\d+)$", re.IGNORECASE
)
 
_CORRECTION_MARKERS = [
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
_DATE_ANCHOR_PHRASES = [
    "week of", "weeks of",
    "due by", "due on", "due before",
    "before", "after", "since", "until", "from",
    "by", "on",
]
 
_DATE_SLASH_RE = re.compile(
    r"\b(1[0-2]|0?[1-9])/(3[01]|[12]\d|0?[1-9])(?:/\d{2,4})?\b"
)

_DATE_WORD_RE = re.compile(
    r"\b(today|tomorrow|tonight|yesterday|monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b", re.IGNORECASE
)

_DAYPART_TIMES = {
    "morning": (9, 0), "afternoon": (15, 0), "after lunch": (14, 0),
    "evening": (18, 0), "night": (21, 0), "noon": (12, 0), "midnight": (0, 0),
}

_WEEKDAY_RE = re.compile(
    r"\b(?:(this|next|coming)\s+)?"
    r"(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b",
    re.IGNORECASE
)

_WEEKDAY_QUALIFIED_DAYPART_RE = re.compile(
    r"\b(this|next|coming)\s+"
    r"(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\s+"
    r"(morning|afternoon|evening|night)\b",
    re.IGNORECASE
)

_WEEKDAY_DAYPART_RE = re.compile(
    r"(?<!this )(?<!next )(?<!coming )\b"
    r"(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\s+"
    r"(morning|afternoon|evening|night|noon|midnight)\b",
    re.IGNORECASE
)

_WEEKDAY_QUALIFIER_RE = re.compile(
    r"\b(this|next|coming)\s+"
    r"(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b"
    r"(?!\s+(morning|afternoon|evening|night|noon|midnight))",
    re.IGNORECASE
)

DEFAULT_TIMEZONE = "America/New_York"

def _is_number_token(tok):
    return tok.like_num or bool(_NUMBER_WORD_RE.match(tok.text))
 
def _find_correction_markers(raw_text):
    """
    Returns every correction-marker occurrence in raw_text with its character span, e.g. [{"text": "actually", "start_char": 19,
    "end_char": 27}]. Single source of truth shared by CorrectionAnalyzer and EntityAnalyzer so both agree on where
    corrections happen instead of each re-deriving it separately.
    """
    markers = []
    lower = raw_text.lower()
    for marker in _CORRECTION_MARKERS:
        start = 0
        while True:
            idx = lower.find(marker, start)
            if idx == -1:
                break
            markers.append({
                "text": marker,
                "start_char": idx,
                "end_char": idx + len(marker)
            })
            start = idx + len(marker)
    return markers
 
 
def _earliest_marker(markers):
    """
    Given markers already filtered to one sentence, returns the earliest one. Only the first marker in a sentence acts as the
    correction pivot -- a later marker (e.g. "instead" reinforcing an already-corrected value) must not re-flag the corrected value
    itself as superseded.
    """
    return min(markers, key=lambda m: m["start_char"]) if markers else None

def get_timezone(timezone_name=None):
    """
    Return the configured ZoneInfo timezone. All temporal processing in this module should use this timezone.
    """
    return ZoneInfo(timezone_name or DEFAULT_TIMEZONE)

def get_local_now(timezone_name=None):
    """
    Return the current timezone-aware datetime in the configured timezone.
    """
    return datetime.now(get_timezone(timezone_name))

def ensure_timezone(dt, timezone_name=None):
    """
    Ensure a datetime is timezone-aware and expressed in the configured timezone.
    """
    tz = get_timezone(timezone_name)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=tz)
    return dt.astimezone(tz)
 
def _has_date_anchor_before(raw_text, match_start, window=20):
    """
    True if one of _DATE_ANCHOR_PHRASES appears immediately (allowing trailing whitespace) before match_start. Prevents an N/N pattern
    from being treated as a date with no supporting context.
    """
    prefix = raw_text[max(0, match_start - window):match_start].lower().rstrip()
    return any(prefix.endswith(phrase) for phrase in _DATE_ANCHOR_PHRASES)
 
