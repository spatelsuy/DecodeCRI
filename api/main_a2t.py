import sys
import os
from supabase import create_client, Client
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(__file__))

import yaml
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi import Response
from fastapi import Request

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
    
@app.get("/health_a2t")
def health():
    return {
        "status": "healthy",
        "pattern": "Manager–Worker + Planner–Executor",
        "engine": "LangGraph"
    }
