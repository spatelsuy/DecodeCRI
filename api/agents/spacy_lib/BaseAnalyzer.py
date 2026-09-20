import json
import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import spacy
import dateparser

class BaseAnalyzer:
    """
    Common interface every analyzer implements. `key` is the name
    used for this analyzer's output inside the blueprint's
    "evidence" dict. To add a new analyzer: subclass this, set
    `key`, implement `analyze`, and add an instance to
    DEFAULT_ANALYZERS below (or pass a custom list) — nothing
    else has to change.
    """
    key = None
 
    def analyze(self, doc, raw_text):
        raise NotImplementedError
 
