import sys
import os

import json
import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import spacy
import dateparser


from Common import *
from BaseAnalyzer import BaseAnalyzer

class RelationshipAnalyzer(BaseAnalyzer):
    key = "relationship_hints"
    _PATTERNS = {
        "AFTER": ["after", "once done"],
        "BEFORE": ["before", "prior to"],
    }
 
    def analyze(self, doc, raw_text):
        hints = []
        lower = raw_text.lower()
        for relation, patterns in self._PATTERNS.items():
            for p in patterns:
                if p in lower:
                    hints.append({
                        "type": relation,
                        "text": p
                    })
        return hints
