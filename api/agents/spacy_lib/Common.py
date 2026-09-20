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

# Matches clock times like "9am", "10 pm", "11:30am", "9 a.m." — used both to recover entities spaCy's NER mislabels, and to
# re-clip NER spans that swallow adjacent non-time words. Hour is constrained to 1-12 (valid 12-hour clock range) and minutes to
# 00-59, so invalid strings like "13am" or "3:65am" (which the unconstrained \d{1,2} version used to match) are correctly
# rejected rather than passed through to dateparser.
CMN_CLOCK_TIME_RE = re.compile(
    r"\b(1[0-2]|[1-9])(?::([0-5]\d))?\s?(a\.?m\.?|p\.?m\.?)\b", re.IGNORECASE
)

DEFAULT_TIMEZONE = "America/New_York"



def cmn_is_number_token(tok):
    return tok.like_num or bool(CMN_NUMBER_WORD_RE.match(tok.text))
 
def cmn_find_correction_markers(raw_text):
    """
    Returns every correction-marker occurrence in raw_text with its character span, e.g. [{"text": "actually", "start_char": 19,
    "end_char": 27}]. Single source of truth shared by CorrectionAnalyzer and EntityAnalyzer so both agree on where
    corrections happen instead of each re-deriving it separately.
    """
    markers = []
    lower = raw_text.lower()
    for marker in CMN_CORRECTION_MARKERS:
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
 
 
def cmn_earliest_marker(markers):
    """
    Given markers already filtered to one sentence, returns the earliest one. Only the first marker in a sentence acts as the
    correction pivot -- a later marker (e.g. "instead" reinforcing an already-corrected value) must not re-flag the corrected value
    itself as superseded.
    """
    return min(markers, key=lambda m: m["start_char"]) if markers else None

def cmn_get_timezone(timezone_name=None):
    """
    Return the configured ZoneInfo timezone. All temporal processing in this module should use this timezone.
    """
    return ZoneInfo(timezone_name or DEFAULT_TIMEZONE)

def cmn_get_local_now(timezone_name=None):
    """
    Return the current timezone-aware datetime in the configured timezone.
    """
    return datetime.now(cmn_get_timezone(timezone_name))

def cmn_ensure_timezone(dt, timezone_name=None):
    """
    Ensure a datetime is timezone-aware and expressed in the configured timezone.
    """
    tz = cmn_get_timezone(timezone_name)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=tz)
    return dt.astimezone(tz)
 
def cmn_has_date_anchor_before(raw_text, match_start, window=20):
    """
    True if one of CMN_DATE_ANCHOR_PHRASES appears immediately (allowing trailing whitespace) before match_start. Prevents an N/N pattern
    from being treated as a date with no supporting context.
    """
    prefix = raw_text[max(0, match_start - window):match_start].lower().rstrip()
    return any(prefix.endswith(phrase) for phrase in CMN_DATE_ANCHOR_PHRASES)
 


