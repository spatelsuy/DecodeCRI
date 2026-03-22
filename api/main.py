import yaml
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi import Response

from typing import Dict, List, Any, Optional
from statistics import mean
import math
from fastapi.responses import JSONResponse
import re
import json


CONFIDENCE_MAP = {
    "High": 3,
    "Medium": 2,
    "Low": 1
}

REVERSE_CONFIDENCE_MAP = {
    3: "High",
    2: "Medium",
    1: "Low"
}

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
    
@app.get("/api/health")
def health():
    return {
        "status": "API healthy",
        "pattern": "Manager–Worker + Planner–Executor",
        "engine": "LangGraph"
    }


@app.get("/health")
def health():
    return {
        "status": "Normal healthy",
        "pattern": "Manager–Worker + Planner–Executor",
        "engine": "LangGraph"
    }
