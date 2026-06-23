
import yaml
import time
from typing import Dict, Any
from models import AudioProcessingState
from groq_client import call_groq, call_groq_transcribe


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
        
    # Craft a strict system prompt that instructs the LLM to output YAML
    # that your call_groq function can parse into a structured dictionary.
    system_prompt = (
        "You are an expert personal organizer and scheduling AI assistant.\n"
        "Analyze the user speech transcript to extract all past, present, and future tasks.\n"
        "Your response must be exclusively formatted as a valid YAML block.\n"
        "Do not include any chat formatting, introductory text, or markdown outside the block.\n\n"
        "The YAML structure must match this exact blueprint schema:\n"
        "summary: A brief high-level description of the user's update.\n"
        "primary_mood: The emotional tone of the speaker (e.g., Busy, Stressed, Relaxed, Productive).\n"
        "activities:\n"
        "  - task: Description of the specific action or event.\n"
        "    timeframe: When this occurs (e.g., Tomorrow, Today, Over the weekend, Next week).\n"
        "    category: The domain of the task (e.g., Healthcare, Family, Social, Work, Personal).\n"
        "    is_future: True if it is an upcoming reminder, False if it is a completed past event.\n"
        "    priority: Priority level based on urgency (High, Medium, Low).\n"
    )
    
    user_payload = {
        "user_speech_transcript": text_to_analyze
    }
    
    try:
        # Call your existing function using a smart, large context model
        analysis_result = call_groq(
            system_prompt=system_prompt,
            user_payload=user_payload,
            model="llama-3.1-70b-versatile"
        )
        
        # This will be a standard Python dictionary containing the organized structure
        return {"categorization_json": analysis_result}
        
    except Exception as e:
        print(f"Categorization Node Error: {e}")
        return {"categorization_json": {"error": f"Failed to organize schedule: {str(e)}"}}
