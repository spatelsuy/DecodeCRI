
import yaml
import time
import difflib
import json
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from typing import Dict, Any
from models import AudioProcessingState
from groq_client import call_groq, call_groq_transcribe, call_groqJSON, call_groqJSONPreCheck


A2T_PRECHECK = """
You are an expert schedule‑extractor and reasoning engine.  
From the paragraph supplied by the user, identify **every distinct activity** and assign a concrete date‑time in ISO‑8601 format (YYYY‑MM‑DDTHH:mm:ss).  

When the text says “before X”, place the activity at the **latest feasible minute** that still satisfies the constraint (e.g., one minute before X).  
When only a range or no explicit time is given, pick a **reasonable midpoint** between surrounding anchored events, using everyday scheduling logic.  

**Any assumption should be context driven.**  

Assume:
- “today” = "{{CURRENT_DATE}}" format IS YYYY-MM-DD
- "time‑zone" = "{{TIMEZONE}}"

**Output must be a single JSON object with the exact key `LINGUISTIC_BLUEPRINT`.**  
The JSON must contain:
1. `overall_assumptions` – a short map of the global premises you used (reference date, today/tomorrow, time‑zone, handling of “before”, etc.).  
2. `considerations` – an array of bullet‑style notes that explain the general rules you followed while converting natural‑language constraints into timestamps.  
3. `activities` – an array of objects, each with the following fields:  
   - `activity` (string) – the verb‑noun phrase describing what is done.  
   - `time` (string) – the concrete timestamp in ISO‑8601 (`YYYY‑MM‑DDTHH:mm:ss`).  
   - `assumption` (string) – any local, **context‑driven** assumption you had to make for this entry (e.g., “chosen as midpoint between 10 am and 1 pm”).  
   - `reasoning` (string) – a short narrative of how you derived the time from the paragraph.  
   - `why_time_selected` (string) – why the exact minute you chose satisfies the user’s constraints.

**Do not add any extra keys or explanatory text outside the JSON.**  
If the paragraph contains no recognizable activity, return an empty `activities` array but still include the top‑level keys.

"""

A2T_PROMPT = """
You are an intelligent assistant that converts raw spoken text into structured personal organization data.
INSTRUCTIONS FOR READING THE INPUT PAYLOAD:
You will receive a JSON payload with two keys. Treat them as follows:
1. "user_speech_transcript" -> This contains the raw spoken text from the user. Use this as your source of truth.
2. "LINGUISTIC_BLUEPRINT" -> This contains the first-pass structural data that contain activities, its timestamp, the assumption, reasoning and why_time_selected.

The user_speech_transcript may be unpunctuated, conversational, fragmented, repetitive, partially incorrect due to speech-to-text errors, or code-switched (e.g. English + Hindi / Hinglish).

Today's date is: "{{CURRENT_DATE}}"
Date format: YYYY-MM-DD
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
Enrich the "title" and "context" by making it complete senetence,  however do not assume. The sentence should be from the given raw text. 

"""

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
    print("--- PROMPT 0 perform precheck and extract activities ---")
    precheck_result = {}
    DEFAULT_TIMEZONE = "UTC"
    user_tz = state.get("user_timezone") or DEFAULT_TIMEZONE
    try:
        tzinfo = ZoneInfo(user_tz)
    except ZoneInfoNotFoundError:
        log.warning("Invalid timezone %s – falling back to %s", user_tz, DEFAULT_TIMEZONE)
        tzinfo = ZoneInfo(DEFAULT_TIMEZONE)
        user_tz = DEFAULT_TIMEZONE    

    client_time = state.get("client_time", datetime.now(tzinfo).strftime("%Y-%m-%d"))
    text_to_analyze = state.get("transcription_text", "").strip()
    if not text_to_analyze or "Error during precheck" in text_to_analyze:
        return {"categorization_json": {"error": "No valid text to analyze"}}

    user_payload_precheck = {"user_speech_transcript": text_to_analyze}
    final_prompt_precheck = (
        A2T_PRECHECK
        .replace("{{CURRENT_DATE}}", client_time)
        .replace("{{TIMEZONE}}", user_tz)
    )    
    try:
      raw_result = call_groqJSONPreCheck(
        system_prompt=final_prompt_precheck,
        user_payload=user_payload_precheck,
        model="openai/gpt-oss-120b"
      )
      if not isinstance(raw_result, dict):
          log.error("LLM returned non‑dict: %r", raw_result)
          precheck_result = {}
      else:
          precheck_result = raw_result
      print("\n===============PROMPT 0 precheck_json============\n", precheck_result);
    except Exception as e:
      print(f"preheck Node Error: {e}")
      precheck_result = {}
    
    print("--- PROMPT 1 (extracting activities) ---")
    user_payload = {
        "user_speech_transcript": text_to_analyze, 
        "LINGUISTIC_BLUEPRINT": precheck_result
    }
    
    try:
      # Call your existing function using a smart, large context model
      final_prompt = A2T_PROMPT.replace('{{CURRENT_DATE}}', client_time)
      analysis_result = call_groqJSON(
        system_prompt=final_prompt,
        user_payload=user_payload,
        model="openai/gpt-oss-120b"
      )
      # This will be a standard Python dictionary containing the organized structure
      print("\n===============PROMPT 1 categorization_json============\n", analysis_result);
      return {"categorization_json": analysis_result}
        
    except Exception as e:
      print(f"Categorization Node Error: {e}")
      return {"categorization_json": {"error": f"Failed to organize schedule: {str(e)}"}}


def categorize_validation(state: AudioProcessingState) -> Dict[str, Any]:
    print("--- PROMPT 2: Validate extraction-----")
    
    text_to_analyze = state.get("transcription_text", "")
    if not text_to_analyze or "Error during transcription" in text_to_analyze:
      return {"categorization_json": {"error": "No valid text to validate"}}

    json_to_analyze = state.get("categorization_json", "")
    #print("json_to_analyze=======\n", json_to_analyze);
    if not json_to_analyze or "Error during transcription" in json_to_analyze:
      return {"categorization_json": {"error": "No valid text to validate"}} 


    DEFAULT_TIMEZONE = "UTC"
    user_tz = state.get("user_timezone") or DEFAULT_TIMEZONE

    user_payload = {
      "user_speech_transcript": text_to_analyze, 
      "extracted_json": json_to_analyze
    }
    
    try:
      # Call your existing function using a smart, large context model
      #today_date = datetime.today().strftime('%Y-%m-%d')
      today_date = datetime.now(ZoneInfo(user_tz)).strftime('%Y-%m-%d')
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
      print("\n===============PROMPT 1 validated_json============\n", analysis_result)
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
