import os
import requests
import yaml
from dotenv import load_dotenv
from typing import Dict, Any

load_dotenv()

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

#model="mixtral-8x7b-32768"
def call_groq(system_prompt: str, user_payload: Dict[str, Any], model="llama-3.1-8b-instant"):
    GROQ_API_KEY = os.getenv("PROMPT_GROQ_KEY")
    if not GROQ_API_KEY:
        raise RuntimeError("PROMPT_GROQ_KEY not found in environment variables")
    
    user_prompt = yaml.dump(user_payload, sort_keys=False)
    print("\nMODEL === ", model)
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0,
        "max_tokens": 2048,
        "top_p": 0.1
    }

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    
    response = requests.post(
        GROQ_API_URL,
        headers=headers,
        json=payload,
        timeout=60
    )

    if response.status_code != 200:
        raise Exception(f"Groq API error: {response.text}")

    raw_output = response.json()["choices"][0]["message"]["content"]
    cleaned = raw_output.replace("```yaml", "").replace("```", "").strip()

    parsed = yaml.safe_load(cleaned)
    #print("\nPARSED Output=", parsed);

    if not isinstance(parsed, dict):
        raise Exception("LLM did not return valid YAML")

    return parsed


# The endpoint for Groq's transcriptions follows the OpenAI structure
GROQ_TRANSCRIPTION_URL = "https://api.groq.com/openai/v1/audio/transcriptions"

def call_groq_transcribe(file_bytes: bytes, file_name: str = "recording.webm", model: str = "whisper-large-v3") -> str:
    GROQ_API_KEY = os.getenv("PROMPT_GROQ_KEY")
    if not GROQ_API_KEY:
        raise RuntimeError("PROMPT_GROQ_KEY not found in environment variables")

    print("\nTRANSCRIPTION MODEL === ", model)
    data = {
        "model": model,
        "temperature": "0.0", # Groq expects a string or float representation
        "response_format": "json"
    }

    files = {
        "file": (file_name, file_bytes, "audio/webm")
    }
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}"
    }

    response = requests.post(
        GROQ_TRANSCRIPTION_URL,
        headers=headers,
        data=data,
        files=files,
        timeout=60
    )

    if response.status_code != 200:
        raise Exception(f"Groq Transcription API error: {response.text}")

    result = response.json()
    return result.get("text", "").strip()


def call_groqJSON(system_prompt: str, user_payload: Dict[str, Any], model="llama-3.1-8b-instant"):
    GROQ_API_KEY = os.getenv("PROMPT_GROQ_KEY")
    if not GROQ_API_KEY:
        raise RuntimeError("PROMPT_GROQ_KEY not found in environment variables")
        
    # 1. Convert the user input payload to a JSON string
    user_prompt = json.dumps(user_payload, indent=2)
    print("\nMODEL === ", model)
    
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0,
        "max_tokens": 2048,
        "top_p": 0.1,
        # 2. Force the Groq API engine to return a valid JSON object structure
        "response_format": { "type": "json_object" } 
    }
    
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    
    response = requests.post(
        GROQ_API_URL,
        headers=headers,
        json=payload,
        timeout=60
    )
    
    if response.status_code != 200:
        raise Exception(f"Groq API error: {response.text}")
        
    # 3. Read the raw text response from the LLM
    raw_output = response.json()["choices"][0]["message"]["content"].strip()
    
    # 4. Clean up Markdown blocks if the model mistakenly included them
    cleaned = raw_output.replace("```json", "").replace("```", "").strip()
    
    try:
        # 5. Parse the raw string directly into a Python dictionary using native JSON
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        raise Exception("LLM did not return valid JSON syntax")
        
    if not isinstance(parsed, dict):
        raise Exception("LLM did not return a valid JSON object map")
        
    return parsed




