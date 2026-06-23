
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
    """Node 2: Takes the text string and uses an LLM to build structured JSON"""
    print("--- Node 2: Categorizing text content ---")
    
    text_to_analyze = state.get("transcription_text", "")
    if not text_to_analyze or "Error during transcription" in text_to_analyze:
        return {"categorization_json": {"error": "No valid text to categorize"}}
        
    try:
        # Initialize an LLM model capable of tool calling/structured outputs
        llm = ChatGroq(model="llama3-70b-8192", temperature=0)
        
        # Bind the Pydantic model to force the LLM to output perfect structured JSON
        structured_llm = llm.with_structured_output(TextCategorization)
        
        # Run the structured analysis
        prompt = f"Analyze the following transcribed user speech text: '{text_to_analyze}'"
        result: TextCategorization = structured_llm.invoke(prompt)
        
        # Convert the Pydantic model response directly into a dictionary for the state
        return {"categorization_json": result.model_dump()}
        
    except Exception as e:
        print(f"Categorization Node Error: {e}")
        return {"categorization_json": {"error": f"LLM categorization failed: {str(e)}"}}
