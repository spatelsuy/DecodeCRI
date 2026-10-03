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

class ActionAnalyzer(BaseAnalyzer):
    """
    Emits verbs with their subject/objects, plus two additions meant
    to give a downstream LLM real material to populate a "context"
    field with, instead of leaving it null:
 
    - "sentence": the full sentence containing this action, so
      supporting detail outside the verb's direct syntactic children
      (e.g. "with Hari", "which is at 11am") is visible per-action,
      not just buried in the raw transcript.
    - "related_entities": named entities in that same sentence that
      aren't already captured as subject/objects -- concrete
      candidates for what "context" should contain (a name, a
      related meeting, a location, etc).
    """
    key = "actions"
    _IGNORED_VERBS = {"be", "have", "do"}
 
    def analyze(self, doc, raw_text):
        actions = []
        action_id = 1
        for token in doc:
            if token.pos_ != "VERB":
                continue
            lemma = token.lemma_.lower()
            if lemma in self._IGNORED_VERBS:
                continue
 
            # subject extraction
            subject = None
            for child in token.children:
                if child.dep_ in ("nsubj", "nsubjpass"):
                    subject = child.text
 
            # object extraction
            objects = []
            for child in token.children:
                if child.dep_ in ("dobj", "pobj", "attr", "dative"):
                    objects.append(child.text)
 
            sent = token.sent
            already_captured = {(subject or "").lower()} | {o.lower() for o in objects}
            related_entities = [
                {"text": ent.text, "type": ent.label_}
                for ent in doc.ents
                if sent.start_char <= ent.start_char < sent.end_char
                and ent.text.lower() not in already_captured
            ]
 
            actions.append({
                "id": action_id,
                "verb": lemma,
                "text": token.text,
                "subject": subject,
                "objects": objects,
                "sentence": sent.text.strip(),
                "related_entities": related_entities
            })
            action_id += 1
        return actions
 
 
