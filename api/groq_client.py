import os
import requests
import yaml
import json
from dotenv import load_dotenv
from typing import Dict, List, Any
import copy

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
                            "day_of_month": {
                              "type": ["number", "null"],
                              "description": "Only set when frequency is 'monthly' and the recurrence is based on a fixed day-of-month number (e.g. '25th of every month'). Leave null for weekday-based monthly patterns (use week_of_month/day_of_week instead) or non-monthly frequencies."
                            },                            
                            "week_of_month": {
                                "type": ["number", "null"],
                                "enum": [1, 2, 3, 4, 5, -1, None],
                                "description": "Only set when frequency is 'monthly' and the recurrence is based on a weekday (e.g. 'last Thursday', '2nd Monday', '5th Friday'). Leave as null in every other case."
                            },
                            "start_date": {"type": ["string", "null"]},
                            "end_date": {"type": ["string", "null"]}
                        },
                        "required": ["is_recurring", "frequency", "day_of_week", "day_of_month", "week_of_month", "start_date", "end_date"],
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
                            "day_of_month": {
                              "type": ["number", "null"],
                              "description": "Only set when frequency is 'monthly' and the recurrence is based on a fixed day-of-month number (e.g. '25th of every month'). Leave null for weekday-based monthly patterns (use week_of_month/day_of_week instead) or non-monthly frequencies."
                            },                              
                            "week_of_month": {
                                "type": ["number", "null"],
                                "enum": [1, 2, 3, 4, 5, -1, None],
                                "description": "Only set when frequency is 'monthly' and the recurrence is based on a weekday (e.g. 'last Thursday', '2nd Monday', '5th Friday'). Leave as null in every other case."
                            },                         
                            "start_date": {"type": ["string", "null"]},
                            "end_date": {"type": ["string", "null"]}
                        },
                        "required": ["is_recurring", "frequency", "day_of_week", "day_of_month", "week_of_month", "start_date", "end_date"],
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
                            "day_of_month": {
                              "type": ["number", "null"],
                              "description": "Only set when frequency is 'monthly' and the recurrence is based on a fixed day-of-month number (e.g. '25th of every month'). Leave null for weekday-based monthly patterns (use week_of_month/day_of_week instead) or non-monthly frequencies."
                            },                              
                            "week_of_month": {
                                "type": ["number", "null"],
                                "enum": [1, 2, 3, 4, 5, -1, None],
                                "description": "Only set when frequency is 'monthly' and the recurrence is based on a weekday (e.g. 'last Thursday', '2nd Monday', '5th Friday'). Leave as null in every other case."
                            },                            
                            "start_date": {"type": ["string", "null"]},
                            "end_date": {"type": ["string", "null"]}
                        },
                        "required": ["is_recurring", "frequency", "day_of_week", "day_of_month", "week_of_month", "start_date", "end_date"],
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

my_linguistic_response_schema = {
  "title": "Linguistic Blueprint – Schedule Extraction",
  "type": "object",
  "required": ["LINGUISTIC_BLUEPRINT"],
  "additionalProperties": False,
  "properties": {
    "LINGUISTIC_BLUEPRINT": {
      "type": "object",
      "required": ["overall_assumptions", "considerations", "activities"],
      "additionalProperties": False,
      "properties": {
        "overall_assumptions": {
          "type": "object",
          "description": "Global premises used for all activities.",
          "required": [
            "reference_date",
            "today",
            "tomorrow",
            "time_zone",
            "implicit_times"
          ],
          "additionalProperties": False,
          "properties": {
            "reference_date": {
              "type": "string",
              "format": "date",
              "example": "2026-10-11"
            },
            "today": {
              "type": "string",
              "format": "date",
              "example": "2026-10-11"
            },
            "tomorrow": {
              "type": "string",
              "format": "date",
              "example": "2026-10-12"
            },
            "time_zone": {
              "type": "string",
              "description": "Time‑zone context (unspecified → local).",
              "example": "unspecified (assumed local)"
            },
            "implicit_times": {
              "type": "string",
              "description": "Rule for handling “before X” and vague times.",
              "example": "When the paragraph says “before X”, schedule at the latest feasible minute before X; when no exact time is given, use a reasonable midpoint between surrounding events."
            }
          }
        },

        "considerations": {
          "type": "array",
          "description": "General methodological notes.",
          "items": {
            "type": "string"
          },
          "minItems": 1,
          "example": [
            "All times are expressed in ISO‑8601 (YYYY‑MM‑DDTHH:mm:ss).",
            "Activities described as “before X” are placed one minute prior to X."
          ]
        },

        "activities": {
          "type": "array",
          "description": "List of extracted activities with full reasoning.",
          "items": {
            "type": "object",
            "required": [
              "activity",
              "time",
              "assumption",
              "reasoning",
              "why_time_selected"
            ],
            "additionalProperties": False,
            "properties": {
              "activity": {
                "type": "string",
                "description": "Verb‑noun phrase describing the action."
              },
              "time": {
                "type": "string",
                "format": "date-time",
                "description": "Concrete timestamp in ISO‑8601 (YYYY‑MM‑DDTHH:mm:ss).",
                "example": "2026-10-11T09:59:00"
              },
              "assumption": {
                "type": "string",
                "description": "Context‑driven assumption made to place the activity."
              },
              "reasoning": {
                "type": "string",
                "description": "Short narrative of how the time was derived from the paragraph."
              },
              "why_time_selected": {
                "type": "string",
                "description": "Why this exact minute satisfies the constraints."
              }
            }
          },
          "example": [
            {
              "activity": "Take bath",
              "time": "2026-10-11T09:59:00",
              "assumption": "The bath must finish before 10 am; scheduled at the latest feasible minute.",
              "reasoning": "Paragraph says \"complete taking bath before 10am\" – choose 09:59:00.",
              "why_time_selected": "Meets the ‘before 10am’ requirement while leaving a minute buffer."
            }
          ]
        }
      }
    }
  }
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


HALLUCINATION_PHRASES = {
    "thank you", "thank you.", "thanks for watching", "please subscribe",
    "bye", "bye bye", "see you next time", "thanks", "okay", "hi",
}

def is_likely_hallucination_phrase(text: str) -> bool:
    cleaned = text.strip().lower().strip(".,!?")
    return cleaned in HALLUCINATION_PHRASES

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
        "response_format": "verbose_json",   # <-- changed from "json"
        "language": "en"
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
    NO_SPEECH_THRESHOLD = 0.3
    LOGPROB_THRESHOLD = -1.0
    TEMPERATURE_THRESHOLD = 0.0  # if Whisper needed to raise temperature at all, treat with suspicion
    
    kept_text = []
    for seg in segments:
        print("THE SEGMENT=")
        print(json.dumps(seg, indent=2))
        no_speech_prob = seg.get("no_speech_prob", 0.0)
        avg_logprob = seg.get("avg_logprob", 0.0)
        temperature = seg.get("temperature", 0.0)
        text = seg.get("text", "").strip()
        
        is_filler = is_likely_hallucination_phrase(text)
        if (is_filler and no_speech_prob > 0.15) or no_speech_prob > NO_SPEECH_THRESHOLD or avg_logprob < LOGPROB_THRESHOLD or temperature > TEMPERATURE_THRESHOLD:
            print(f"Dropping: '{text}' (filler={is_filler}, no_speech_prob={no_speech_prob:.3f}, avg_logprob={avg_logprob:.2f})")
            continue

        kept_text.append(text)
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


def call_groqJSON(system_prompt: str, user_payload: Dict[str, Any], model="openai/gpt-oss-120b", reasoning_effort: str = "medium"):
    GROQ_API_KEY = os.getenv("PROMPT_GROQ_KEY_PAID")
    if not GROQ_API_KEY:
        raise RuntimeError("PROMPT_GROQ_KEY_PAID not found in environment variables")

    user_prompt = json.dumps(user_payload, indent=2)
    print("\nMODEL === ", model, " | reasoning_effort =", reasoning_effort)

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0,
        "max_tokens": 8192,
        "include_reasoning": False,
        "reasoning_effort": reasoning_effort,  # left at Groq's default — nothing changes unless you opt to test "low"
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

    response = requests.post(GROQ_API_URL, headers=headers, json=payload, timeout=60)

    # Log usage on every call — tells us how much of max_tokens reasoning is actually consuming,
    # so we have real data instead of guessing next time something goes wrong.
    try:
        usage = response.json().get("usage")
        if usage:
            print("USAGE:", json.dumps(usage))
    except Exception:
        pass

    def _repair(parsed: dict) -> dict:
        # Guarantee the shape client-side — don't rely on the model always
        # remembering to include empty categories.
        parsed.setdefault("tasks", [])
        parsed.setdefault("events", [])
        parsed.setdefault("reminders", [])
        parsed.setdefault("notes", [])
        return parsed

    if response.status_code != 200:
        try:
            print("Status code=", response.status_code)
            err_obj = response.json()
            failed_gen = err_obj.get("error", {}).get("failed_generation")
            if failed_gen:
                salvaged = json.loads(failed_gen)
                print("⚠️ Schema validation failed — salvaged from failed_generation instead of discarding.")
                return _repair(salvaged)
        except Exception as salvage_err:
            print("Salvage attempt also failed:", salvage_err)

        raise Exception(f"Groq API error: {response.text}")

    message_obj = response.json()["choices"][0]["message"]
    raw_output = message_obj.get("content", "")
    if not raw_output or raw_output.strip() == "":
        print("\n--- DEBUG ERROR ---")
        print("Groq Response JSON structure:", response.json())
        raise Exception("LLM content field came back completely empty. Check reasoning fields.")
    raw_output = raw_output.strip()

    cleaned = raw_output.replace("```json", "").replace("```", "").strip()
    if not cleaned.startswith("{"):
        start_idx = cleaned.find("{")
        end_idx = cleaned.rfind("}") + 1
        if start_idx != -1 and end_idx != 0:
            cleaned = cleaned[start_idx:end_idx]

    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError as e:
        print("\n" + "="*50)
        print("CRITICAL: JSON DECODE ERROR ENCOUNTERED!")
        print(f"Error Message: {e}")
        print("EXACT RAW OUTPUT RECEIVED FROM MODEL:")
        print(raw_output)
        print("="*50 + "\n")
        raise Exception(f"LLM did not return valid JSON syntax. Decode Error: {e}")

    if not isinstance(parsed, dict):
        raise Exception("LLM did not return a valid JSON object map")

    print("Returning repair one")
    return _repair(parsed)


def _repairPreCheck(parsed: Dict[str, Any]) -> Dict[str, Any]:
    parsed = copy.deepcopy(parsed)
    blueprint = parsed.setdefault("LINGUISTIC_BLUEPRINT", {})

    overall = blueprint.setdefault("overall_assumptions", {})
    overall.setdefault("reference_date", "1970-01-01")   # fallback ISO‑date
    overall.setdefault("today", "1970-01-01")
    overall.setdefault("tomorrow", "1970-01-02")
    overall.setdefault("time_zone", "unspecified (assumed local)")
    overall.setdefault(
        "implicit_times",
        "When the paragraph says “before X”, schedule at the latest feasible minute before X; "
        "when no exact time is given, use a reasonable midpoint between surrounding events."
    )

    blueprint.setdefault("considerations", [])
    activities: List[Dict[str, Any]] = blueprint.setdefault("activities", [])
    required_activity_keys = [
        "activity",
        "time",
        "assumption",
        "reasoning",
        "why_time_selected",
    ]

    for act in activities:
        if not isinstance(act, dict):
            continue
        for key in required_activity_keys:
            act.setdefault(key, "")
        if not act["time"]:
            act["time"] = "1970-01-01T00:00:00"
    return parsed

def call_groqJSONPreCheck(system_prompt: str, user_payload: Dict[str, Any], model="openai/gpt-oss-120b", reasoning_effort: str = "medium"):
    GROQ_API_KEY = os.getenv("PROMPT_GROQ_KEY_PAID")
    if not GROQ_API_KEY:
        raise RuntimeError("PROMPT_GROQ_KEY_PAID not found in environment variables")

    user_prompt = json.dumps(user_payload, indent=2)
    print("\nMODEL === ", model, " | reasoning_effort =", reasoning_effort)
    print(system_prompt)
    print(user_prompt)
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0,
        "max_tokens": 8192,
        "include_reasoning": False,
        "reasoning_effort": reasoning_effort,  # left at Groq's default — nothing changes unless you opt to test "low"
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "schedule_extraction_registry",
                "strict": True,
                "schema": my_linguistic_response_schema
            }
        }
    }

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    response = requests.post(GROQ_API_URL, headers=headers, json=payload, timeout=60)
    # Log usage on every call
    try:
        usage = response.json().get("usage")
        if usage:
            print("USAGE:", json.dumps(usage))
    except Exception:
        pass

    if response.status_code != 200:
        try:
            print("Status code=", response.status_code)
            err_obj = response.json()
            failed_gen = err_obj.get("error", {}).get("failed_generation")
            if failed_gen:
                salvaged = json.loads(failed_gen)
                print("precheck Schema validation failed — salvaged from failed_generation instead of discarding.")
                return _repairPreCheck(salvaged)
        except Exception as salvage_err:
            print("precheck salvage attempt also failed:", salvage_err)
        raise Exception(f"Groq API error: {response.text}")

    message_obj = response.json()["choices"][0]["message"]
    raw_output = message_obj.get("content", "")
    if not raw_output or raw_output.strip() == "":
        print("\n--- PRECHECK DEBUG ERROR ---")
        print("Groq Response JSON structure:", response.json())
        raise Exception("Precheck LLM content field came back completely empty. Check reasoning fields.")
    raw_output = raw_output.strip()

    cleaned = raw_output.replace("```json", "").replace("```", "").strip()
    if not cleaned.startswith("{"):
        start_idx = cleaned.find("{")
        end_idx = cleaned.rfind("}") + 1
        if start_idx != -1 and end_idx != 0:
            cleaned = cleaned[start_idx:end_idx]

    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError as e:
        print("\n" + "="*50)
        print("PRECHECK - CRITICAL: JSON DECODE ERROR ENCOUNTERED!")
        print(f"Error Message: {e}")
        print("PRECHECK - EXACT RAW OUTPUT RECEIVED FROM MODEL:")
        print(raw_output)
        print("="*50 + "\n")
        raise Exception(f"PRECHECK - LLM did not return valid JSON syntax. Decode Error: {e}")

    if not isinstance(parsed, dict):
        raise Exception("PRECHECK - LLM did not return a valid JSON object map")
    print("Precheck Returning repair one")
    return _repairPreCheck(parsed)
