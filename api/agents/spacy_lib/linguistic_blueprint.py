# ==========================================================
# GENERIC EVIDENCE BLUEPRINT GENERATOR
# ==========================================================
# INSTALL:
# pip install spacy dateparser
# python -m spacy download en_core_web_sm
# ==========================================================
import sys
import os
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
from spacy_lib.TypoAnalyzer import TypoAnalyzer
from spacy_lib.EntityAnalyzer import EntityAnalyzer
from spacy_lib.CorrectionAnalyzer import CorrectionAnalyzer
from spacy_lib.RelationshipAnalyzer import RelationshipAnalyzer
from spacy_lib.TemporalAnalyzer import TemporalAnalyzer
 
# ==========================================================
# LINGUISTIC CONTEXT
# ==========================================================
class LinguisticContext:
    """
    Owns the spaCy pipeline. Loads the model once, and produces one
    parsed Doc per raw_text. All analyzers share that single Doc,
    instead of each analyzer re-running nlp(text) on its own.
    """
 
    def __init__(self, model_name="en_core_web_sm", debug=False):
        self.nlp = spacy.load(model_name)
        self.debug = debug
 
    def parse(self, raw_text):
        doc = self.nlp(raw_text)
        if self.debug:
            self._print_debug(doc)
        return doc
 
    @staticmethod
    def _print_debug(doc):
        print("=" * 100)
        print("FULL TEXT:", repr(doc.text))
        print("=" * 100)
 
        print("\n--- sentences (doc.sents) ---")
        for i, sent in enumerate(doc.sents):
            print(i, repr(sent.text))
 
        print("\n--- tokens (full attributes) ---")
        header = (
            f"{'i':<4}{'text':<12}{'lemma_':<12}{'pos_':<8}{'tag_':<8}{'dep_':<12}"
            f"{'head':<12}{'ent_type_':<10}{'ent_iob_':<10}{'is_stop':<9}"
            f"{'is_alpha':<9}{'is_punct':<9}{'shape_':<10}"
        )
        print(header)
        print("-" * len(header))
        for tok in doc:
            print(
                f"{tok.i:<4}{tok.text:<12}{tok.lemma_:<12}{tok.pos_:<8}{tok.tag_:<8}"
                f"{tok.dep_:<12}{tok.head.text:<12}{tok.ent_type_:<10}{tok.ent_iob_:<10}"
                f"{str(tok.is_stop):<9}{str(tok.is_alpha):<9}{str(tok.is_punct):<9}{tok.shape_:<10}"
            )
 
        print("\n--- noun chunks (doc.noun_chunks) ---")
        for chunk in doc.noun_chunks:
            print(repr(chunk.text), "-> root:", repr(chunk.root.text))
 
        print("\n--- named entities (doc.ents) ---")
        for ent in doc.ents:
            prev = doc[ent.start - 1].text if ent.start > 0 else None
            print(f"{ent.text!r:25} label={ent.label_:8} start={ent.start} end={ent.end} prev_token={prev!r}")
        print("=" * 100 + "\n")


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
 
 
# MAIN BLUEPRINT GENERATOR
def _default_analyzers(base_date, timezone_name=DEFAULT_TIMEZONE):
    return [
        TemporalAnalyzer(
            base_date=base_date,
            timezone_name=timezone_name
        ),
        ActionAnalyzer(),
        RelationshipAnalyzer(),
        CorrectionAnalyzer(),
        TypoAnalyzer(),
        EntityAnalyzer(),
    ]
 
def generate_blueprint(raw_text, context=None, analyzers=None, base_date=None, timezone_name=DEFAULT_TIMEZONE):
    print("GENERATING BLUEPRINT CALLED " + timezone_name)
    local_tz = cmn_get_timezone(timezone_name)
    if base_date is None:
        base_date = datetime.now(local_tz).replace(microsecond=0)
    else:
        base_date = cmn_ensure_timezone(base_date, timezone_name)

    context = context or LinguisticContext(debug=False)
    analyzers = (
        analyzers
        if analyzers is not None
        else _default_analyzers(base_date, timezone_name)
    )
    doc = context.parse(raw_text)
    evidence = {}
    for analyzer in analyzers:
        evidence[analyzer.key] = analyzer.analyze(doc, raw_text)
        
    print("Analyzed ALL")
    return {
        "user_speech_transcript": raw_text, "language": "en", "timezone": timezone_name, "current_date": base_date.isoformat(), "evidence": evidence
    }
