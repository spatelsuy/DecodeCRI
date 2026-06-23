import sys
import os
from supabase import create_client, Client
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(__file__))

import yaml
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi import Response
from fastapi import Request

from models import CRIDSGeneral, CRIState, A2TGeneral, AudioProcessingState
from graph import cri_ds_decodeClassify_runtime

from session_store import SESSION_STORE

from typing import Dict, List, Any, Optional
from statistics import mean
import math
from fastapi.responses import JSONResponse
import re
import json


app = FastAPI(title="IAM Agentic Maturity Platform")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----------------------------
# AGENT GEN ENTRYPOINT
# ----------------------------

load_dotenv()
url: str = os.getenv("SUPABASE_URL")
key: str = os.getenv("SUPABASE_SERVICE_KEY")

# Initialize the Supabase client
supabase: Client = create_client(url, key)

# ----------------------------
# AGENT MAIN ENTRYPOINT
# ----------------------------

@app.post("/a2t/transcribe")
async def transcribe_audio(
    user_name: str = Form(...),      # Reads form text
    file: UploadFile = File(...)     # Reads the raw webm file binary
):
    # Your transcription code here
    print("CLIENT =", user_name)
    
    try:
        audio_content = await file.read()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not read upload file: {str(e)}")
    initial_state: AudioProcessingState = {
        "user_name": user_name,
        "file_bytes": audio_content,
        "file_name": file.filename or "recording.webm",
        "transcription_text": None,
        "categorization_json": None
    }
    print("Filename =", initial_state.get("file_name"))
    try:
        # 3. Synchronously invoke the LangGraph pipeline
        # .invoke() processes all node edges sequentially and returns the final updated state dictionary
        print("INVOKING A2T GRAPH")
        final_state = graph_app.invoke(initial_state)
        print("INVOKED A2T GRAPH")
        # 4. Extract outputs from the final state dictionary and pass to frontend JSON
        return {
            "status": "success",
            "user": final_state.get("user_name"),
            "transcription": final_state.get("transcription_text"),
            "analysis": final_state.get("categorization_json")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Graph Execution Failed: {str(e)}")
    
    return {"status": "success", "user": user_name}


    
@app.get("/health_a2t")
def health():
    return {
        "status": "healthy",
        "pattern": "Manager–Worker + Planner–Executor",
        "engine": "LangGraph"
    }

@app.get("/a2t/health_a2t")
def health():
    return {
        "status": "healthy_a2t",
        "pattern": "Manager–Worker + Planner–Executor",
        "engine": "LangGraph"
    }
