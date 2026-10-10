import re

from Common import *
from BaseAnalyzer import BaseAnalyzer
from TemporalAnalyzer import TemporalAnalyzer, EVENT_NOUNS, PCOMP_ACTIVITY_PREPS


class ActionAnalyzer(BaseAnalyzer):
    """
    Emits EVERY activity in the text -- verbs AND event nouns -- not just verbs.

    Compared with the old verb-only version:
      - event nouns ("meeting", "appointment", "dinner") are actions too, so
        "I have my steering committee meeting" is no longer invisible just
        because its verb is "have".
      - light/modal verbs ("need to", "want to", "go for") are NOT emitted as
        actions; they become the `modality` of the real action they introduce.
      - words that belong to a date/time phrase ("coming" in "coming Tuesday")
        are never actions.
      - date/time phrases are linked to the specific action they attach to
        (`when`), instead of every action getting the whole sentence's entities.
      - `related_entities` are scoped to the action's own words.
      - `source_segment` is a verbatim slice of the transcript for that action.
      - "for this" / "about that" get a heuristic `refers_to` link.

    Activity-detection logic is shared with TemporalAnalyzer (same vocabulary,
    same dependency walk) so the two analyzers cannot disagree.
    """
    key = "actions"

    _ALWAYS_LIGHT = {"be", "have"}
    # LABEL-ONLY map: lemma -> modality type. Whether a verb is a carrier is decided
    # structurally (see _is_carrier), so a verb missing from this map is still
    # handled correctly -- it just gets modality None instead of a label.
    _MODALITY = {
        # obligation / necessity
        "need": "obligation", "must": "obligation", "should": "obligation",
        "ought": "obligation", "have": "obligation", "got": "obligation",
        "suppose": "obligation", "require": "obligation", "remember": "obligation",
        "forget": "obligation",
        # desire / preference
        "want": "desire", "wish": "desire", "hope": "desire", "like": "desire",
        "love": "desire", "prefer": "desire", "fancy": "desire", "care": "desire",
        # intention / decision
        "plan": "intention", "intend": "intention", "decide": "intention",
        "aim": "intention", "mean": "intention", "propose": "intention",
        "resolve": "intention", "determine": "intention",
        # commitment
        "promise": "commitment", "swear": "commitment", "vow": "commitment",
        "pledge": "commitment", "agree": "commitment", "offer": "commitment",
        "volunteer": "commitment", "commit": "commitment",
        # attempt / effort
        "try": "attempt", "attempt": "attempt", "strive": "attempt",
        "struggle": "attempt", "seek": "attempt",
        # ability / possibility
        "can": "possibility", "could": "possibility", "may": "possibility",
        "might": "possibility", "manage": "ability", "able": "ability",
        # phase of the activity (start/stop/continue)
        "start": "aspect", "begin": "aspect", "continue": "aspect",
        "keep": "aspect", "stop": "aspect", "resume": "aspect", "quit": "aspect",
    }
    # The small spaCy model sometimes fails to lemmatize irregular verbs
    # ("forgot" stays "forgot"), so also match these surface forms.
    _IRREGULAR_FORMS = {
        "forgot": "forget", "forgotten": "forget", "swore": "swear", "sworn": "swear",
        "meant": "mean", "began": "begin", "begun": "begin", "kept": "keep",
        "chose": "decide", "chosen": "decide", "sought": "seek", "undertook": "attempt",
    }
    _SKIP_VERB_DEPS = {"aux", "auxpass", "amod", "compound"}
    _DEMONSTRATIVES = {"this", "that", "it"}
    _TEMPORAL_ENTITY_TYPES = {"DATE", "TIME"}

    def __init__(self, base_date=None, timezone_name=DEFAULT_TIMEZONE, temporal=None):
        # Pass the TemporalAnalyzer you already built so both analyzers share one
        # instance (same base_date / timezone). If omitted, build one from the
        # arguments, so a bare ActionAnalyzer() still works.
        self._temporal = temporal or TemporalAnalyzer(base_date=base_date, timezone_name=timezone_name)

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _inside(tok, spans):
        end = tok.idx + len(tok.text)
        return any(s["start_char"] <= tok.idx and end <= s["end_char"] for s in spans)

    def _is_carrier(self, tok):
        """
        A verb that only hands off to another verb it shares a subject with:
        'need TO buy', 'forgot TO call', 'decided TO start', 'go FOR jogging'.
        Detected from the parse (an xcomp verb and NO object of its own), not from
        a word list. A verb with an object ("ask RAM to send", "remind ME to call")
        is object-control: the verb is itself an action, so it is not a carrier.
        """
        has_xcomp = any(c.dep_ == "xcomp" and c.pos_ == "VERB" for c in tok.children)
        has_obj = any(c.dep_ in ("dobj", "obj", "dative", "iobj") for c in tok.children)
        if has_xcomp and not has_obj:
            return True
        for c in tok.children:
            if c.dep_ == "prep" and c.lemma_.lower() in PCOMP_ACTIVITY_PREPS and any(
                    g.dep_ == "pcomp" and g.pos_ == "VERB" for g in c.children):
                return True
        return False

    def _find_action_heads(self, doc, spans):
        verb_heads = []
        for tok in doc:
            if tok.pos_ != "VERB" or tok.dep_ in self._SKIP_VERB_DEPS:
                continue
            lemma = tok.lemma_.lower()
            if lemma in self._ALWAYS_LIGHT or self._inside(tok, spans):
                continue
            if lemma == "do" and not any(c.dep_ in ("dobj", "obj") for c in tok.children):
                continue
            if self._is_carrier(tok):
                continue
            verb_heads.append(tok)
        verb_ids = {t.i for t in verb_heads}

        noun_heads = []
        for tok in doc:
            if tok.pos_ not in ("NOUN", "PROPN") or tok.lemma_.lower() not in EVENT_NOUNS:
                continue
            if tok.dep_ == "compound" or self._inside(tok, spans):
                continue
            # "attend the meeting": the verb already carries the object
            if tok.dep_ in ("dobj", "obj") and tok.head.i in verb_ids:
                continue
            anc = tok.head
            connected = False
            while True:
                if anc.pos_ in ("VERB", "AUX"):
                    connected = True
                    break
                if anc.head == anc:
                    break
                anc = anc.head
            if connected:
                noun_heads.append(tok)

        heads = [(t, "verb") for t in verb_heads] + [(t, "event_noun") for t in noun_heads]
        heads.sort(key=lambda p: p[0].i)
        return heads

    def _carrier_chain(self, head, action_ids):
        """Climb through light/modal carriers: jogging -> for -> go -> need."""
        chain, cur = [], head
        for _ in range(6):
            parent = cur.head
            if parent == cur:
                break
            if cur.dep_ == "xcomp" and parent.pos_ in ("VERB", "AUX") and parent.i not in action_ids:
                chain.append(parent)
                cur = parent
            elif (cur.dep_ == "pcomp" and parent.dep_ == "prep"
                  and parent.head.pos_ in ("VERB", "AUX") and parent.head.i not in action_ids):
                chain.extend([parent, parent.head])
                cur = parent.head
            else:
                break
        return chain

    def _governing_verb(self, noun):
        anc = noun.head
        while True:
            if anc.pos_ in ("VERB", "AUX"):
                return anc
            if anc.head == anc:
                return None
            anc = anc.head

    def _modality_type(self, tok):
        for key in (tok.lemma_.lower(), self._IRREGULAR_FORMS.get(tok.text.lower()), tok.text.lower()):
            if key in self._MODALITY:
                return self._MODALITY[key]
        return None

    def _modality(self, head, chain):
        for c in head.children:  # "I must finish", "we should call"
            if c.dep_ in ("aux", "auxpass") and self._modality_type(c):
                return {"type": self._modality_type(c), "marker": c.text}
        # Outermost carrier = the speaker's stance ("DECIDED to start learning").
        for c in reversed(chain):
            if c.pos_ not in ("VERB", "AUX"):
                continue
            if self._modality_type(c):
                return {"type": self._modality_type(c), "marker": c.text}
            if c.lemma_.lower() == "go" and c.tag_ == "VBG":      # "I'm going to call ..."
                return {"type": "intention", "marker": "going to"}
        return None

    @staticmethod
    def _own_subject(tok):
        for c in tok.children:
            if c.dep_ in ("nsubj", "nsubjpass"):
                return c
        return None

    def _subject(self, head, chain, gov, action_ids):
        """Returns (subject_token, is_direct). Inherited subjects ("buy X and
        call Y", "buy X before taking Y") are returned with is_direct=False."""
        for tok in [head] + chain + ([gov] if gov is not None else []):
            s = self._own_subject(tok)
            if s is not None:
                return s, True
        cur = head
        for _ in range(4):
            if cur.dep_ == "pcomp" and cur.head.dep_ == "prep":
                nxt = cur.head.head
            elif cur.dep_ in ("conj", "advcl"):
                nxt = cur.head
            else:
                break
            if nxt == cur:
                break
            for tok in [nxt] + self._carrier_chain(nxt, action_ids):
                s = self._own_subject(tok)
                if s is not None:
                    return s, False
            cur = nxt
        return None, False

    _CLAUSE_DEPS = {"relcl", "acl", "advcl", "ccomp", "xcomp", "conj"}

    def _object_phrase(self, c, spans):
        skip = set()
        for sub in c.subtree:                       # don't swallow nested clauses
            if sub.dep_ in self._CLAUSE_DEPS and sub is not c:
                skip |= set(sub.subtree)
        toks = sorted((t for t in c.subtree
                       if t not in skip and t.pos_ not in ("VERB", "AUX")
                       and t.dep_ != "det" and not self._inside(t, spans)), key=lambda t: t.i)
        return " ".join(t.text for t in toks)

    def _objects(self, head, spans):
        out = []
        for c in head.children:
            if c.dep_ not in ("dobj", "obj", "attr", "dative") or self._inside(c, spans):
                continue
            if c.tag_ in ("WDT", "WP") and head.dep_ == "relcl":
                # "the document that I must finish": object is the noun the clause modifies
                phrase = self._noun_description(head.head, spans)
            else:
                phrase = self._object_phrase(c, spans)
            if phrase:
                out.append(phrase)
        return out

    def _verb_label(self, head, spans):
        objs = self._objects(head, spans)
        return " ".join([head.text] + objs)

    def _noun_description(self, head, spans):
        mods = [t for t in head.subtree
                if t.i < head.i and t.dep_ in ("amod", "compound") and not self._inside(t, spans)]
        toks = sorted(mods + [head], key=lambda t: t.i)
        return " ".join(t.text for t in toks)

    # ------------------------------------------------------------------
    def analyze(self, doc, raw_text):
        t = self._temporal
        spans = t.find_temporal_spans(doc)
        heads = self._find_action_heads(doc, spans)
        head_tokens = [h for h, _ in heads]
        action_ids = {h.i for h in head_tokens}
        sents = list(doc.sents)
        sent_index = {s.start: n for n, s in enumerate(sents)}

        def sent_no(tok):
            return sent_index[tok.sent.start]

        # temporal span -> owning action head
        when = {h.i: [] for h in head_tokens}
        when_spans = {h.i: [] for h in head_tokens}
        for span in spans:
            for tok in t.tokens_overlapping_span(doc, span["start_char"], span["end_char"]):
                owner = t.find_activity_from_dependency(tok, head_tokens)
                if owner is not None:
                    when[owner.i].append({"text": span["text"], "label": span["label"]})
                    when_spans[owner.i].append(span)
                    break

        actions = []
        for n, (head, kind) in enumerate(heads, start=1):
            chain = self._carrier_chain(head, action_ids)
            gov = self._governing_verb(head) if kind == "event_noun" else None
            if gov is not None and gov.i in action_ids:
                gov = None
            subj, subj_direct = self._subject(head, chain, gov, action_ids)

            # tokens that belong to THIS action (minus nested actions' own words)
            own = set(head.subtree)
            for other in head_tokens:
                if other.i != head.i and other in head.subtree:
                    own -= set(other.subtree)

            seg = set(own) | set(chain)
            for sp in when_spans[head.i]:   # linked dates/times belong to this action's segment
                seg |= set(t.tokens_overlapping_span(doc, sp["start_char"], sp["end_char"]))
            if gov is not None:
                seg.add(gov)
            if subj is not None and subj_direct:
                seg |= set(subj.subtree)
            toks = sorted(seg, key=lambda x: x.i)
            while toks and toks[-1].pos_ in ("ADP", "CCONJ", "SCONJ", "PUNCT", "PART"):
                toks.pop()
            while toks and toks[0].pos_ in ("PUNCT", "CCONJ", "SCONJ"):
                toks.pop(0)
            source_segment = doc.text[toks[0].idx: toks[-1].idx + len(toks[-1].text)] if toks else head.text

            objects = self._objects(head, spans) if kind == "verb" else []
            captured = {(subj.text if subj is not None else "").lower()} | {o.lower() for o in objects}
            own_idx = {x.i for x in own}
            related = [
                {"text": e.text, "type": e.label_}
                for e in doc.ents
                if e.label_ not in self._TEMPORAL_ENTITY_TYPES
                and all(i in own_idx for i in range(e.start, e.end))
                and e.text.lower() not in captured
                and e.text.lower() not in head.text.lower()
            ]

            actions.append({
                "id": n,
                "kind": kind,
                "verb": head.lemma_.lower() if kind == "verb" else None,
                "text": head.text,
                "activity": self._verb_label(head, spans) if kind == "verb" else head.text,
                "description": self._verb_label(head, spans) if kind == "verb" else self._noun_description(head, spans),
                "modality": self._modality(head, chain),
                "subject": subj.text if subj is not None else None,
                "objects": objects,
                "when": when[head.i],
                "related_entities": related,
                "refers_to": None,
                "source_segment": source_segment,
            })

        # "for this" / "about that": heuristic link to the nearest earlier event noun
        by_head = {h.i: a for (h, _), a in zip(heads, actions)}
        for tok in doc:
            if tok.lower_ not in self._DEMONSTRATIVES or tok.pos_ != "PRON" or tok.dep_ not in ("pobj", "dobj"):
                continue
            owner = t.find_activity_from_dependency(tok, head_tokens)
            if owner is None:
                continue
            candidates = [
                (h, a) for (h, k), a in zip(heads, actions)
                if k == "event_noun" and h.i < tok.i and h.i != owner.i
                and sent_no(tok) - sent_no(h) <= 1
            ]
            if candidates:
                _, ante = candidates[-1]
                by_head[owner.i]["refers_to"] = {
                    "pronoun": tok.text, "action_id": ante["id"], "confidence": "heuristic"
                }
        return actions
