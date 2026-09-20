import json
import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import spacy
import dateparser

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from spacy_lib.Common import *
from spacy_lib.BaseAnalyzer import BaseAnalyzer


class EntityAnalyzer(BaseAnalyzer):
    """
    Emits every spaCy entity, plus two independent sets of flags:
 
    1. "possibly_superseded" / "correction_marker" -- true when the entity appears before a correction marker (e.g. "actually",
       "wait") in the same sentence, meaning the USER verbally replaced this value. e.g. in "meet at 3pm, actually make it
       4pm", "3pm" is flagged True. Downstream: discard/replace.
 
    2. "possibly_mislabeled" / "suggested_type" -- true when spaCy's NER gave this entity the wrong label (e.g. tagged "10am" as
       QUANTITY, or "7/20" as CARDINAL, instead of TIME/DATE). This is an NER accuracy issue, unrelated to anything the user said.
       Downstream: KEEP the value, just trust suggested_type over the raw "type" field -- do not treat this like a correction.
 
    These two flag-pairs are deliberately separate. A value can be mislabeled without being corrected, or corrected without being
    mislabeled; conflating them into one flag would tell the LLM to discard values (mislabeled) that should actually be kept.
    """
    key = "entities"
 
    def analyze(self, doc, raw_text):
        markers = cmn_find_correction_markers(raw_text)
 
        entities = []
        for ent in doc.ents:
            sent = ent.sent
            same_sent_markers = [
                m for m in markers
                if sent.start_char <= m["start_char"] < sent.end_char
            ]
            pivot = cmn_earliest_marker(same_sent_markers)
            possibly_superseded = pivot is not None and ent.end_char <= pivot["start_char"]
 
            possibly_mislabeled = False
            suggested_type = None
            if ent.label_ not in ("DATE", "TIME"):
                if TemporalAnalyzer._CLOCK_TIME_RE.fullmatch(ent.text.strip()):
                    possibly_mislabeled = True
                    suggested_type = "TIME"
                elif CMN_DATE_SLASH_RE.fullmatch(ent.text.strip()) and cmn_has_date_anchor_before(raw_text, ent.start_char):
                    possibly_mislabeled = True
                    suggested_type = "DATE"
 
            entities.append({
                "text": ent.text,
                "type": ent.label_,
                "possibly_superseded": possibly_superseded,
                "correction_marker": pivot["text"] if possibly_superseded else None,
                "possibly_mislabeled": possibly_mislabeled,
                "suggested_type": suggested_type
            })
        return entities
