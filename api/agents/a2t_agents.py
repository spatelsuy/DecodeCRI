
import yaml
import time
from datetime import datetime
from typing import Dict, Any
from models import AudioProcessingState
from groq_client import call_groq, call_groq_transcribe, call_groqJSON


A2T_PROMPT = """
You are an intelligent assistant that converts raw spoken text (unpunctuated, 
conversational and possibly code-switched (e.g., Hinglish)) into structured personal organization data.

Today's date is: "{{CURRENT_DATE}}". Format is YYYY-MM-DD.

Your task is to extract and categorize information into:
1. tasks       – things the user needs to do
2. events      – scheduled activities with a time or date
3. reminders   – time-bound alerts or deadlines
4. notes       – background context, not directly actionable. contextual information that supports a task or event but is not itself an action.

RULES:
1. ATOMIC INTENTS: One intent = one item. Split multi-action or run-on speech into separate array elements.
2. TIME ANCHORING: Resolve absolute and relative time expressions to strict ISO-8601 strings using Today's Date as your anchor. For vague spoken times (e.g., "evening", "after lunch"), use logical default times (e.g., 18:00:00, 14:00:00). 
3. EXPLICIT LINKING: Link dependent or contextual items by placing the exact `title` string of the parent item into the `related_to` field.
4. MISSING VALUES: For any required schema field where data is completely missing or unspecified in the speech, set that specific field value to `null`. Do not invent or assume data.
5. TEMPORAL CONTEXT INHERITANCE: Spoken speech sets a time anchor once and applies it implicitly to subsequent statements. If a specific day (e.g., "Tomorrow") is established at the beginning of the transcript, all subsequent tasks, events, and reminders in that stream inherit that same date context unless the user explicitly shifts to a new day. 
6. STRICT OUTPUT: Return ONLY a valid JSON object. No markdown wrappers (e.g., do not use ```json), no conversational filler, and no text outside the JSON object.

Return this exact JSON structure:
{
  "extracted_on": "{{CURRENT_DATE}}",
  "tasks":     [],
  "events":    [],
  "reminders": [],
  "notes":     []
}

For "tasks" and "events", use this schema:
{
  "title": "short action label or meeting name",
  "time": "normalized ISO-8601 string, or null",
  "priority": "high | medium | low",
  "related_to": "title of related item, or null",
  "context": "brief reason or detail, or null"
}

For "reminders", use this distinct schema to prevent generic placeholders:
{
  "reminder_action": "The text or task the user needs to be alerted about",
  "trigger_time": "normalized ISO-8601 string",
  "related_to": "title of the parent task/event this reminder alerts for, or null"
}

For "notes", use this schema:
{
  "content": "The text of the note or context background",
  "related_to": "title of the task or event this note supports, or null"
}
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
