import json
import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import spacy
import dateparser


_GENERIC_UNIT_WORDS = {
    "second", "seconds",
    "minute", "minutes",
    "hour", "hours",
    "day", "days",
    "week", "weeks",
    "month", "months",
    "year", "years",
}
