"""
Deterministic date validator.

Cross-checks a first-pass (or audit-pass) categorization_json's "time"
fields against the blueprint's already-resolved temporal_entities,
instead of asking the LLM to recompute dates itself -- which is where
the "Reach office" bad-guess bug came from (LLM invented a datetime
for a recurring item with no single correct date).

This does NOT try to be a full replacement for the LLM audit pass --
it only handles the part that's pure arithmetic/lookup, which is the
part that should never be inconsistent between runs.
"""
from datetime import datetime


def _all_resolved_dates(linguistic_blueprint):
    """Set of every resolved_datetime string the blueprint found."""
    return {
        t["resolved_datetime"]
        for t in linguistic_blueprint.get("evidence", {}).get("temporal_entities", [])
    }


def check_item_dates(categorization_json, linguistic_blueprint):
    """
    Returns a list of warning dicts for any item whose "time" (or
    recurrence.start_date/end_date, if present) doesn't correspond to
    anything the blueprint actually resolved from the transcript.
    Does not mutate categorization_json -- flags only, for a human or
    a targeted follow-up LLM call to review, rather than trusting an
    LLM to silently "fix" it (which is what produced the bad guess).
    """
    known_dates = _all_resolved_dates(linguistic_blueprint)
    warnings = []

    for category in ("tasks", "events", "reminders"):
        for index, item in enumerate(categorization_json.get(category, [])):
            title = item.get("title", "<untitled>")
            time_val = item.get("time")
            recurrence = item.get("recurrence") or {}
            is_recurring = recurrence.get("is_recurring", False)

            # Recurring items should never carry a single-occurrence
            # "time" -- if they do, it's very likely a guess, since a
            # recurring item has no one correct date to anchor to.
            if is_recurring and time_val is not None:
                warnings.append({
                    "category": category,
                    "index": index,  # e.g. categorization_json["tasks"][index]
                    "title": title,
                    "issue": "recurring_item_has_single_time",
                    "detail": f"time={time_val!r} but is_recurring=True; "
                              f"a recurring item has no single occurrence "
                              f"to anchor 'time' to. Likely a guess.",
                })

            # Non-null, non-recurring "time" should trace back to
            # something the blueprint actually found in the transcript.
            if time_val is not None and not is_recurring:
                if time_val not in known_dates:
                    warnings.append({
                        "category": category,
                        "index": index,
                        "title": title,
                        "issue": "time_not_grounded_in_blueprint",
                        "detail": f"time={time_val!r} does not match any "
                                  f"blueprint temporal_entities value; "
                                  f"may be fabricated.",
                    })

            # Recurring items should have start_date/end_date grounded
            # too, if present.
            for bound in ("start_date", "end_date"):
                val = recurrence.get(bound)
                if val is not None:
                    # start_date/end_date are date-only; compare against
                    # the date portion of known resolved datetimes.
                    known_date_parts = {d.split("T")[0] for d in known_dates}
                    if val not in known_date_parts:
                        warnings.append({
                            "category": category,
                            "index": index,
                            "title": title,
                            "issue": f"recurrence.{bound}_not_grounded",
                            "detail": f"{bound}={val!r} does not match any "
                                      f"blueprint temporal_entities date; "
                                      f"may be fabricated.",
                        })

    return warnings


if __name__ == "__main__":
    # Reproduce the exact "Reach office" bug case from the conversation.
    linguistic_blueprint = {
        "evidence": {
            "temporal_entities": [
                {"text": "monday", "resolved_datetime": "2026-07-20T00:00:00"},
                {"text": "9am", "resolved_datetime": "2026-07-18T09:00:00"},
                {"text": "11am", "resolved_datetime": "2026-07-18T11:00:00"},
                {"text": "1pm", "resolved_datetime": "2026-07-18T13:00:00"},
                {"text": "10am", "resolved_datetime": "2026-07-18T10:00:00"},
                {"text": "7/20", "resolved_datetime": "2026-07-20T00:00:00"},
            ]
        }
    }

    # This is the SECOND-pass (audit) output that had the bug --
    # it guessed a datetime for a recurring item.
    buggy_output = {
        "tasks": [
            {
                "title": "Reach office",
                "time": "2026-07-20T10:00:00",  # <- fabricated guess
                "recurrence": {
                    "is_recurring": True,
                    "start_date": "2026-07-20",
                    "end_date": "2026-07-26",  # <- not in blueprint at all
                },
            }
        ],
        "events": [],
        "reminders": [],
    }

    for w in check_item_dates(buggy_output, linguistic_blueprint):
        print(w)
