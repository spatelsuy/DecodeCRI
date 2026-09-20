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

class CorrectionAnalyzer(BaseAnalyzer):
    """
    Returns every correction marker with its character span, e.g.
    "actually" at [19, 27), instead of a bare list of marker strings.
    The span lets EntityAnalyzer (and, if extended later,
    TemporalAnalyzer/ActionAnalyzer) determine which specific items
    a correction applies to, rather than just knowing a correction
    happened somewhere in the text.
    """
    key = "correction_signals"
 
    def analyze(self, doc, raw_text):
        return cmn_find_correction_markers(raw_text)
		
