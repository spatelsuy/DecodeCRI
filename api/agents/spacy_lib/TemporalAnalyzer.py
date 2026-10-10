import sys
import os

import json
import re
from datetime import datetime, date, time, timedelta
from zoneinfo import ZoneInfo
import spacy
import dateparser

from Common import *
from BaseAnalyzer import BaseAnalyzer

# NOTE: the (?:...) grouping here is load-bearing. Without it, every
# pattern that splices WEEKDAYS into a larger f-string pattern breaks:
# `|` has lower precedence than concatenation, so e.g.
# rf"\bnext\s+to\s+next\s+{WEEKDAYS}\b" without grouping compiles to
# "\bnext\s+to\s+next\s+Monday|Tuesday|...|Sunday\b" -- seven independent
# alternatives, where only "next to next Monday" actually requires the
# prefix at all. This was previously masked because spaCy's own NER usually
# tagged common phrasings correctly on its own, so the regex fallback's
# brokenness rarely got exercised.
WEEKDAYS = (
    r"(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)"
)

DATE_PATTERNS = [
    r"\bday after tomorrow\b",
    r"\btwo days from now\b",
    r"\btomorrow\b",
    r"\btoday\b",
    r"\byesterday\b",
    r"\bnext week\b",
    r"\bweek after next\b",
    rf"\bnext\s+to\s+next\s+{WEEKDAYS}\b",
    rf"\b(?:this|next|coming|following|last|previous|upcoming)\s+{WEEKDAYS}\b",
    rf"\b{WEEKDAYS}\s+after next\b",
    rf"\b{WEEKDAYS}\b",
]

TIME_PATTERNS = [
    r"\b(?:1[0-2]|0?[1-9])(?::\d{2})?\s*(?:a\.?m\.?|p\.?m\.?)\b",
    r"\b(?:[01]?\d|2[0-3]):\d{2}\b",
    r"\b(?:morning|afternoon|evening|tonight|midday|midnight|noon)\b",
]

DATE_REGEX = re.compile("|".join(DATE_PATTERNS), re.IGNORECASE)
TIME_REGEX = re.compile("|".join(TIME_PATTERNS), re.IGNORECASE)

# A duration is not a scheduled date/time. This prevents expressions such as
# "my eight hours of learning" from being emitted as temporal appointments.
_NUMBER_WORDS = (
    r"zero|one|two|three|four|five|six|seven|eight|nine|ten|"
    r"eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|"
    r"eighteen|nineteen|twenty|a|an|couple of|few"
)
DURATION_RE = re.compile(
    rf"\b(?:\d+|{_NUMBER_WORDS})\s+"
    r"(?:seconds?|minutes?|hours?|days?|weeks?|months?|years?)\b",
    re.IGNORECASE,
)
NEXT_WEEK_RE = re.compile(r"\b(?P<period>next week|week after next)\b", re.IGNORECASE)

_EXPAND_ALLOWED_DEPS = {"det", "amod", "nummod", "compound", "poss", "appos"}

NON_ACTIVITY_VERBS = {
    "be", "have", "do",
    "will", "would", "shall", "should",
    "can", "could", "may", "might",
    "must", "need",
}


# Activity nouns that can represent an action, event, or scheduled activity.
# Keep this list separate from dependency and traversal logic.
EVENT_NOUNS = {
    "meeting",
    "appointment",
    "interview",
    "dinner",
    "lunch",
    "breakfast",
    "call",
    "presentation",
    "discussion",
    "conversation",
    "class",
    "lecture",
    "training",
    "conference",
    "event",
    "party",
    "trip",
    "flight",
    "visit",
    "reservation",
    "consultation",
    "session",
    "demo",
    "workshop",
    "webinar",
    "deadline",
    "celebration",
    "leave", "vacation", "holiday", "off",  # "on leave", "day off", etc.
}

PCOMP_ACTIVITY_PREPS = {"for"}
WEEKDAY_INDEX = {
    "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
    "friday": 4, "saturday": 5, "sunday": 6,
}
SKIP_MODIFIERS = {"next"}
FORWARD_SKIP_IF_TODAY = {"coming", "upcoming", "following"}
PAST_MODIFIERS = {"last", "previous"}
RECURRING_MARKERS = {
    "every", "each", "alternate", "monthly", "weekly", "daily",
    "annually", "yearly",
}

# ---- Recurrence (frequency) vocabulary -------------------------------
# Words like "monthly" / "every other week" say HOW OFTEN something
# happens. They are not dates and must not be resolved as dates; they are
# turned into recurrence metadata on the activity instead.
FREQUENCY_WORDS = {
    "daily": ("daily", 1), "weekly": ("weekly", 1), "monthly": ("monthly", 1),
    "quarterly": ("quarterly", 1), "yearly": ("yearly", 1), "annually": ("yearly", 1),
    "biweekly": ("weekly", 2), "fortnightly": ("weekly", 2),
}
UNIT_TO_FREQUENCY = {
    "day": "daily", "week": "weekly", "month": "monthly",
    "quarter": "quarterly", "year": "yearly",
}

# A span consisting ONLY of a frequency marker (no date/time content).
FREQUENCY_ONLY_RE = re.compile(
    r"^\s*(?:"
    r"(?:daily|weekly|monthly|quarterly|yearly|annually|biweekly|fortnightly)"
    r"|(?:every|each)\s+(?:(?:other|alternate|second)\s+)?(?:day|week|month|quarter|year)"
    r")\s*$",
    re.IGNORECASE,
)
EVERY_OTHER_RE = re.compile(
    rf"\bevery\s+(?:other|alternate|second)\s+(?P<unit>day|week|month|year|{WEEKDAYS})\b", re.IGNORECASE
)
EVERY_UNIT_RE = re.compile(
    r"\b(?:every|each)\s+(?P<unit>day|week|month|quarter|year)\b", re.IGNORECASE
)
EVERY_WEEKDAY_RE = re.compile(
    rf"\b(?:every|each)\s+(?P<weekday>{WEEKDAYS})\b", re.IGNORECASE
)
FREQUENCY_WORD_RE = re.compile(
    r"\b(?P<word>daily|weekly|monthly|quarterly|yearly|annually|biweekly|fortnightly)\b", re.IGNORECASE
)

# Regex source for frequency phrases, so recurrence detection does not depend
# on spaCy's NER happening to tag them ("every other week" is not tagged).
RECURRENCE_REGEX = re.compile(
    r"\b(?:daily|weekly|monthly|quarterly|yearly|annually|biweekly|fortnightly)\b"
    r"|\b(?:every|each)\s+(?:(?:other|alternate|second)\s+)?(?:day|week|month|quarter|year)\b",
    re.IGNORECASE,
)

PERIOD_DEFAULTS = {
    "morning": (9, 0),
    "noon": (12, 0),
    "midday": (12, 0),
    "afternoon": (15, 0),
    "evening": (18, 0),
    "night": (20, 0),
    "tonight": (20, 0),
    "midnight": (0, 0),
}

WEEKDAY_RE = re.compile(
    r"\b(?:(?P<modifier>this|next|coming|following|last|previous|upcoming)\s+)?"
    r"(?P<weekday>monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b",
    re.IGNORECASE,
)

# "Skip two occurrences" idioms. Must be checked BEFORE WEEKDAY_RE:
# - "next to next Tuesday" matches WEEKDAY_RE on just its second
#   "next Tuesday" substring, silently dropping "next to" and giving a
#   date one week too early.
# - "Tuesday after next" matches WEEKDAY_RE with modifier=None (the
#   modifier group only looks BEFORE the weekday), so it's misread as a
#   bare weekday (nearest occurrence) instead of two weeks out.
DOUBLE_NEXT_RE = re.compile(
    rf"\bnext\s+to\s+next\s+(?P<weekday>{WEEKDAYS})\b", re.IGNORECASE
)
AFTER_NEXT_RE = re.compile(
    rf"\b(?P<weekday>{WEEKDAYS})\s+after\s+next\b", re.IGNORECASE
)

RELATIVE_DAY_RE = re.compile(
    r"\b(?P<rel>day after tomorrow|two days from now|tomorrow|today|yesterday)\b",
    re.IGNORECASE,
)

CLOCK_TIME_RE = re.compile(
    r"\b(?P<hour>1[0-2]|0?[1-9])(?::(?P<minute>\d{2}))?\s*(?P<meridiem>a\.?m\.?|p\.?m\.?)\b",
    re.IGNORECASE,
)


PERIOD_RE = re.compile(
    r"\b(morning|noon|midday|afternoon|evening|night|tonight|midnight)\b",
    re.IGNORECASE,
)

class TemporalAnalyzer(BaseAnalyzer):
  key = "temporal_entities"
  def __init__(self, base_date=None, timezone_name=DEFAULT_TIMEZONE):
    self.timezone_name = timezone_name
    self.local_tz = cmn_get_timezone(timezone_name)   
    if base_date is None:
      self.base_date = datetime.now(self.local_tz)
    else:
      self.base_date = cmn_ensure_timezone(base_date, timezone_name)

  def expand_span_by_dependency(self, doc, start_char, end_char):
    span_tokens = [
        t for t in doc
        if t.idx < end_char and t.idx + len(t.text) > start_char
    ]
    if not span_tokens:
        return None

    span_idxs = {t.i for t in span_tokens}
    extra = [
        child
        for t in span_tokens
        for child in t.children
        if child.dep_ in _EXPAND_ALLOWED_DEPS and child.i not in span_idxs
    ]

    all_tokens = sorted(set(span_tokens + extra), key=lambda t: t.i)

    new_start = all_tokens[0].idx
    new_end = all_tokens[-1].idx + len(all_tokens[-1].text)
    text = doc.text[new_start:new_end]   # original characters, not re-joined tokens
    return text, new_start, new_end

  def tokens_overlapping_span(self, doc, start_char, end_char):
    return [
        token for token in doc
        if token.idx < end_char
        and token.idx + len(token) > start_char
    ]

  def dependency_path(self, token):
    path = [token]
    current = token

    while current.head != current:
        current = current.head
        path.append(current)

    return path

  def ancestor_chain(self, token):
    path = []
    current = token
    visited = set()

    while current.i not in visited:
        visited.add(current.i)
        path.append(current)

        if current.head == current:
            break

        current = current.head
    return path

  def deeper_action_candidates(self, verb_token, depth=1, visited=None):
    if visited is None:
        visited = set()

    results = []
    for child in verb_token.children:
        if child.i in visited:
            continue

        if child.dep_ == "xcomp" and child.pos_ == "VERB":
            visited.add(child.i)
            results.append((child, depth))
            results.extend(self.deeper_action_candidates(child, depth + 1, visited))

        elif child.dep_ == "prep" and child.lemma_.lower() in PCOMP_ACTIVITY_PREPS:
            for grandchild in child.children:
                if grandchild.dep_ == "pcomp" and grandchild.pos_ == "VERB" and grandchild.i not in visited:
                    visited.add(grandchild.i)
                    results.append((grandchild, depth))
                    results.extend(self.deeper_action_candidates(grandchild, depth + 1, visited))

    return results

  def activity_label(self, activity):
    """
    Build a basic label from the activity verb and its direct
    object, when available.
    """
    object_tokens = []

    for child in activity.children:
        if child.dep_ in {"dobj", "obj"}:
            # Include the noun phrase but avoid nested verbs.
            object_tokens.extend(
                t for t in child.subtree
                if t.pos_ not in {"VERB", "AUX"}
            )

    object_tokens = sorted(set(object_tokens), key=lambda t: t.i)

    if object_tokens:
        object_text = " ".join(t.text for t in object_tokens)
        return f"{activity.text} {object_text}"

    return activity.text


  def get_ancestor_distances(self, token):
    """
    Return a dictionary mapping each ancestor token to its distance
    from the supplied token.
    The token itself is included at distance 0.
    """
    distances = {}
    current = token
    distance = 0

    while current.i not in distances:
        distances[current.i] = (current, distance)
        if current.head == current:
            break
        current = current.head
        distance += 1
    return distances
  

  def _resolve_weekday_date(self, reference_date, weekday_name, modifier):
    target_idx = WEEKDAY_INDEX[weekday_name.lower()]
    today_idx = reference_date.weekday()
    diff = (target_idx - today_idx) % 7
    modifier = (modifier or "").lower()

    if modifier in PAST_MODIFIERS:
        diff_back = (today_idx - target_idx) % 7
        if diff_back == 0:
            diff_back = 7
        return reference_date - timedelta(days=diff_back)

    if modifier == "double_next":
        # "next to next <weekday>" / "<weekday> after next": skip TWO
        # occurrences, not one.
        if diff == 0:
            diff = 7
        return reference_date + timedelta(days=diff + 14)      

    if modifier in SKIP_MODIFIERS:
        if diff == 0:
            diff = 7
        return reference_date + timedelta(days=diff + 7)

    if modifier in FORWARD_SKIP_IF_TODAY and diff == 0:
        diff = 7      
    
    # Plain weekday, or this/coming/upcoming/following.
    return reference_date + timedelta(days=diff)

  def _find_weekday_match(self, text):
    """
    Checks the 'skip two occurrences' idioms first -- otherwise they'd be
    swallowed or misread by the plain single-modifier WEEKDAY_RE (see the
    comment above DOUBLE_NEXT_RE/AFTER_NEXT_RE). Returns a
    (weekday_name, modifier) tuple, or None if nothing matched.
    """
    m = DOUBLE_NEXT_RE.search(text)
    if m:
        return m.group("weekday"), "double_next"
 
    m = AFTER_NEXT_RE.search(text)
    if m:
        return m.group("weekday"), "double_next"
 
    m = WEEKDAY_RE.search(text)
    if m:
        return m.group("weekday"), m.group("modifier")
 
    return None


  def _resolve_time_of_day(self, text):
    match = CLOCK_TIME_RE.search(text)
    if match:
        hour = int(match.group("hour"))
        minute = int(match.group("minute") or 0)
        meridiem = match.group("meridiem").lower().replace(".", "")
        if meridiem == "pm" and hour != 12:
            hour += 12
        if meridiem == "am" and hour == 12:
            hour = 0
        return hour, minute

    match = PERIOD_RE.search(text)
    if match:
        return PERIOD_DEFAULTS[match.group(1).lower()]

    return None


  def resolve_combined_temporal(self, combined_text, reference_dt):
    lowered = combined_text.lower()
    reference_date = reference_dt.date()

    is_recurring = any(
        re.search(rf"\b{re.escape(marker)}\b", lowered) for marker in RECURRING_MARKERS
    )

    target_date = None

    # Resolve week-level expressions to the Monday that starts the named week.
    # For "next week", this means the next Monday after the current week.
    week_match = NEXT_WEEK_RE.search(lowered)
    rel_match = RELATIVE_DAY_RE.search(lowered)
    weekday_match = self._find_weekday_match(combined_text)

    if week_match:
        days_until_monday = (0 - reference_date.weekday()) % 7
        if days_until_monday == 0:
            days_until_monday = 7
        target_date = reference_date + timedelta(days=days_until_monday)
        if week_match.group("period").lower() == "week after next":
            target_date += timedelta(days=7)
    elif rel_match:
        rel = rel_match.group("rel").lower()
        offset = {
            "today": 0, "tomorrow": 1, "day after tomorrow": 2,
            "two days from now": 2, "yesterday": -1,
        }[rel]
        target_date = reference_date + timedelta(days=offset)
    elif weekday_match:
        weekday_name, modifier = weekday_match
        target_date = self._resolve_weekday_date(
            reference_date, weekday_name, modifier
        )

    time_of_day = self._resolve_time_of_day(combined_text)

    if target_date is None and time_of_day is None:
        return None, is_recurring, "unresolved"

    if target_date is None:
        target_date = reference_date

    hour, minute = time_of_day if time_of_day else (0, 0)
    try:
        resolved_dt = datetime.combine(target_date, time(hour, minute), tzinfo=ZoneInfo(self.timezone_name))
    except Exception as e:
        print(f"Unexpected error: {e}")
    return resolved_dt.isoformat(), is_recurring, "explicit"


  def debug_temporal_paths(self, doc, temporal_spans):
    for span in temporal_spans:
        #print(f"\nTemporal span: {span['text']!r}")
        start = span["start_char"]
        end = span["end_char"]

        for token in doc:
            # Check whether this token overlaps the temporal span.
            token_start = token.idx
            token_end = token.idx + len(token.text)
            if token_end <= start or token_start >= end:
                continue
            path = []
            current = token
            visited = set()
            while current.i not in visited:
                visited.add(current.i)
                path.append(
                    f"{current.text}({current.pos_}, {current.dep_})"
                )
                if current.head == current:
                    break
                current = current.head
              
            #print(f"  Token: {token.text!r}")
            #print("  Ancestor path:", " -> ".join(path))
  
  def find_activity_candidates(self, doc):
    candidates = []
    candidate_ids = set()

    # ------------------------------------------------------
    # Pass 1: Find meaningful verb candidates
    # ------------------------------------------------------
    for token in doc:

        if token.pos_ != "VERB":
            continue

        if token.lemma_.lower() in NON_ACTIVITY_VERBS:
            continue

        if token.dep_ in {"aux", "auxpass"}:
            continue

        if token.i not in candidate_ids:
            candidates.append(token)
            candidate_ids.add(token.i)

    # ------------------------------------------------------
    # Pass 2: Find activity nouns connected to a verb
    # ------------------------------------------------------
    for token in doc:

        if token.pos_ not in {"NOUN", "PROPN"}:
            continue

        if token.lemma_.lower() not in EVENT_NOUNS:
            continue

        # Walk up the dependency tree to check whether this noun
        # is connected to a verb. Include helper verbs in this check.
        ancestor = token.head
        connected_to_verb = False

        while ancestor != token:
            if ancestor.pos_ in {"VERB", "AUX"}:
                connected_to_verb = True
                break
            if ancestor.head == ancestor:
                break
            ancestor = ancestor.head
        if connected_to_verb and token.i not in candidate_ids:
            candidates.append(token)
            candidate_ids.add(token.i)

    # Keep candidates in their original sentence order.
    candidates.sort(key=lambda t: t.i)

    #print("Activity candidates:")
    #for candidate in candidates:
    #    print(
    #        f"Text: {candidate.text!r}, "
    #        f"Lemma: {candidate.lemma_!r}, "
    #        f"POS: {candidate.pos_}, "
    #        f"Dependency: {candidate.dep_}, "
    #        f"Head: {candidate.head.text!r}"
    #    )
    return candidates


  
  def find_temporal_spans(self, doc):
    found = []
    for ent in doc.ents:
        if ent.label_ in {"DATE", "TIME"}:
            # Ignore duration entities such as "eight hours". Dependency
            # expansion below may add words like "my", so we filter again
            # after expansion as well.
            if DURATION_RE.search(ent.text):
                continue
            found.append({
                "text": ent.text,
                "start_char": ent.start_char,
                "end_char": ent.end_char,
                "source": "spacy_entity",
                "label": ent.label_,
            })

    for label, regex in [
        ("DATE", DATE_REGEX),
        ("TIME", TIME_REGEX),
    ]:
        for match in regex.finditer(doc.text):
            found.append({
                "text": match.group(),
                "start_char": match.start(),
                "end_char": match.end(),
                "source": "regex",
                "label": label,
            })

    for match in RECURRENCE_REGEX.finditer(doc.text):
        found.append({
            "text": match.group(),
            "start_char": match.start(),
            "end_char": match.end(),
            "source": "regex",
            "label": "RECURRENCE",
        })

    expanded = []
    for item in found:
        result = self.expand_span_by_dependency(doc, item["start_char"], item["end_char"])
        if result is None:
            expanded.append(item)
            continue
        text, start_char, end_char = result
        expanded.append({**item, "text": text, "start_char": start_char, "end_char": end_char})

    # Sort so that, among overlapping spans, the LONGEST one wins -- not
    # whichever source happens to come first. spaCy's NER sometimes tags
    # only part of a phrase (e.g. "Tuesday" alone inside "Tuesday after
    # next"), while the regex fallback captures the complete idiom; if
    # both start at the same character, preferring spacy_entity
    # unconditionally would silently keep the shorter, wrong span.
    # Only once length is equal do we prefer spacy_entity as a tiebreak.
    expanded.sort(key=lambda x: (x["start_char"], -(x["end_char"] - x["start_char"]), x["source"] != "spacy_entity"))

    unique = []
    for item in expanded:
        overlaps_existing = any(
            item["start_char"] < kept["end_char"]
            and item["end_char"] > kept["start_char"]
            for kept in unique
        )
        if not overlaps_existing:
            unique.append(item)

    # Remove duration phrases after dependency expansion too (for example,
    # an entity "eight hours" may expand to "my eight hours").
    unique = [item for item in unique if not DURATION_RE.search(item["text"])]

    #print("temporal span")
    #print(unique)
    for item in unique:
        if FREQUENCY_ONLY_RE.match(item["text"]):
            item["label"] = "RECURRENCE"

    return sorted(unique, key=lambda x: x["start_char"])


  def find_activity_from_dependency(self, token, activity_candidates):
    if not activity_candidates:
        return None

    ancestor_path = self.ancestor_chain(token)
    candidate_ids = {c.i for c in activity_candidates}

    # ------------------------------------------------------
    # Pass 1: Walk ancestors closest-first. At each ancestor, prefer
    # a more specific action reachable from THAT ancestor alone (its
    # own xcomp / prep("for")->pcomp children) over the ancestor
    # itself; otherwise, if the ancestor itself is a candidate, take
    # it. Stop at the first ancestor that produces any match.
    #
    # This must be done one ancestor at a time, not aggregated across
    # the whole chain at once: aggregating let a distant, unrelated
    # xcomp hanging off the sentence's ROOT verb (e.g. "need -> buy")
    # win for every temporal expression in a multi-clause sentence,
    # even when a much closer, correct ancestor (e.g. "taking") was
    # already a valid direct match.
    # ------------------------------------------------------
    for ancestor in ancestor_path:
        extended = [
            (candidate, depth) for candidate, depth in self.deeper_action_candidates(ancestor)
            if candidate.i in candidate_ids
        ]
        if extended:
            extended.sort(key=lambda pair: -pair[1])  # deepest/most specific first
            return extended[0][0]

        if ancestor.i in candidate_ids:
            return ancestor

    # ------------------------------------------------------
    # Pass 2: Shared governing verb fallback
    # ------------------------------------------------------
    temporal_ancestors = self.get_ancestor_distances(token)

    fallback_matches = []

    for candidate in activity_candidates:
        if candidate.pos_ not in {"NOUN", "PROPN"}:
            continue

        candidate_ancestors = self.get_ancestor_distances(candidate)

        # Find shared ancestors between the temporal token and
        # the candidate activity noun.
        shared_ancestors = (
            set(temporal_ancestors.keys())
            & set(candidate_ancestors.keys())
        )

        for ancestor_id in shared_ancestors:
            shared_ancestor, temporal_distance = temporal_ancestors[ancestor_id]
            _, candidate_distance = candidate_ancestors[ancestor_id]

            # Require a verb to act as the shared governing point.
            if shared_ancestor.pos_ not in {"VERB", "AUX"}:
                continue

            directly_attached = candidate.head.i == shared_ancestor.i
            prep_attached = (
                candidate.head.dep_ == "prep"
                and candidate.head.head.i == shared_ancestor.i
            )
            if not (directly_attached or prep_attached):
                continue
            
            fallback_matches.append((candidate, temporal_distance + candidate_distance))

    # Deduplicate candidates in case more than one shared ancestor
    # produced a match.
    unique_matches = {}

    for candidate, distance in fallback_matches:
        existing = unique_matches.get(candidate.i)
        if existing is None or distance < existing[1]:
            unique_matches[candidate.i] = (candidate, distance)

    if len(unique_matches) == 1:
        return next(iter(unique_matches.values()))[0]

    if len(unique_matches) > 1:
        # Do not guess when several activity nouns qualify.
        # A later context-building stage can resolve ambiguity.
        return None

    return None

  
  
  def extract_temporal_activities(self, doc, text):
    temporal_spans = self.find_temporal_spans(doc)
    activities = self.find_activity_candidates(doc)
    activities = [
        a for a in activities
        if not any(
            s["start_char"] <= a.idx and a.idx + len(a.text) <= s["end_char"]
            for s in temporal_spans
        )
    ]
    self.debug_temporal_paths(doc, temporal_spans)
    # One result bucket per activity token.
    results = {}
    for activity in activities:
        results[activity.i] = {
            "activity": self.activity_label(activity),
            "activity_token": activity.text,
            "activity_token_index": activity.i,
            "temporal_expressions": [],
        }

    # Associate each temporal expression with an activity using
    # the dependency path from its token(s).
    for span in temporal_spans:
        span_tokens = self.tokens_overlapping_span(
            doc, span["start_char"], span["end_char"],
        )
        associated_activity = None
        # A span may contain multiple tokens, such as "9pm tomorrow".
        # Check each token and take the first dependency-supported
        # activity found.
        for span_token in span_tokens:
            associated_activity = self.find_activity_from_dependency(
                span_token, activities,
            )

            if associated_activity is not None:
                break

        # Clause-start date safeguard: in speech such as
        # "...buy grocery Tuesday I need to reach office...", a shared
        # dependency ancestor can incorrectly attach Tuesday to "buy".
        # If a DATE span is followed by a new subject + action-intent phrase,
        # attach it to the first activity after that phrase instead.
        if span["label"] == "DATE" and span_tokens:
            span_sentence = span_tokens[0].sent
            following = [
                candidate for candidate in activities
                if candidate.idx >= span["end_char"]
                and candidate.sent.start == span_sentence.start
            ]
            if following:
                following.sort(key=lambda candidate: candidate.idx)
                next_candidate = following[0]
                gap = doc.text[span["end_char"]:next_candidate.idx]
                starts_new_clause = re.search(
                    r"\b(?:I|we|you|he|she|they)\s+"
                    r"(?:need|have|want|plan|will|must|should|can)\b",
                    gap,
                    re.IGNORECASE,
                )
                if starts_new_clause:
                    associated_activity = next_candidate

        expression_result = {
            "text": span["text"],
            "label": span["label"],
            "start_char": span["start_char"],
            "end_char": span["end_char"],
            "source": span["source"],
        }
        
        if associated_activity is None:
            expression_result["association"] = "unresolved"
            expression_result["activity_token"] = None
            print( 
                f"UNRESOLVED temporal expression: "
                f"{span['text']!r}"
            )
            continue

        expression_result["association"] = "dependency_path"
        expression_result["activity_token"] = associated_activity.text

        results[associated_activity.i]["temporal_expressions"].append(
            expression_result
        )

        #print(
        #    f"{span['text']!r} "
        #    f"--> activity={associated_activity.text!r} "
        #    f"(dependency-supported)"
        #)
    # Return only activities that received at least one temporal
    # expression. Keep all their original temporal wording.
    output = []

    for item in results.values():
        if item["temporal_expressions"]:
            item["temporal_expressions"].sort(
                key=lambda x: x["start_char"]
            )
            output.append(item)

    return output

  def parse_recurrence(self, text):
    """
    Extract recurrence metadata from text, or None if there is none.
    Returns {"frequency", "interval", "day_of_week", "marker"}.
    frequency is None when we only know it repeats ("alternate", "each").
    """
    m = EVERY_OTHER_RE.search(text)
    if m:
        unit = m.group("unit").lower()
        if unit in WEEKDAY_INDEX:
            return {"frequency": "weekly", "interval": 2, "day_of_week": unit, "marker": m.group(0)}
        return {"frequency": UNIT_TO_FREQUENCY[unit], "interval": 2, "day_of_week": None, "marker": m.group(0)}

    m = EVERY_UNIT_RE.search(text)
    if m:
        return {"frequency": UNIT_TO_FREQUENCY[m.group("unit").lower()], "interval": 1,
                "day_of_week": None, "marker": m.group(0)}

    m = EVERY_WEEKDAY_RE.search(text)
    if m:
        return {"frequency": "weekly", "interval": 1,
                "day_of_week": m.group("weekday").lower(), "marker": m.group(0)}

    m = FREQUENCY_WORD_RE.search(text)
    if m:
        frequency, interval = FREQUENCY_WORDS[m.group("word").lower()]
        return {"frequency": frequency, "interval": interval, "day_of_week": None, "marker": m.group(0)}

    m = re.search(r"\b(?:every|each|alternate)\b", text, re.IGNORECASE)
    if m:
        return {"frequency": None, "interval": None, "day_of_week": None, "marker": m.group(0)}

    return None

  def build_temporal_entities(self, temporal_activities, reference_dt=None):
    if reference_dt is None:
        # Use the analyzer's configured reference datetime so tests and
        # production runs resolve relative dates consistently.
        reference_dt = self.base_date

    temporal_entities = []

    for item in temporal_activities:
        exprs = item["temporal_expressions"]
        date_exprs = [e for e in exprs if e["label"] != "RECURRENCE"]
        recur_exprs = [e for e in exprs if e["label"] == "RECURRENCE"]

        # Recurrence is read from ALL expressions (so "Every Thursday" and a
        # standalone "monthly" are both seen), but only real date/time text
        # is used to resolve a datetime.
        recurrence = self.parse_recurrence(" ".join(e["text"] for e in exprs))

        if date_exprs:
            combined_text = " ".join(e["text"] for e in date_exprs)
            resolved_datetime, is_recurring, date_source = self.resolve_combined_temporal(
                combined_text, reference_dt
            )
        else:
            # Frequency only ("a monthly review"): recurring, but no anchor date.
            combined_text = " ".join(e["text"] for e in recur_exprs)
            resolved_datetime, is_recurring, date_source = None, True, "recurrence_only"

        temporal_entities.append({
            "text": combined_text,
            "resolved_datetime": resolved_datetime,
            "recurring": bool(is_recurring or recurrence),
            "recurrence": recurrence,
            "date_source": date_source,
            # Kept for traceability back to the activity this came from;
            # drop this key if you only want the fields shown above.
            "activity": item["activity"],
            # Internal metadata used below for controlled date inheritance.
            "_start_char": min(e["start_char"] for e in exprs),
            "_has_calendar_date": any(e["label"] == "DATE" for e in date_exprs),
        })

    # Resolve entities in the order they were spoken, not the order of the
    # activity tokens. A time-only expression inherits the most recent
    # explicit calendar date (e.g. Tuesday -> 8 am -> 4 pm).
    temporal_entities.sort(key=lambda entity: entity["_start_char"])
    inherited_date = None
    for entity in temporal_entities:
        resolved = entity["resolved_datetime"]
        if entity["_has_calendar_date"] and resolved:
            parsed = datetime.fromisoformat(resolved)
            inherited_date = parsed.date()
        elif not entity["_has_calendar_date"] and resolved and inherited_date:
            parsed = datetime.fromisoformat(resolved)
            inherited = datetime.combine(inherited_date, parsed.timetz())
            entity["resolved_datetime"] = inherited.isoformat()
            entity["date_source"] = "inherited"

        entity.pop("_start_char", None)
        entity.pop("_has_calendar_date", None)

    #return {"temporal_entities": temporal_entities}
    return temporal_entities
  

  def analyze(self, doc, raw_text):
    temporal_entities = []
    temporal_activities = self.extract_temporal_activities(doc, raw_text)
    final_output = self.build_temporal_entities(temporal_activities)
    return final_output
