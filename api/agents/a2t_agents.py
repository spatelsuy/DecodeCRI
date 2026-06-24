
import yaml
import time
from typing import Dict, Any
from models import AudioProcessingState
from groq_client import call_groq, call_groq_transcribe, call_groqJSON


A2T_PROMPT = """
You are a personal planning assistant. Analyze the following text and extract all events, tasks, and commitments mentioned. Categorize each item into one of these categories:

- Work – meetings, professional tasks, work-related activities
- Personal – family responsibilities, personal obligations
- Health – medical appointments, wellness activities
- Errand – shopping, purchases, logistical tasks
- Social – parties, gatherings, celebrations

For each item, extract:
- Title (short label)
- Category
- Day/timing (Today / Tomorrow / Weekend / Specific time if mentioned)
- Priority or urgency (High / Medium / Low)
- Any dependencies or deadlines (e.g. "must be done before X")

Return the output as a structured JSON array.
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
