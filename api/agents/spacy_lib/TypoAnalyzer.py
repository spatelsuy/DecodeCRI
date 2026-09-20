import json
import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import spacy
import dateparser

from BaseAnalyzer import BaseAnalyzer

class TypoAnalyzer(BaseAnalyzer):
    key = "possible_typos"
    _TYPO_RULES = {
        "meeitng": "meeting",
        "sent": "send"
    }
 
    def analyze(self, doc, raw_text):
        typos = []
        lower = raw_text.lower()
        for wrong, correct in self._TYPO_RULES.items():
            if wrong in lower:
                typos.append({
                    "original": wrong,
                    "suggestion": correct
                })
        return typos
