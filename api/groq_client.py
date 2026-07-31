import os
import requests
import yaml
import json
from dotenv import load_dotenv
from typing import Dict, Any

load_dotenv()

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

my_strict_schema = {
    "type": "object",
    "properties": {
        "extracted_on": {
            "type": "string",
            "description": "ISO-8601 date string reflecting the anchor current date."
        },
        "tasks": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Short action-oriented label"},
                    "time": {"type": ["string", "null"], "description": "ISO-8601 string or null"},
                    "priority": {"type": "string", "enum": ["high", "medium", "low"]},
                    "is_deadline": {"type": "boolean"},
                    "related_to": {"type": ["string", "null"]},
                    "context": {"type": ["string", "null"]},
                    "source_segment": {"type": "string"},
                    "recurrence": {
                        "type": "object",
                        "properties": {
                            "is_recurring": {"type": "boolean"},
                            "frequency": {
                                "type": ["string", "null"], 
                                "description": "The cadence of repetition (daily, weekly, bi-weekly, monthly, quarterly, semi-annually, annually) or any custom interval."
                            },
                            "day_of_week": {
                                "type": ["string", "null"], 
                                "enum": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday", None],
                                "description": "Specific day if mentioned, otherwise null."
                            },
                            "start_date": {"type": ["string", "null"]},
                            "end_date": {"type": ["string", "null"]}
                        },
                        "required": ["is_recurring", "frequency", "day_of_week", "start_date", "end_date"],
                        "additionalProperties": False
                    }
                },
                "required": ["title", "time", "priority", "is_deadline", "related_to", "context", "source_segment", "recurrence"],
                "additionalProperties": False
            }
        },
        "events": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "time": {"type": ["string", "null"]},
                    "priority": {"type": "string", "enum": ["high", "medium", "low"]},
                    "is_deadline": {"type": "boolean"},
                    "related_to": {"type": ["string", "null"]},
                    "context": {"type": ["string", "null"]},
                    "source_segment": {"type": "string"},
                    "recurrence": {
                        "type": "object",
                        "properties": {
                            "is_recurring": {"type": "boolean"},
                            "frequency": {
                                "type": ["string", "null"], 
                                "description": "The cadence of repetition (daily, weekly, bi-weekly, monthly, quarterly, semi-annually, annually) or any custom interval."
                            },
                            "day_of_week": {
                                "type": ["string", "null"], 
                                # FIXED HERE: Added None to allow null output
                                "enum": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday", None],
                                "description": "Specific day if mentioned, otherwise null."
                            },
                            "start_date": {"type": ["string", "null"]},
                            "end_date": {"type": ["string", "null"]}
                        },
                        "required": ["is_recurring", "frequency", "day_of_week", "start_date", "end_date"],
                        "additionalProperties": False
                    }
                },
                "required": ["title", "time", "priority", "is_deadline", "related_to", "context", "source_segment", "recurrence"],
                "additionalProperties": False
            }
        },
        "reminders": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "time": {"type": ["string", "null"]},
                    "priority": {"type": "string", "enum": ["high", "medium", "low"]},
                    "is_deadline": {"type": "boolean"},
                    "related_to": {"type": ["string", "null"]},
                    "context": {"type": ["string", "null"]},
                    "source_segment": {"type": "string"},
                    "recurrence": {
                        "type": "object",
                        "properties": {
                            "is_recurring": {"type": "boolean"},
                            "frequency": {
                                "type": ["string", "null"], 
                                "description": "The cadence of repetition (daily, weekly, bi-weekly, monthly, quarterly, semi-annually, annually) or any custom interval."
                            },
                            "day_of_week": {
                                "type": ["string", "null"], 
                                # FIXED HERE: Added None to allow null output
                                "enum": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday", None],
                                "description": "Specific day if mentioned, otherwise null."
                            },
                            "start_date": {"type": ["string", "null"]},
                            "end_date": {"type": ["string", "null"]}
                        },
                        "required": ["is_recurring", "frequency", "day_of_week", "start_date", "end_date"],
                        "additionalProperties": False
                    }
                },
                "required": ["title", "time", "priority", "is_deadline", "related_to", "context", "source_segment", "recurrence"],
                "additionalProperties": False
            }
        },
        "notes": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "short summary"},
                    "time": {"type": ["string", "null"]},
                    "priority": {"type": "string"},
                    "is_deadline": {"type": "boolean"},
                    "related_to": {"type": ["string", "null"]},
                    "context": {"type": "string", "description": "full note detail"},
                    "source_segment": {"type": "string"}
                },
                "required": ["title", "time", "priority", "is_deadline", "related_to", "context", "source_segment"],
                "additionalProperties": False
            }
        }
    },
    "required": ["extracted_on", "tasks", "events", "reminders", "notes"],
    "additionalProperties": False
}




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
        "temperature": "0.0",
        "response_format": "verbose_json"   # <-- changed from "json"
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
    segments = result.get("segments", [])

    if not segments:
        # fallback in case API doesn't return segments for very short clips
        return result.get("text", "").strip()

    # Filter out likely-hallucinated / silence segments
    NO_SPEECH_THRESHOLD = 0.6
    LOGPROB_THRESHOLD = -1.0

    kept_text = []
    for seg in segments:
        no_speech_prob = seg.get("no_speech_prob", 0.0)
        avg_logprob = seg.get("avg_logprob", 0.0)

        if no_speech_prob > NO_SPEECH_THRESHOLD or avg_logprob < LOGPROB_THRESHOLD:
            print(f"Dropping likely hallucinated segment: '{seg.get('text','').strip()}' "
                  f"(no_speech_prob={no_speech_prob:.2f}, avg_logprob={avg_logprob:.2f})")
            continue

        kept_text.append(seg.get("text", "").strip())

    return " ".join(kept_text).strip()





def call_groq_transcribe_old(file_bytes: bytes, file_name: str = "recording.webm", model: str = "whisper-large-v3") -> str:
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
    GROQ_API_KEY = os.getenv("PROMPT_GROQ_KEY_PAID")
    #GROQ_API_KEY = os.getenv("PROMPT_GROQ_KEY")
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
        "max_tokens": 8192,
        
        # === ADD THESE TWO LINES TO SECURE OPENAI/GPT-OSS-120B ===
        "include_reasoning": False,
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "schedule_extraction_registry",
                "strict": True, 
                "schema": my_strict_schema
            }
        }        
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
    message_obj = response.json()["choices"][0]["message"]
    raw_output = message_obj.get("content", "")
    if not raw_output or raw_output.strip() == "":
        # Diagnostic print if the model returned nothing but background reasoning
        print("\n--- DEBUG ERROR ---")
        print("Groq Response JSON structure:", response.json())
        raise Exception("LLM content field came back completely empty. Check reasoning fields.")

    raw_output = raw_output.strip()
    
    # 4. Clean up Markdown blocks if the model mistakenly included them
    cleaned = raw_output.replace("```json", "").replace("```", "").strip()

    # 4b. Extreme fallback: If it wrapped JSON inside conversational filler, find the brackets
    if not cleaned.startswith("{"):
        start_idx = cleaned.find("{")
        end_idx = cleaned.rfind("}") + 1
        if start_idx != -1 and end_idx != 0:
            cleaned = cleaned[start_idx:end_idx]
    
    try:
        # 5. Parse the raw string directly into a Python dictionary using native JSON
        parsed = json.loads(cleaned)
    except json.JSONDecodeError as e:
        # === ADD THESE DIAGNOSTIC PRINTS HERE ===
        print("\n" + "="*50)
        print("CRITICAL: JSON DECODE ERROR ENCOUNTERED!")
        print(f"Error Message: {e}")
        print("="*50)
        print("EXACT RAW OUTPUT RECEIVED FROM MODEL:")
        print(raw_output)
        print("="*50)
        print("CLEANED STRING ATTEMPTED TO PARSE:")
        print(cleaned)
        print("="*50 + "\n")
        
        raise Exception(f"LLM did not return valid JSON syntax. Decode Error: {e}")
        
    if not isinstance(parsed, dict):
        raise Exception("LLM did not return a valid JSON object map")
        
    return parsed




