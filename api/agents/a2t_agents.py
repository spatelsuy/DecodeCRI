
import spacy

import yaml
import time
import difflib
import json
from datetime import datetime
from typing import Dict, Any
from models import AudioProcessingState
from groq_client import call_groq, call_groq_transcribe, call_groqJSON
from linguistic_blueprint import generate_blueprint

A2T_PROMPT = """
You are an intelligent assistant that converts raw spoken text into structured personal organization data.

The spoken text may be unpunctuated, conversational, fragmented, repetitive, partially incorrect due to speech-to-text errors, or code-switched (e.g. English + Hindi / Hinglish).

Today's date is: "{{CURRENT_DATE}}"
Date format: YYYY-MM-DD

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

6a.1. FORCE TO 'REMINDERS' if the text contains explicit self-alert phrasing: "remind me to", "don't let me forget", "remember to", or "wake me up". 
   - Example: "Remind me to attend the 9am scrum" → REMINDER (Overrides Event).

6a.2. FORCE TO 'EVENTS' if the text describes a meeting, appointment, interactive session, social plan, or presence-based commitment involving a specific time or location anchor.
   - Example: "I need to go to office at 8am" or "I have a call with Bob" → EVENT (Overrides Task).

6a.3. FORCE TO 'TASKS' if the action is an independent, non-interactive, execution-based chore, deliverable, or to-do, even if it has a target time window or general date constraint.
   - Example: "I need to prepare the complexity score tonight" → TASK.

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
  "raw_text": string,
  "current_date": ISO datetime, // matches {{CURRENT_DATE}}; if they ever
                                // differ, treat {{CURRENT_DATE}} as authoritative
  "evidence": {
    "temporal_entities":   [{ "text": string, "resolved_datetime": ISO datetime }],
    "actions":             [{ "id": int, "verb": string, "text": string,
                               "subject": string|null, "objects": string[] }],
    "relationship_hints":  [{ "type": "AFTER"|"BEFORE", "text": string }],
    "correction_signals":  string[],   // e.g. "actually", "wait", "i mean" — signals
                                       // the user is self-correcting; when present near
                                       // an item, prefer the corrected/later phrasing
    "possible_typos":      [{ "original": string, "suggestion": string }],
    "entities":            [{ "text": string, "type": string }]
  }
}

EXACT COUNT ALIGNMENT: Your final generated arrays must match the intent boundaries implied by evidence.actions. 
Every action block should map to a corresponding entry in your response (some may merge into one intent per the ATOMIC INTENTS rule; do not silently drop one).
- Use evidence.actions[].subject/objects as the acting party and target of each intent.
- Use evidence.relationship_hints to help decide sequencing and populate "related_to".
- Use evidence.correction_signals to detect self-corrected statements — prefer the corrected version and do not create a duplicate item for the discarded phrasing.
- Use evidence.possible_typos to silently correct obvious ASR errors in titles/notes.
- This blueprint currently does NOT flag negation. Detect cancellations, "never mind", "skip that", or negated actions directly from user_speech_transcript using your own language understanding, and do not create a standard active task/event for them.
- Correct any clear misalignments or leaked context from the blueprint using your advanced language understanding of the raw user_speech_transcript.



Titles must be concise and intent-driven. Preserve the user's real meaning. Store supporting detail in context or notes, not in the title.
Now process the spoken text and return only the final JSON object.
"""




VALIDATION_PROMPT = """
You are a data validation utility. Your job is to audit a structured JSON object against the raw text it was extracted from and correct any mistakes.

Today's date is: "{{CURRENT_DATE}}"
Day of the week: "{{CURRENT_DAY_OF_WEEK}}"

INSTRUCTIONS FOR READING THE INPUT PAYLOAD:
You will receive a JSON payload with two keys. Treat them as follows:
1. "user_speech_transcript" -> This contains the raw spoken text from the user. Use this as your source of truth.
2. "extracted_json" -> This contains the first-pass structural data that you need to audit, verify, and correct.

AUDIT CHECKLIST:
1. MISSING DATA: Compare "user_speech_transcript" to "extracted_json". Are there any tasks, events, or reminders present in the transcript that were left out of the JSON? If so, add them.
2. INVALID COPIES: Look inside "extracted_json". Did the first pass create redundant duplicates (e.g., creating an entry under 'notes' for details already explained inside a task)? If so, clean them up.
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

    linguistic_blueprint = get_linguistic_blueprint(text_to_analyze)
    generate_blueprint(text_to_analyze)
    print("LINGUISTIC_BLUEPRINT", linguistic_blueprint)
    user_payload = {
        "raw_audio_transcript": text_to_analyze, 
        "linguistic_blueprint": linguistic_blueprint,
        "system_action_directives": {
        "classification_rule_matrix": [
             {
                "if_blueprint_verb_implies": "Action, execution, chore, preparation, operational task, or individual work", 
                "force_category": "tasks",
                "examples": ["prepare", "check", "write", "fix", "review", "update", "send"]
             },
             {
                "if_blueprint_verb_implies": "Interactive meeting, scheduled sync, presence-based commitment, or calendar block", 
                "force_category": "events",
                "examples": ["attend", "meet", "call", "go to", "visit", "interview"]
             },
             {
                "if_blueprint_verb_implies": "An alert request, a reminder anchor, or a request to not forget", 
                "force_category": "reminders",
                "examples": ["remind", "remember", "forget"]
             }
        ]
        }
    }
    
    try:
      # Call your existing function using a smart, large context model
      today_date = datetime.today().strftime('%Y-%m-%d')
      client_time = state["client_time"]
      final_prompt = A2T_PROMPT.replace('{{CURRENT_DATE}}', client_time)
      analysis_result = call_groqJSON(
        system_prompt=final_prompt,
        user_payload=user_payload,
        model="openai/gpt-oss-120b"
      )
      # This will be a standard Python dictionary containing the organized structure
      print("\n===============categorization_json============\n", analysis_result);
      return {"categorization_json": analysis_result}
        
    except Exception as e:
      print(f"Categorization Node Error: {e}")
      return {"categorization_json": {"error": f"Failed to organize schedule: {str(e)}"}}



def categorize_validation(state: AudioProcessingState) -> Dict[str, Any]:
    """Node 2: Vaidate the extracted JSON.
    """
    print("--- Node 2: Validate extraction")
    
    text_to_analyze = state.get("transcription_text", "")
    if not text_to_analyze or "Error during transcription" in text_to_analyze:
      return {"categorization_json": {"error": "No valid text to validate"}}

    json_to_analyze = state.get("categorization_json", "")
    print("json_to_analyze=======\n", json_to_analyze);
    if not json_to_analyze or "Error during transcription" in json_to_analyze:
      return {"categorization_json": {"error": "No valid text to validate"}} 
    
    user_payload = {
      "user_speech_transcript": text_to_analyze, 
      "extracted_json": json_to_analyze
    }
    
    try:
      # Call your existing function using a smart, large context model
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
      # This will be a standard Python dictionary containing the organized structure
      return {"categorization_json": analysis_result}
        
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
