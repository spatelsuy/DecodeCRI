import os
from dotenv import load_dotenv
from supabase import create_client, Client
import yaml
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi import Response
from models import CRIDSGeneral, CRIState
from graph import cri_ds_decodeClassify_runtime
from session_store import SESSION_STORE
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

load_dotenv()
url: str = os.getenv("SUPABASE_URL")
key: str = os.getenv("SUPABASE_SERVICE_KEY")

# Initialize the Supabase client
supabase: Client = create_client(url, key)

def read_prompt_from_db(state: CRIState) -> bool:
    try:
        table_name = 'PROMPTS'
        response = (
            supabase.table(table_name)
            .select("PROMPT_NAME, PROMPT_STR")        # Only select the columns you need
            .execute()
            )
        # Perform the insert operation
        #print(response.data)
        rows = response.data
        count = len(rows)
        if count < 1:
            return False

        for row in rows:
            print("prompt name =", row['PROMPT_NAME'])
            if row['PROMPT_NAME'] == "CRI_DS_INTERPRETATION":
                state.CRI_DS_INTERPRETATION = row['PROMPT_STR']
                #print("Value of CRI_DS_INTERPRETATION = ", state.CRI_DS_INTERPRETATION)
            elif row['PROMPT_NAME'] == "CRI_DS_CLASSIFY":
                state.CRI_DS_CLASSIFY = row['PROMPT_STR']
                #print("Value of CRI_DS_CLASSIFY = ", state.CRI_DS_CLASSIFY)
            elif row['PROMPT_NAME'] == "CRI_DS_VALIDATE":
                state.CRI_DS_VALIDATE = row['PROMPT_STR']
                #print("Value of CRI_DS_VALIDATE = ", state.CRI_DS_VALIDATE)  

        return True

    except Exception as e:
        print(f"An error occurred: {e}")
        return False  



def read_from_database(ds_id: str, state: CRIState) -> bool:
    try:
        print("Reading Data from DB for ", ds_id)
        table_name = 'CRI_DECODE'
        response = (
            supabase.table(table_name)
            .select("STATE, KEY, VALUE")        # Only select the columns you need
            .eq("DS_ID", ds_id)    # Your filter from before
            .eq("STATE", "CRIState")
            .execute()
            )
        # Perform the insert operation
        #print(response.data)
        rows = response.data
        count = len(rows)
        if count < 3:
            return False

        for row in rows:
            if row['KEY'] == "INTERPRITATION":
                #print("Value of INTERPRITATION = ", row['VALUE'])
                state.cri_interpretation = row['VALUE']
            elif row['KEY'] == "CLASSIFICATION":
                #print("Value of CLASSIFICATION = ", row['VALUE'])
                state.ds_classification = row['VALUE']
            elif row['KEY'] == "VALIDATED_CLASSIFICATION":
                #print("Value of VALIDATED_CLASSIFICATION = ", row['VALUE'])
                state.ds_classification_validated = row['VALUE']  

        return True

    except Exception as e:
        print(f"An error occurred: {e}")
        return False  
        

def write_to_database(ds_id: str, state: CRIState) -> bool:
    
    print("Writing to DB")

    """
    Inserts data into a Supabase table.    
    """
    table_name = 'CRI_DECODE' # Replace with your actual table name
    data_to_insert = [
        {"DS_ID": ds_id, "STATE": "CRIState", "KEY": "INTERPRITATION", "VALUE": state["cri_interpretation"]},
        {"DS_ID": ds_id, "STATE": "CRIState", "KEY": "CODE_CLASSIFICATION", "VALUE": state["code_classification"]},
        {"DS_ID": ds_id, "STATE": "CRIState", "KEY": "CLASSIFICATION", "VALUE": state["ds_classification"]}, 
        {"DS_ID": ds_id, "STATE": "CRIState", "KEY": "VALIDATED_CLASSIFICATION_INPUT", "VALUE": state["validated_classification_input"]}, 
        {"DS_ID": ds_id, "STATE": "CRIState", "KEY": "VALIDATED_CLASSIFICATION", "VALUE": state["ds_classification_validated"]}
    ]

    try:
        # Perform the insert operation
        response = supabase.table(table_name).insert(data_to_insert).execute()
        print("Data inserted successfully:")
        #print(response.data)
        return True

    except Exception as e:
        print(f"An error occurred: {e}")
        return False


# ----------------------------
# AGENT MAIN ENTRYPOINT
# ----------------------------

@app.post("/cri_ds_decodeClassify")
def assess(request: CRIDSGeneral):
    try:
        cri_ds_data = yaml.safe_load(request.cri_ds_statement)
        #print("\nCRI_DS_DATA DECODE=\n", cri_ds_data)
        if "cri_ds_statement" in cri_ds_data:
            cri_ds = cri_ds_data["cri_ds_statement"]
            #print("\n###cri_ds_statement=###\n", cri_ds)
        
        ds_id = cri_ds_data["cri_ds_statement"]["profile_id"]
        state = CRIState(cri_ds_statement = request.cri_ds_statement)
        
        
        result = read_from_database(ds_id, state)
        if result == True:
            print("Data already exist in DB")
            print("INTERPRITATION = ", state.cri_interpretation)
            print("CLASSIFICATION = ", state.ds_classification)
            print("VALIDATED CLASSIFICATION = ", state.ds_classification_validated)
            return JSONResponse({
                "cri_interpretation": state.cri_interpretation, 
                "ds_classification": state.ds_classification,
                "cri_validated_classification": state.ds_classification_validated
            })
        else:
            print("NEED TO CONNECT LLM")
            read_prompt_from_db(state)
        
        
        result = cri_ds_decodeClassify_runtime.invoke(state)
        
        #print("\nCRI INTERPRITATION :\n", json.dumps(result["cri_interpretation"], indent=2))
        #print("\nCRI CLASSIFICATION :\n", json.dumps(result["ds_classification"], indent=2))
        #print("\nCRI VALIDATED CLASSIFICATION :\n", json.dumps(result["ds_classification_validated"], indent=2))
        
        parsed = yaml.safe_load(state.cri_ds_statement)
        ds_id = parsed["cri_ds_statement"]["profile_id"]
        
        write_to_database(ds_id, result)

        return JSONResponse({
            "cri_interpretation": result["cri_interpretation"], 
            "ds_classification": result["ds_classification"],
            "cri_validated_classification": result["ds_classification_validated"]
        })        
        
    except Exception as e:
        print("Error in getting CRI DS Decode & Classify\n", str(e))
        raise HTTPException(status_code=500, detail=str(e))

    
@app.get("/health")
def health():
    return {
        "status": "healthy",
        "pattern": "Manager–Worker + Planner–Executor",
        "engine": "LangGraph"
    }

@app.get("/api/health")
def health():
    return {
        "status": "API healthy",
        "pattern": "Manager–Worker + Planner–Executor",
        "engine": "LangGraph"
    }

