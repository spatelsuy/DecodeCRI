
import yaml
import time
from typing import Dict, Any
from models import AudioProcessingState
from groq_client import call_groq, call_groq_transcribe, call_groqJSON


A2T_PROMPT = """
You are an intelligent assistant that converts raw spoken text into structured personal organization data.

Your task is to extract and categorize information into:

1. tasks (things user needs to do)
2. events (scheduled activities with time/date)
3. reminders (time-bound actions)
4. shopping (items to buy)
5. notes (context or non-actionable information)

Instructions:

- Break the input into meaningful items.
- Extract time references (today, tomorrow, evening, weekend, specific times).
- Normalize time into clear descriptions (e.g., "tomorrow 12:00 PM", "today evening").
- Identify relationships between items:
  (e.g., "buy gifts" related to "marriage party")
- If a sentence contains multiple actions, split them.
- If something is unclear, still extract it but do not invent details.
- Keep output concise and structured.
- Do NOT include explanations.

Return ONLY valid JSON in the following format:

{
  "tasks": [],
  "events": [],
  "reminders": [],
  "shopping": [],
  "notes": []
}

Each item should follow this structure:
{
  "title": "...",
  "time": "... (if available)",
  "related_to": "... (optional)"
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
        analysis_result = call_groqJSON(
            system_prompt=A2T_PROMPT,
            user_payload=user_payload,
            model="openai/gpt-oss-120b"
        )
        
        # This will be a standard Python dictionary containing the organized structure
        return {"categorization_json": analysis_result}
        
    except Exception as e:
        print(f"Categorization Node Error: {e}")
        return {"categorization_json": {"error": f"Failed to organize schedule: {str(e)}"}}
