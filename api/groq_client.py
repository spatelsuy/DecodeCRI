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
