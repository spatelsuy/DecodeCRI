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
 
 
class TemporalAnalyzer(BaseAnalyzer):
    """
    Uses spaCy's DATE/TIME entity spans (reliable boundaries) as candidates, then resolves each span individually with
    dateparser.parse. This avoids the free-form phrase-boundary bugs in dateparser.search_dates, which can slurp in unrelated
    words (e.g. "at 11am after the") and misread them as dates.
 
    spaCy's statistical NER occasionally mislabels clear clock-time expressions as something other than DATE/TIME (observed: "10am"
    tagged QUANTITY) which silently drops them from the DATE/TIME-only scan above. A regex fallback recovers any clock-time pattern in
    the raw text that NER missed. It also re-clips TIME spans that NER over-extended into adjacent, unrelated words (observed:
    "9am PST Hari" merged a person's name into the time span).
    """
    key = "temporal_entities"
 
    # Matches clock times like "9am", "10 pm", "11:30am", "9 a.m." — used both to recover entities spaCy's NER mislabels, and to
    # re-clip NER spans that swallow adjacent non-time words. Hour is constrained to 1-12 (valid 12-hour clock range) and minutes to
    # 00-59, so invalid strings like "13am" or "3:65am" (which the unconstrained \d{1,2} version used to match) are correctly
    # rejected rather than passed through to dateparser.
    _CLOCK_TIME_RE = re.compile(
        r"\b(1[0-2]|[1-9])(?::([0-5]\d))?\s?(a\.?m\.?|p\.?m\.?)\b", re.IGNORECASE
    )
  
    def __init__(self, base_date=None, timezone_name=DEFAULT_TIMEZONE):
       self.timezone_name = timezone_name
       self.local_tz = cmn_get_timezone(timezone_name)   
       if base_date is None:
           self.base_date = datetime.now(self.local_tz)
       else:
           self.base_date = cmn_ensure_timezone(base_date, timezone_name)
     
    def _is_explicit_date_entity(self, raw_text_around_span):
        return bool(CMN_DATE_WORD_RE.search(raw_text_around_span)) or bool(CMN_DATE_SLASH_RE.search(raw_text_around_span))

    def _resolve_weekday(self, weekday, qualifier=None):
        """
        Resolve a weekday relative to base_date.
    
        Rules:
          - this Sunday  -> Sunday of the current week
          - Sunday       -> today if today is Sunday, otherwise next occurrence
          - coming Sunday -> next occurrence, unless today is Sunday
          - next Sunday  -> next week's Sunday
        """
    
        weekdays = {
            "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
            "friday": 4, "saturday": 5, "sunday": 6,
        }
    
        weekday = weekday.lower()
        qualifier = qualifier.lower() if qualifier else None
    
        if weekday not in weekdays:
            return None
    
        target = weekdays[weekday]
        current = self.base_date.weekday()
        days_ahead = (target - current) % 7
    
        if qualifier == "next":
            # "next Sunday" means the following occurrence,
            # never today.
            days_ahead = (target - current) % 7
            if days_ahead == 0:
                days_ahead = 7
    
        elif qualifier == "this":
            # "this Sunday" means the Sunday in the current calendar week.
            days_ahead = target - current
    
            # If the weekday has already passed this week, "this Sunday"
            # should not jump backward into the previous week.
            if days_ahead < 0:
                return None
    
        elif qualifier == "coming":
            # Treat "coming Sunday" as the next occurrence,
            # but today itself is acceptable.
            days_ahead = days_ahead
    
        return self.base_date + timedelta(days=days_ahead)
 
    def _resolve(self, raw):
        return dateparser.parse(
            raw,
            settings={
                "RELATIVE_BASE": self.base_date,
                "PREFER_DATES_FROM": "future",
                "RETURN_AS_TIMEZONE_AWARE": True,
                "TIMEZONE": self.timezone_name,
            }
        )
 
    def _apply_date_inheritance(self, temporal_entities, raw_text):
        print("1")
        # Requires each entry to already carry "_start_char" internally (add this
        # alongside the existing fields in all three append blocks, strip before return)
        try:
            entities_sorted = sorted(temporal_entities, key=lambda e: e["_start_char"])
            current_anchor_date = None  # a date(), not datetime
            print("2")    
            for ent in entities_sorted:
                window = raw_text[max(0, ent["_start_char"]-25):ent["_start_char"]+len(ent["text"])+10]
                is_explicit = self._is_explicit_date_entity(window)
                dt = datetime.fromisoformat(ent["resolved_datetime"])
        
                if is_explicit:
                    current_anchor_date = dt.date()
                    ent["date_source"] = "explicit"
                elif current_anchor_date is not None:
                    # Bare time expression -- keep its time-of-day, but replace the
                    # date with whatever anchor was most recently established,
                    # instead of trusting dateparser's "next occurrence from now" guess.
                    corrected = datetime(current_anchor_date.year, current_anchor_date.month, current_anchor_date.day, dt.hour, dt.minute, dt.second, dt.microsecond, tzinfo=self.local_tz)
                    ent["resolved_datetime"] = corrected.isoformat()
                    ent["date_source"] = "inherited"
                else:
                    ent["date_source"] = "default"  # no anchor seen yet -- today's date may be a real guess, flag it as such
        
            for ent in temporal_entities:
                ent.pop("_start_char", None)

            print("3")
            return temporal_entities
        except Exception as e:
            print("ERROR in _apply_date_inheritance:", repr(e))
            # Clean up internal field even if an error occurs
            for ent in temporal_entities:
                ent.pop("_start_char", None)

            # Return original temporal entities instead of crashing
            return temporal_entities

    def analyze(self, doc, raw_text):
        temporal_entities = []
        seen = set()
        ner_char_spans = []  # (start_char, end_char) already consumed by NER pass
 
        for ent in doc.ents:
            if ent.label_ not in ("DATE", "TIME"):
                continue
 
            raw = ent.text.strip()
            lower = raw.lower()
 
            # Reject bare unit words ("minutes", "days", ...) unless a
            # number actually precedes them, e.g. "30 minutes" is fine
            # but "meeting minutes" is not a duration at all.
            if lower in CMN_GENERIC_UNIT_WORDS:
                prev_tok = doc[ent.start - 1] if ent.start > 0 else None
                if prev_tok is None or not cmn_is_number_token(prev_tok):
                    continue
 
            # If this is a TIME entity but NER over-extended the span
            # to include non-time words (e.g. "9am PST Hari"), re-clip
            # it down to just the clock-time pattern.
            clock_match = self._CLOCK_TIME_RE.search(raw)
            if ent.label_ == "TIME" and clock_match and clock_match.group() != raw:
                raw = clock_match.group()
                lower = raw.lower()
 
            ner_char_spans.append((ent.start_char, ent.end_char))
 
            dt = self._resolve(raw)
            if dt is None:
                continue
 
            dedup_key = (lower, dt.isoformat())
            if dedup_key in seen:
                continue
            seen.add(dedup_key)
            temporal_entities.append({
                "text": raw,
                "resolved_datetime": dt.isoformat(),
                "_start_char": ent.start_char
            })
 
        # Regex fallback: recover clock-time expressions NER missed
        # entirely (mislabeled as something other than DATE/TIME).
        for m in self._CLOCK_TIME_RE.finditer(raw_text):
            span = (m.start(), m.end())
            if any(span[0] < e and s < span[1] for s, e in ner_char_spans):
                continue  # already covered by the NER pass above
 
            raw = m.group()
            lower = raw.lower()
            dt = self._resolve(raw)
            if dt is None:
                continue
 
            dedup_key = (lower, dt.isoformat())
            if dedup_key in seen:
                continue
            seen.add(dedup_key)
            temporal_entities.append({
                "text": raw,
                "resolved_datetime": dt.isoformat(),
                "_start_char": m.start()
            })
 
        # Regex fallback #2: recover slash-format dates (e.g. "7/20",
        # "7/20/2026") that NER mislabeled as CARDINAL. Guarded by a
        # preceding date-anchor phrase ("week of", "due by", "on", ...)
        # so a fraction like "1/2 cup" or a score like "7/20" in an
        # unrelated context is not misread as a date.
        for m in CMN_DATE_SLASH_RE.finditer(raw_text):
            span = (m.start(), m.end())
            if any(span[0] < e and s < span[1] for s, e in ner_char_spans):
                continue  # already covered by an earlier pass
            if not cmn_has_date_anchor_before(raw_text, m.start()):
                continue  # no date context -- likely a fraction/score/ratio
 
            raw = m.group()
            lower = raw.lower()
            dt = self._resolve(raw)
            if dt is None:
                continue
 
            dedup_key = (lower, dt.isoformat())
            if dedup_key in seen:
                continue
            seen.add(dedup_key)
            temporal_entities.append({
                "text": raw,
                "resolved_datetime": dt.isoformat(),
                "_start_char": m.start()
            })

        # Regex fallback #3: qualified weekday + daypart
        # Examples: "this Sunday night", "next Sunday night", "coming Sunday night"
        for m in CMN_WEEKDAY_QUALIFIED_DAYPART_RE.finditer(raw_text):
            raw = m.group()
            lower = raw.lower()
            qualifier, weekday, daypart = lower.split()
            base_dt = self._resolve_weekday(weekday, qualifier)
            if base_dt is None:
                continue
        
            hour, minute = CMN_DAYPART_TIMES[daypart]
            dt = base_dt.replace(hour=hour, minute=minute, second=0, microsecond=0)
        
            temporal_entities.append({
                "text": raw,
                "resolved_datetime": dt.isoformat(),
                "_start_char": m.start()
            })

        # Regex fallback #4: recover weekday + daypart expressions (e.g. "Sunday night")
        for m in CMN_WEEKDAY_DAYPART_RE.finditer(raw_text):
            span = (m.start(), m.end())
            raw = m.group()
            lower = raw.lower()

            # Remove partial NER entities (e.g., "Sunday") covered by this broader match ("Sunday night")
            overlapping_spans = [s for s in ner_char_spans if span[0] < s[1] and s[0] < span[1]]
            if overlapping_spans:
                temporal_entities = [
                    e for e in temporal_entities 
                    if not any(s[0] <= e.get("_start_char", -1) < s[1] for s in overlapping_spans)
                ]

            parts = lower.split()
            
            if len(parts) == 2 and parts[0] in {
                "monday", "tuesday", "wednesday",
                "thursday", "friday", "saturday", "sunday"
            } and parts[1] in CMN_DAYPART_TIMES:
            
                weekday, daypart = parts
            
                # Resolve weekday ourselves.
                base_dt = self._resolve_weekday(weekday)
            
                if base_dt is not None:
                    hour, minute = CMN_DAYPART_TIMES[daypart]
                    dt = base_dt.replace(hour=hour, minute=minute)
                else:
                    dt = None
            
            else:
                dt = self._resolve(raw)

            if dt is None:
                continue

            dedup_key = (lower, dt.isoformat())
            if dedup_key in seen:
                continue
            seen.add(dedup_key)
            temporal_entities.append({
                "text": raw,
                "resolved_datetime": dt.isoformat(),
                "_start_char": m.start()
            })

        # Regex fallback #5: qualified weekdays
        # Examples: "this Sunday", "next Sunday", "coming Sunday"
        for m in CMN_WEEKDAY_QUALIFIER_RE.finditer(raw_text):
            span = (m.start(), m.end())
            raw = m.group()
            lower = raw.lower()
        
            qualifier, weekday = lower.split()
        
            dt = self._resolve_weekday(weekday, qualifier)
        
            if dt is None:
                continue
        
            dedup_key = (lower, dt.isoformat())
            if dedup_key in seen:
                continue
        
            seen.add(dedup_key)
        
            temporal_entities.append({
                "text": raw,
                "resolved_datetime": dt.isoformat(),
                "_start_char": m.start()
            })
     
        temporal_entities = self._apply_date_inheritance(temporal_entities, raw_text)
        return temporal_entities
 
 
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
 
 
class EntityAnalyzer(BaseAnalyzer):
    """
    Emits every spaCy entity, plus two independent sets of flags:
 
    1. "possibly_superseded" / "correction_marker" -- true when the
       entity appears before a correction marker (e.g. "actually",
       "wait") in the same sentence, meaning the USER verbally
       replaced this value. e.g. in "meet at 3pm, actually make it
       4pm", "3pm" is flagged True. Downstream: discard/replace.
 
    2. "possibly_mislabeled" / "suggested_type" -- true when spaCy's
       NER gave this entity the wrong label (e.g. tagged "10am" as
       QUANTITY, or "7/20" as CARDINAL, instead of TIME/DATE). This is
       an NER accuracy issue, unrelated to anything the user said.
       Downstream: KEEP the value, just trust suggested_type over the
       raw "type" field -- do not treat this like a correction.
 
    These two flag-pairs are deliberately separate. A value can be
    mislabeled without being corrected, or corrected without being
    mislabeled; conflating them into one flag would tell the LLM to
    discard values (mislabeled) that should actually be kept.
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

    print("Base Date is setup")
    context = context or LinguisticContext(debug=False)
    analyzers = (
        analyzers
        if analyzers is not None
        else _default_analyzers(base_date, timezone_name)
    )
    print("Analyzer is set")
    doc = context.parse(raw_text)
    print("DOC is set")
    evidence = {}
    for analyzer in analyzers:
        print("KEY = ")
        evidence[analyzer.key] = analyzer.analyze(doc, raw_text)
        
    
    print("Analyzed ALL")
    return {
        "user_speech_transcript": raw_text, "language": "en", "timezone": timezone_name, "current_date": base_date.isoformat(), "evidence": evidence
    }
