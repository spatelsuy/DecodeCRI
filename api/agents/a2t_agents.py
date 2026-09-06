import sys
import os

import spacy

import yaml
import time
import difflib
import json
from datetime import datetime
from typing import Dict, Any
from models import AudioProcessingState
from groq_client import call_groq, call_groq_transcribe, call_groqJSON

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from spacy_lib.linguistic_blueprint import generate_blueprint
from date_cross_check import check_item_dates 

A2T_PROMPT = """
You are an intelligent assistant that converts raw spoken text into structured personal organization data.
The spoken text may be unpunctuated, conversational, fragmented, repetitive, partially incorrect due to speech-to-text errors, or code-switched (e.g. English + Hindi / Hinglish).

Today's date is: "{{CURRENT_DATE}}"
Date format: YYYY-MM-DD
User Timezone: America/New_York

Extract and categorize the user's intent into:
1. tasks      – things the user needs to do
2. events     – scheduled meetings, appointments, or planned activities
3. reminders  – time-bound alerts, follow-ups, or deadline prompts
4. notes      – background information that is not directly actionable

---
RULES

1. OUTPUT
Return only one valid JSON object. No markdown, no backticks, no commentary outside the JSON.

2. ATOMIC INTENTS
One intent = one item. Split multi-action sentences into separate items. 
CRITICAL: A recurring item (e.g., "every Monday for 12 months") is considered ONE single intent. Do NOT explode, loop, or generate separate JSON objects for each individual calendar date. Represent it as a single object utilizing the 'recurrence' schema.

3. MISSING OR UNCLEAR VALUES
Use null for any field that is not clearly present or cannot be reliably inferred. Do not guess or invent people, dates, times, places, or context.

4. TEMPORAL CONTEXT INHERITANCE
If the user establishes a date or time anchor (e.g. "tomorrow", "on Friday", "next week"), apply it to all following related items until a new anchor is introduced. Natural speech states the day once, then lists items — do not require the date to be repeated. If a broader anchor is already set and a later item adds a specific time, combine them.
Example: "Tomorrow I have a call at 10 AM and a meeting at 3 PM." → both items are tomorrow.
CRITICAL TEMPORAL ISOLATION: Only apply a specific date/time anchor to an item if that specific time token appears directly in the item's time_context from the provided blueprint or explicitly touches it in the text segment. If an action's isolated time_context is null, do not arbitrarily apply neighboring precise time anchors to it.

5. TIME NORMALIZATION
Resolve all time expressions against "{{CURRENT_DATE}}". Normalize to ISO-8601 datetime strings when date and/or time can be determined. 
Prefer any pre-resolved value found in linguistic_blueprint.temporal_entities[].resolved_datetime over deriving it yourself —
only fall back to your own resolution for time expressions not present in that list.
For vague time expressions:
- morning → 09:00 | afternoon → 15:00 | after lunch → 14:00 | evening → 18:00 | night → 21:00

6. CATEGORY DISCIPLINE
- tasks: actionable to-dos
- events: meetings, appointments, scheduled activities
- reminders: triggered by "remind me", "don't let me forget", "remember to", or any time-bound alert
- notes: context, background, or supporting detail not directly actionable


6a. CATEGORY RESOLUTION TIE-BREAKER PROTOCOL
If an item overlaps multiple categories, you MUST resolve it using this strict linguistic syntax hierarchy:

6a.1. FORCE TO 'REMINDERS' if the user explicitly asks to be alerted or prompted about this item -- phrasing like "remind me", "remind me to", "don't let me forget", "remember to", "wake me up", "please remind me",
or similar self-alert requests, regardless of exact wording or position in the sentence.
   - Example: "Remind me to attend the 9am scrum" → REMINDER (Overrides Event).

6a.1b. MERGE, DON'T DUPLICATE: A "remind me" / self-alert verb that refers to the SAME underlying commitment as another action in the same sentence (e.g. "pay the bill... please remind me") is NOT a separate atomic intent. It is a classification signal for that one commitment --
merge both actions into a single item, classified per rule 6a.1, not two items.

6a.2. FORCE TO 'EVENTS' if the text describes a meeting, appointment, interactive session, social plan, or presence-based commitment involving a specific time or location anchor.
   - Example: "I need to go to office at 8am" or "I have a call with Bob" → EVENT (Overrides Task).

6a.3. FORCE TO 'TASKS' if the action is an independent, non-interactive, execution-based chore, deliverable, or to-do, even if it has a target time window or general date constraint.
   - Example: "I need to prepare the complexity score tonight" → TASK.

6a.4. RECURRING ROUTINE TIEBREAK: For a recurring, non-social, self-directed commitment (commute, arrival time, daily routine) that could plausibly fit either 6a.2 or 6a.3, classify as TASKS. Reserve EVENTS for occurrences that
are either one-time, or socially anchored (a meeting, a call, a visit involving another named person).
   - Example: "I need to reach office by 8am every day this week" → TASK
     (recurring, solo routine).
   - Example: "I need to go to office at 9am with Hari" → EVENT (one-time,
     names another person).

7. LINKING
If one item depends on or refers to another, set "related_to" to the exact title string of the parent item.

8. PRIORITY
- high: urgent or deadline-sensitive
- medium: important but not urgent
- low: routine or informational (default for all categories if not implied)

9. DEADLINES
Set "is_deadline" to true only when the user clearly states a cutoff, due date, or "must be done by" condition. Otherwise false.

10. DEDUPLICATION & ANTI-LOOPING
Do not create duplicate items. 
CRITICAL: Never generate multiple separate task/event entries for repeating schedules or occurrences. If a user says "every day" or "every week", output EXACTLY ONE item container and capture the repetition rules inside the 'recurrence' field.

11. CODE-SWITCHED / NATURAL SPEECH
Understand Hinglish and mixed-language input. Ignore filler words and ASR noise unless they change the meaning. Interpret intent conservatively.

12. LINGUISTIC BLUEPRINT CROSS-REFERENCE
You will receive a 'linguistic_blueprint' JSON object with this shape:
{
  "user_speech_transcript": string,
  "language": string,
  "current_date": ISO datetime, // matches {{CURRENT_DATE}}; if they ever
                                // differ, treat {{CURRENT_DATE}} as authoritative
  "evidence": {
    "temporal_entities":   [{ "text": string, "resolved_datetime": ISO datetime }],
    "actions": [{ "id": int, "verb": string, "text": string,
                 "subject": string|null, "objects": string[],
                 "sentence": string, "related_entities": [{"text": string, "type": string}] }],
    "relationship_hints":  [{ "type": "AFTER"|"BEFORE", "text": string }],
    "correction_signals":  [{ "text": string, "start_char": int, "end_char": int }],
    "possible_typos":      [{ "original": string, "suggestion": string }],
    "entities":            [{ "text": string, "type": string,
                               "possibly_superseded": bool, "correction_marker": string|null,
                               "possibly_mislabeled": bool, "suggested_type": string|null }]
  }
}
EXACT COUNT ALIGNMENT: Your final generated arrays must match the intent boundaries implied by evidence.actions.
Every action block should map to a corresponding entry in your response (some may merge into one intent per the ATOMIC INTENTS rule; do not silently drop one).
- Use evidence.actions[].subject/objects as the acting party and target of each intent.
- Use evidence.actions[].sentence and evidence.actions[].related_entities to populate the "context" field. Do not leave "context" null if related_entities contains anything not already reflected in the item's title (e.g. a person's name, a related meeting, a
  location) -- summarize that supporting detail briefly. Only leave "context" null if there is genuinely nothing beyond the title.
- Use evidence.relationship_hints to help decide sequencing and populate "related_to".
- Use evidence.correction_signals to detect self-corrected statements — prefer the corrected version and do not create a duplicate item for the discarded phrasing.
- Use evidence.possible_typos to silently correct obvious ASR errors in titles/notes.
- In evidence.entities, if "possibly_superseded" is true, the user verbally replaced this value during the transcript (see "correction_marker" for the trigger word) — do not create an item from it; use the corrected value stated afterward instead.
- In evidence.entities, if "possibly_mislabeled" is true, this is a linguistic-analysis labeling error, NOT anything the user said — trust "suggested_type" over "type" and use the value normally; do not discard or treat it as corrected.
- This blueprint currently does NOT flag negation. Detect cancellations, "never mind", "skip that", or negated actions directly from user_speech_transcript using your own language understanding, and do not create a standard active task/event for them.
- Correct any clear misalignments or leaked context from the blueprint using your advanced language understanding of the raw user_speech_transcript.


Titles must be concise and intent-driven. Preserve the user's real meaning. Store supporting detail in context or notes, not in the title.
Now process the spoken text and return only the final JSON object.
"""


VALIDATION_PROMPT = """
You are a data validation utility. Your job is to audit a structured JSON object against the raw text it was extracted from and correct any mistakes.

Today's date is: "{{CURRENT_DATE}}"
Day of the week: "{{CURRENT_DAY_OF_WEEK}}"
User Timezone: America/New_York

INSTRUCTIONS FOR READING THE INPUT PAYLOAD:
You will receive a JSON payload with two keys. Treat them as follows:
1. "user_speech_transcript" -> This contains the raw spoken text from the user. Use this as your source of truth.
2. "extracted_json" -> This contains the first-pass structural data that you need to audit, verify, and correct.

AUDIT CHECKLIST:
1. MISSING DATA: Compare "user_speech_transcript" to "extracted_json". Are there any tasks, events, or reminders present in the transcript that were left out of the JSON? If so, add them.
2. INVALID COPIES: Look inside "extracted_json". Did the first pass create redundant duplicates? Two patterns to check:
   a) A note entry that only repeats details already explained inside a task, event, or reminder -- remove the redundant note.
   b) The SAME underlying commitment appearing as both a task/event AND a reminder. This is one stated intent, not two. Keep exactly ONE copy:
      - If "user_speech_transcript" contains explicit self-alert phrasing ("remind me", "remind me to", "don't let me forget", "remember to", "please remind me", "wake me up", or similar -- regardless of exact wording or position), keep the REMINDER copy. Merge any recurrence, context, or priority detail from the discarded copy into the one you keep.
      - Otherwise, keep whichever category matches the action itself and discard the reminder copy.
   Never output both copies.

3. CALENDAR MATH: Recalculate all dates against "{{CURRENT_DATE}}" and "{{CURRENT_DAY_OF_WEEK}}". Match day names (e.g., "Thursday") to their true upcoming date, and convert expressions like "before Friday" to Thursday at 23:59:59.
4. SOURCE VERIFICATION: Check the "source_segment" field. Ensure the text snippet inside it actually exists word-for-word in the "user_speech_transcript". If you modify an item's date or time during this audit, ensure the "source_segment" still reflects the text that provided that context.

OUTPUT INSTRUCTIONS:
Fix any errors found during the audit. 
CRITICAL: Return ONLY the raw schema object containing the keys "extracted_on", "tasks", "events", "reminders", and "notes". Do NOT wrap your response inside "extracted_json", "user_payload", or any other nested root key.
Output ONLY the finalized, repaired, and structurally valid JSON object matching the original flat schema. 
Do not include markdown formatting, backticks, or any conversational text.

"""
# ========================================================
# NEW: RUN SPACY LOCAL DEPENDENCY PARSING BEFORE API CALL
# ========================================================
def get_linguistic_blueprint(text_to_analyze: str) -> Dict[str, Any]:
    """
    Parses unpunctuated voice transcripts locally using spaCy dependency trees 
    to extract structural hooks for verbs, objects, time context, and negation.
    """
    try:
        nlp = spacy.load("en_core_web_sm")
        doc = nlp(text_to_analyze)
        detected_actions = []
        
        for token in doc:
            if token.pos_ in ["VERB", "AUX"] or token.dep_ == "ROOT":
                verb_text = token.text
                obj_text = None
                time_markers = []
                
                # 1. Extract Objects (Direct or Prepositional Destinations)
                dobj_tokens = [c for c in token.children if c.dep_ == "dobj"]
                if dobj_tokens:
                    obj_text = "".join([t.text_with_ws for t in dobj_tokens[0].subtree]).strip()
                else:
                    prep_tokens = [c for c in token.children if c.dep_ == "prep"]
                    if prep_tokens:
                        obj_text = f"{token.text} " + "".join([t.text_with_ws for t in prep_tokens[0].subtree]).strip()
                
                # 2. Handle nested clauses (e.g., "Remind me to put...")
                xcomp_tokens = [c for c in token.children if c.dep_ == "xcomp"]
                if xcomp_tokens:
                    nested_verb = xcomp_tokens[0]
                    nested_dobj = [c for c in nested_verb.children if c.dep_ in ["dobj", "pobj", "advmod"]]
                    if nested_dobj:
                        verb_text = nested_verb.text
                        obj_text = "".join([t.text_with_ws for t in nested_verb.subtree]).strip()

                # 3. Extract Related Times / Anchors
                for sub_token in doc:
                    if sub_token.ent_type_ in ["TIME", "DATE"] or sub_token.dep_ == "npadvmod" or sub_token.text.lower() in ["tonight", "morning", "evening"]:
                        ancestors = [a.text for a in sub_token.ancestors]
                        if verb_text in ancestors or (obj_text and any(w in obj_text for w in ancestors)):
                            if sub_token.text not in time_markers:
                                time_markers.append(sub_token.text)
                
                # 4. Finalize & Sanitize Entry
                if obj_text:
                    for tm in time_markers:
                        obj_text = obj_text.replace(tm, "").strip(", ")
                    
                    # Capture negation flags (e.g., "not", "never")
                    is_negated = any(child.dep_ == "neg" for child in token.children) or \
                                 any(child.dep_ == "neg" for child in token.head.children)

                    action_entry = {
                        "verb": verb_text,
                        "object": obj_text,
                        "time_context": " ".join(time_markers) if time_markers else None,
                        "is_negated": is_negated
                    }
                    
                    # Prevent duplicates and filter out weak direct objects like "me"
                    if action_entry not in detected_actions and obj_text.lower() != "me":
                        detected_actions.append(action_entry)
                        
        return {"detected_actions": detected_actions}

    except Exception as spacy_err:
        print(f"Warning: spaCy fallback triggered due to error: {spacy_err}")
        return {"detected_actions": []}
        

################################################################################################

def transcribe_audio_text(state: AudioProcessingState) -> Dict[str, Any]:
    print(f"--- Node 1: Transcribing via Raw Requests for {state['user_name']} ---")
    
    try:
        # Call the new direct request function
        text_output = call_groq_transcribe(
            file_bytes=state["file_bytes"],
            file_name=state["file_name"]
        )
        return {"transcription_text": text_output}
        
    except Exception as e:
        print(f"Transcription Error: {e}")
        return {"transcription_text": f"Error during transcription: {str(e)}"}



def categorize_text(state: AudioProcessingState) -> Dict[str, Any]:
 
    text_to_analyze = state.get("transcription_text", "")
    if not text_to_analyze or "Error during transcription" in text_to_analyze:
        return {"categorization_json": {"error": "No valid text to analyze"}}

    DEFAULT_TIMEZONE = "UTC"
    user_tz = state.get("user_timezone") or DEFAULT_TIMEZONE
    linguistic_blueprint = generate_blueprint(text_to_analyze, timezone_name=user_tz)
    print("LINGUISTIC_BLUEPRINT", linguistic_blueprint)
    user_payload = {
        "linguistic_blueprint": linguistic_blueprint
    }
 
    try:
      today_date = datetime.today().strftime('%Y-%m-%d')
      client_time = state["client_time"]
      final_prompt = A2T_PROMPT.replace('{{CURRENT_DATE}}', client_time)
      analysis_result = call_groqJSON(
        system_prompt=final_prompt,
        user_payload=user_payload,
        model="openai/gpt-oss-120b"
      )
      print("\n===============categorization_json============\n", analysis_result)
 
      # CHANGED: also persist linguistic_blueprint in state so
      # categorize_validation can read it back later -- it needs the
      # same blueprint to run the deterministic date check.
      return {
          "categorization_json": analysis_result,
          "linguistic_blueprint": linguistic_blueprint
      }
 
    except Exception as e:
      print(f"Categorization Node Error: {e}")
      return {"categorization_json": {"error": f"Failed to organize schedule: {str(e)}"}}


def validate_and_ground_times(
    extracted_json: dict = None, 
    categorized_data: dict = None, 
    blueprint_temporal_entities: list = None,
    **kwargs
) -> dict:
    """
    Ensures extracted event/task timestamps strictly match valid timestamps 
    generated in Stage 1, while tolerating end-of-day offsets and LLM timezone corrections.
    """
    # Standardize input dictionary parameter
    data = extracted_json or categorized_data or {}
    if not data or not blueprint_temporal_entities:
        return data

    # Extract valid dates and exact timestamps from blueprint
    blueprint_timestamps = set()
    blueprint_dates = set()

    for entity in blueprint_temporal_entities:
        dt_str = entity.get("resolved_datetime")
        if dt_str:
            blueprint_timestamps.add(dt_str)
            base_date = dt_str.split("T")[0]
            blueprint_dates.add(base_date)
            
            # Allow +/- 1 day tolerance for midnight boundaries (e.g. "before Monday" => Sunday 23:59:59)
            try:
                dt_obj = datetime.fromisoformat(dt_str)
                blueprint_dates.add((dt_obj - timedelta(days=1)).strftime("%Y-%m-%d"))
                blueprint_dates.add((dt_obj + timedelta(days=1)).strftime("%Y-%m-%d"))
            except ValueError:
                pass

    # Sort entities by phrase length descending to prioritize longer phrases ("8:30 pm" over "8 pm")
    sorted_entities = sorted(
        [e for e in blueprint_temporal_entities if e.get("resolved_datetime")],
        key=lambda x: len(x.get("text", "")),
        reverse=True
    )

    for category in ["tasks", "events", "reminders"]:
        for item in data.get(category, []):
            item_time = item.get("time")
            if not item_time:
                continue

            # Case 1: Exact timestamp match
            if item_time in blueprint_timestamps:
                continue

            # Case 2: Calendar date matches within +/- 1 day boundary tolerance
            item_date = item_time.split("T")[0] if "T" in item_time else None
            if item_date and item_date in blueprint_dates:
                continue

            # Case 3: Timestamp shifted/ungrounded — attempt source segment text snapping
            matched_time = None
            source_seg = item.get("source_segment", "").lower()

            for entity in sorted_entities:
                entity_text = entity.get("text", "").lower()
                if entity_text and entity_text in source_seg:
                    matched_time = entity.get("resolved_datetime")
                    break

            if matched_time:
                item["time"] = matched_time

    return data   

def categorize_validation(state: AudioProcessingState) -> Dict[str, Any]:
    """Node 2: Validate the extracted JSON."""
    print("--- Node 2: Validate extraction")
 
    text_to_analyze = state.get("transcription_text", "")
    if not text_to_analyze or "Error during transcription" in text_to_analyze:
      return {"categorization_json": {"error": "No valid text to validate"}}
 
    json_to_analyze = state.get("categorization_json", "")
    print("json_to_analyze=======\n", json_to_analyze)
 
    # CHANGED: json_to_analyze is a dict, so `in` was checking dict
    # KEYS, not error text -- this never actually caught a failure.
    # Use .get("error") instead.
    if not json_to_analyze or json_to_analyze.get("error"):
      return {"categorization_json": {"error": "No valid text to validate"}}
 
    # NEW: read back the blueprint saved by categorize_text
    linguistic_blueprint = state.get("linguistic_blueprint", {})
 
    user_payload = {
      "user_speech_transcript": text_to_analyze,
      "extracted_json": json_to_analyze
    }
 
    try:
      today_date = datetime.today().strftime('%Y-%m-%d')
      client_time = state["client_time"]
      dt_obj = datetime.strptime(client_time, '%Y-%m-%d')
      day_of_week = dt_obj.strftime('%A')
      final_prompt = VALIDATION_PROMPT.replace('{{CURRENT_DATE}}', client_time)
      final_prompt = final_prompt.replace('{{CURRENT_DAY_OF_WEEK}}', day_of_week)
      analysis_result = call_groqJSON(
        system_prompt=final_prompt,
        user_payload=user_payload,
        model="openai/gpt-oss-120b"
      )
      print_json_diff(json_to_analyze, analysis_result)
 
      # NEW: deterministic check on the audit pass's OWN output --
      # this is where the fabricated "Reach office" datetime actually
      # came from, so we check the result of THIS call, not the input.
      date_warnings = check_item_dates(analysis_result, linguistic_blueprint)
      if date_warnings:
          print("DATE VALIDATION WARNINGS:", date_warnings)
      
      grounded_analysis_result = validate_and_ground_times(
          extracted_json=analysis_result,
          blueprint=linguistic_blueprint,
          client_time=state["client_time"]
      )   
 
      return {
          "categorization_json": grounded_analysis_result,
          "date_warnings": date_warnings  # NEW: optional, for logging/UI/retry later
      }
 
    except Exception as e:
      print(f"Categorization Node Error: {e}")
      return {"categorization_json": {"error": f"Failed to organize schedule: {str(e)}"}}

def print_json_diff(before_dict, after_dict):
    # Convert both dictionaries to pretty-printed, sorted JSON strings
    before_str = json.dumps(before_dict, indent=2, sort_keys=True).splitlines()
    after_str = json.dumps(after_dict, indent=2, sort_keys=True).splitlines()
    
    # Generate the unified diff
    diff = difflib.unified_diff(
        before_str, 
        after_str, 
        fromfile='Stage 1: Extracted', 
        tofile='Stage 2: Validated', 
        lineterm=''
    )
    
    # Print the result
    print("\n--- JSON CHANGE LOG ---")
    diff_text = '\n'.join(list(diff))
    if not diff_text:
        print("No changes detected. The validation step matched the extraction step perfectly.")
    else:
        print(diff_text)
