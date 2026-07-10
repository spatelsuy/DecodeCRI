
import yaml
import time
import difflib
import json
from datetime import datetime
from typing import Dict, Any
from models import AudioProcessingState
from groq_client import call_groq, call_groq_transcribe, call_groqJSON


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

5. TIME NORMALIZATION
Resolve all time expressions against "{{CURRENT_DATE}}". Normalize to ISO-8601 datetime strings when date and/or time can be determined. For vague time expressions:
- morning → 09:00 | afternoon → 15:00 | after lunch → 14:00 | evening → 18:00 | night → 21:00

6. CATEGORY DISCIPLINE
- tasks: actionable to-dos
- events: meetings, appointments, scheduled activities
- reminders: triggered by "remind me", "don't let me forget", "remember to", or any time-bound alert
- notes: context, background, or supporting detail not directly actionable

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
    """Node 2: Extracts scheduling details and tasks from the transcript
    using the existing call_groq utility.
    """
    print("--- Node 2: Parsing activity schedule using call_groq ---")
    
    text_to_analyze = state.get("transcription_text", "")
    if not text_to_analyze or "Error during transcription" in text_to_analyze:
        return {"categorization_json": {"error": "No valid text to analyze"}}
    
    user_payload = {
        "user_speech_transcript": text_to_analyze
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


