
import yaml
import time
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

10. DEDUPLICATION
Do not create duplicate items unless the user clearly expresses separate intents.

11. CODE-SWITCHED / NATURAL SPEECH
Understand Hinglish and mixed-language input. Ignore filler words and ASR noise unless they change the meaning. Interpret intent conservatively.

---

OUTPUT FORMAT

{
  "extracted_on": "{{CURRENT_DATE}}",
  "tasks": [],
  "events": [],
  "reminders": [],
  "notes": []
}

Schema for tasks, events, reminders:
{
  "title": "short action-oriented label",
  "time": "ISO-8601 string or null",
  "priority": "high | medium | low",
  "is_deadline": true | false,
  "related_to": "exact title of related item or null",
  "context": "brief supporting detail or null"
}

Schema for notes:
{
  "title": "short summary",
  "time": null,
  "priority": "low",
  "is_deadline": false,
  "related_to": "exact title of related item or null",
  "context": "full note detail"
}

Titles must be concise and intent-driven. Preserve the user's real meaning. Store supporting detail in context or notes, not in the title.

Now process the spoken text and return only the final JSON object.
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
      return {"categorization_json": analysis_result}
        
    except Exception as e:
      print(f"Categorization Node Error: {e}")
      return {"categorization_json": {"error": f"Failed to organize schedule: {str(e)}"}}
