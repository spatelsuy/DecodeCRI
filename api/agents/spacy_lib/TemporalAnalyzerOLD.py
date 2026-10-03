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

class TemporalAnalyzerOLD(BaseAnalyzer):
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

    def _process_ner_temporal_spans(self, doc, seen: set, temporal_entities: list, ner_char_spans: list):
        for ent in doc.ents:
            if ent.label_ not in ("DATE", "TIME"):
                continue
             
            raw = ent.text.strip()
            lower = raw.lower()
 
            # Reject bare unit words ("minutes", "days", ...) unless a number actually precedes them, e.g. "30 minutes" is fine
            # but "meeting minutes" is not a duration at all.
            if lower in CMN_GENERIC_UNIT_WORDS:
                prev_tok = doc[ent.start - 1] if ent.start > 0 else None
                if prev_tok is None or not cmn_is_number_token(prev_tok):
                    continue
 
            # If this is a TIME entity but NER over-extended the span to include non-time words (e.g. "9am PST Hari"), re-clip
            # it down to just the clock-time pattern.
            clock_match = CMN_CLOCK_TIME_RE.search(raw)
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
 
    def analyze(self, doc, raw_text):
        temporal_entities = []
        seen = set()
        ner_char_spans = []  # (start_char, end_char) already consumed by NER pass
        print("Good")
        self._process_ner_temporal_spans(doc, seen, temporal_entities, ner_char_spans)
        print("Very good")
        # Regex fallback: recover clock-time expressions NER missed
        # entirely (mislabeled as something other than DATE/TIME).
        for m in CMN_CLOCK_TIME_RE.finditer(raw_text):
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
