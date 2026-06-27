
import yaml
import time
from datetime import datetime
from typing import Dict, Any
from models import AudioProcessingState
from groq_client import call_groq, call_groq_transcribe, call_groqJSON


A2T_PROMPT = """
You are an intelligent assistant that converts raw spoken text into 
structured personal organization data.

Today's date is: "{{CURRENT_DATE}}"

Your task is to extract and categorize information into:

1. tasks       – things the user needs to do (no fixed time)
2. events      – scheduled activities with a time or date
3. reminders   – time-bound alerts or deadlines
4. notes       – background context, not directly actionable

Instructions:
- Break input into meaningful individual items.
- Extract and normalize time references using today's date as anchor. Today's date format is YYYY-MM-DD.
  (e.g., "tomorrow 12:00 PM", "Saturday evening").
- Identify relationships between items
  (e.g., "buy gifts" is related to "marriage party").
- If a sentence contains multiple actions, split into separate items.
- If something is unclear, extract it as-is — do NOT invent details.
- Keep output concise. Return ONLY valid JSON, no explanation.

Return this exact JSON structure:

{
  "extracted_on": "{{CURRENT_DATE}}",
  "tasks":     [],
  "events":    [],
  "reminders": [],
  "shopping":  [],
  "notes":     []
}

Each item follows this schema:
{
  "title":      "short action label",
  "time":       "normalized time string, or null",
  "priority":   "high | medium | low",
  "is_deadline": true | false,
  "related_to": "title of related item, or null",
  "context":    "brief reason or detail, or null"
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
      final_prompt = A2T_PROMPT.replace('{{CURRENT_DATE}}', today_str)
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
