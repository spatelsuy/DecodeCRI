# ==========================================================
# GENERIC EVIDENCE BLUEPRINT GENERATOR
# ==========================================================
# INSTALL:
# pip install spacy dateparser
# python -m spacy download en_core_web_sm
# ==========================================================
import json
import re
from datetime import datetime
import spacy
import dateparser

# ==========================================================
# CONFIG
# ==========================================================
# Bare unit words (no digit attached) that spaCy/dateparser often
# mislabel as DATE/TIME even when they're just ordinary nouns
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

def _is_number_token(tok):
    return tok.like_num or bool(_NUMBER_WORD_RE.match(tok.text))


# LINGUISTIC CONTEXT
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
        print("DEBUG = ", self.debug)
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


# ==========================================================
# ANALYZER INTERFACE
# ==========================================================
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

class TemporalAnalyzer(BaseAnalyzer):
    """
    Uses spaCy's DATE/TIME entity spans (reliable boundaries) as
    candidates, then resolves each span individually with
    dateparser.parse. This avoids the free-form phrase-boundary
    bugs in dateparser.search_dates, which can slurp in unrelated
    words (e.g. "at 11am after the") and misread them as dates.
    """
    key = "temporal_entities"

    def __init__(self, base_date=None):
        # Resolved once per analyzer instance. generate_blueprint()
        # always passes the current call's timestamp explicitly, so
        # this fallback only matters if the analyzer is used standalone.
        self.base_date = base_date or datetime.now()

    def analyze(self, doc, raw_text):
        temporal_entities = []
        seen = set()
        for ent in doc.ents:
            if ent.label_ not in ("DATE", "TIME"):
                continue

            raw = ent.text.strip()
            lower = raw.lower()

            # Reject bare unit words ("minutes", "days", ...) unless a
            # number actually precedes them, e.g. "30 minutes" is fine
            # but "meeting minutes" is not a duration at all.
            if lower in _GENERIC_UNIT_WORDS:
                prev_tok = doc[ent.start - 1] if ent.start > 0 else None
                if prev_tok is None or not _is_number_token(prev_tok):
                    continue

            dt = dateparser.parse(
                raw,
                settings={
                    "RELATIVE_BASE": self.base_date,
                    "PREFER_DATES_FROM": "future",
                    "RETURN_AS_TIMEZONE_AWARE": False,
                }
            )
            if dt is None:
                continue

            key = (lower, dt.isoformat())
            if key in seen:
                continue
            seen.add(key)
            temporal_entities.append({
                "text": raw,
                "resolved_datetime": dt.isoformat()
            })
        return temporal_entities


class ActionAnalyzer(BaseAnalyzer):
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

            actions.append({
                "id": action_id,
                "verb": lemma,
                "text": token.text,
                "subject": subject,
                "objects": objects
            })
            action_id += 1
        return actions


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


class CorrectionAnalyzer(BaseAnalyzer):
    key = "correction_signals"
    _MARKERS = [
        "no no",
        "actually",
        "instead",
        "wait",
        "correction",
        "i mean"
    ]

    def analyze(self, doc, raw_text):
        found = []
        lower = raw_text.lower()
        for marker in self._MARKERS:
            if marker in lower:
                found.append(marker)
        return found


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


class EntityAnalyzer(BaseAnalyzer):
    key = "entities"

    def analyze(self, doc, raw_text):
        entities = []
        for ent in doc.ents:
            entities.append({
                "text": ent.text,
                "type": ent.label_
            })
        return entities


# MAIN BLUEPRINT GENERATOR
def _default_analyzers(base_date):
    return [
        TemporalAnalyzer(base_date),
        ActionAnalyzer(),
        RelationshipAnalyzer(),
        CorrectionAnalyzer(),
        TypoAnalyzer(),
        EntityAnalyzer(),
    ]



def generate_blueprint(raw_text, context=None, analyzers=None, base_date=None):
    """
    context: a LinguisticContext instance (created if not supplied).
    analyzers: list of BaseAnalyzer instances (defaults to all six
    built-in analyzers). Pass a custom list to run a subset, or a
    longer list to add new analyzers without touching this function.
    base_date: the "current date" used both as the relative-date
    anchor for TemporalAnalyzer and as the "current_date" field in
    the returned blueprint. Defaults to datetime.now(), resolved
    fresh on every call rather than fixed at import time.
    """
    print("GENERTING BLUEPRINT CALLED")
    context = context or LinguisticContext(debug=False)
    base_date = base_date or datetime.now()
    analyzers = analyzers if analyzers is not None else _default_analyzers(base_date)

    #get doc object from spaCy
    doc = context.parse(raw_text)

    evidence = {}
    for analyzer in analyzers:
        evidence[analyzer.key] = analyzer.analyze(doc, raw_text)

    return {
        "raw_text": raw_text,
        "language": "en",
        "current_date": base_date.isoformat(),
        "evidence": evidence
    }
