



def transcribe_audio_text(state: AudioProcessingState) -> Dict[str, Any]:
    """Node 1: Takes raw bytes and extracts text using Whisper via Groq Client"""
    print(f"--- Node 1: Transcribing audio for {state['user_name']} ---")
    
    try:
        client = Groq() # Reads GROQ_API_KEY from environment
        
        # Call Groq's Whisper API using the raw bytes from the state
        transcription = client.audio.transcriptions.create(
            model="whisper-large-v3",
            file=(state["file_name"], state["file_bytes"])
        )
        
        # Return updates to save into the state
        return {"transcription_text": transcription.text}
        
    except Exception as e:
        print(f"Transcription Node Error: {e}")
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
