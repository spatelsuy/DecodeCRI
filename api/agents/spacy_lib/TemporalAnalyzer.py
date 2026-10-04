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

WEEKDAYS = (
    r"Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday"
)

DATE_PATTERNS = [
    r"\bday after tomorrow\b",
    r"\btwo days from now\b",
    r"\btomorrow\b",
    r"\btoday\b",
    r"\byesterday\b",
    rf"\b(?:this|next|coming|following|last|previous|upcoming)\s+{WEEKDAYS}\b",
    rf"\b{WEEKDAYS}\s+after next\b",
    rf"\b{WEEKDAYS}\b",
]

TIME_PATTERNS = [
    r"\b\d{1,2}(?::\d{2})?\s*(?:a\.?m\.?|p\.?m\.?)\b",
    r"\b\d{1,2}:\d{2}\b",
    r"\b(?:morning|afternoon|evening|tonight|midday|midnight|noon)\b",
]

DATE_REGEX = re.compile("|".join(DATE_PATTERNS), re.IGNORECASE)
TIME_REGEX = re.compile("|".join(TIME_PATTERNS), re.IGNORECASE)

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
}
PCOMP_ACTIVITY_PREPS = {"for"}
WEEKDAY_INDEX = {
    "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
    "friday": 4, "saturday": 5, "sunday": 6,
}
SKIP_MODIFIERS = {"next"}
PAST_MODIFIERS = {"last", "previous"}
RECURRING_MARKERS = {
    "every", "each", "alternate", "monthly", "weekly", "daily",
    "annually", "yearly",
}

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

RELATIVE_DAY_RE = re.compile(
    r"\b(?P<rel>day after tomorrow|two days from now|tomorrow|today|yesterday)\b",
    re.IGNORECASE,
)

CLOCK_TIME_RE = re.compile(
    r"\b(?P<hour>\d{1,2})(?::(?P<minute>\d{2}))?\s*(?P<meridiem>a\.?m\.?|p\.?m\.?)\b",
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
    text = " ".join(t.text for t in all_tokens)
    new_start = all_tokens[0].idx
    new_end = all_tokens[-1].idx + len(all_tokens[-1].text)
    return text, new_start, new_end

  def tokens_overlapping_span(self, doc, start_char, end_char):
    """Return tokens that overlap a character span."""
    return [
        token for token in doc
        if token.idx < end_char
        and token.idx + len(token) > start_char
    ]

  def dependency_path(self, token):
    """Return token -> parent -> ... -> root."""
    path = [token]
    current = token

    while current.head != current:
        current = current.head
        path.append(current)

    return path

  def ancestor_chain(self, token):
    """Plain bottom-up ancestor path: token -> head -> head -> ... -> ROOT."""
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

    if modifier in SKIP_MODIFIERS:
        if diff == 0:
            diff = 7
        return reference_date + timedelta(days=diff + 7)

    # Plain weekday, or this/coming/upcoming/following.
    return reference_date + timedelta(days=diff)
  
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

    rel_match = RELATIVE_DAY_RE.search(lowered)
    weekday_match = WEEKDAY_RE.search(combined_text)

    if rel_match:
        rel = rel_match.group("rel").lower()
        offset = {
            "today": 0, "tomorrow": 1, "day after tomorrow": 2,
            "two days from now": 2, "yesterday": -1,
        }[rel]
        target_date = reference_date + timedelta(days=offset)
    elif weekday_match:
        target_date = self._resolve_weekday_date(
            reference_date, weekday_match.group("weekday"), weekday_match.group("modifier")
        )

    time_of_day = self._resolve_time_of_day(combined_text)

    if target_date is None and time_of_day is None:
        return None, is_recurring, "unresolved"

    if target_date is None:
        target_date = reference_date

    hour, minute = time_of_day if time_of_day else (0, 0)

    resolved_dt = datetime.combine(target_date, time(hour, minute), tzinfo=ZoneInfo(DEFAULT_TIMEZONE))

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
            if ancestor.pos_ == "VERB":
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
    print("11")
    found = []
    for ent in doc.ents:
        if ent.label_ in {"DATE", "TIME"}:
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

    expanded = []
    for item in found:
        result = self.expand_span_by_dependency(doc, item["start_char"], item["end_char"])
        if result is None:
            expanded.append(item)
            continue
        text, start_char, end_char = result
        expanded.append({**item, "text": text, "start_char": start_char, "end_char": end_char})

    # Deduplicate by overlap (expansion means spans from different
    # sources rarely share exact (start,end) anymore). Prefer the
    # spaCy entity record when spans overlap.
    expanded.sort(key=lambda x: (x["start_char"], x["source"] != "spacy_entity"))

    unique = []
    for item in expanded:
        overlaps_existing = any(
            item["start_char"] < kept["end_char"]
            and item["end_char"] > kept["start_char"]
            for kept in unique
        )
        if not overlaps_existing:
            unique.append(item)

    #print("temporal span")
    #print(unique)
    print("12")
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

        # This fallback is specifically for activity nouns.
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
            if shared_ancestor.pos_ != "VERB":
                continue

            # Prefer the straightforward case where the activity noun
            # is directly attached to the shared verb, such as:
            # meeting -> have
            if candidate.head.i != shared_ancestor.i:
                continue

            fallback_matches.append(
                (
                    candidate,
                    temporal_distance + candidate_distance
                )
            )

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
    print("1")
    temporal_spans = self.find_temporal_spans(doc)
    print("2")
    activities = self.find_activity_candidates(doc)
    print("3")
    self.debug_temporal_paths(doc, temporal_spans)
    print("4")
    # One result bucket per activity token.
    results = {}
    for activity in activities:
        results[activity.i] = {
            "activity": self.activity_label(activity),
            "activity_token": activity.text,
            "activity_token_index": activity.i,
            "temporal_expressions": [],
        }

    print("5")
    # Associate each temporal expression with an activity using
    # the dependency path from its token(s).
    for span in temporal_spans:
        span_tokens = self.tokens_overlapping_span(
            doc,
            span["start_char"],
            span["end_char"],
        )
        associated_activity = None
        # A span may contain multiple tokens, such as "9pm tomorrow".
        # Check each token and take the first dependency-supported
        # activity found.
        for span_token in span_tokens:
            associated_activity = self.find_activity_from_dependency(
                span_token,
                activities,
            )

            if associated_activity is not None:
                break

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

        print(
            f"{span['text']!r} "
            f"--> activity={associated_activity.text!r} "
            f"(dependency-supported)"
        )
    print("6")
    # Return only activities that received at least one temporal
    # expression. Keep all their original temporal wording.
    output = []

    for item in results.values():
        if item["temporal_expressions"]:
            item["temporal_expressions"].sort(
                key=lambda x: x["start_char"]
            )
            output.append(item)

    print("7")
    return output

  def build_temporal_entities(self, temporal_activities, reference_dt=None):
    print("8")
    if reference_dt is None:
        reference_dt = datetime.now(ZoneInfo(DEFAULT_TIMEZONE))

    temporal_entities = []

    for item in temporal_activities:
        combined_text = " ".join(
            expr["text"] for expr in item["temporal_expressions"]
        )

        resolved_datetime, is_recurring, date_source = self.resolve_combined_temporal(
            combined_text, reference_dt
        )

        temporal_entities.append({
            "text": combined_text,
            "resolved_datetime": resolved_datetime,
            "recurring": is_recurring,
            "date_source": date_source,
            # Kept for traceability back to the activity this came from;
            # drop this key if you only want the fields shown above.
            "activity": item["activity"],
        })
    print("9")
    return {"temporal_entities": temporal_entities}
  

  def analyze(self, doc, raw_text):
    temporal_entities = []
    temporal_activities = self.extract_temporal_activities(doc, raw_text)
    final_output = self.build_temporal_entities(temporal_activities)
    return final_output
    
