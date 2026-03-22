import os
import yaml
from typing import Dict, Any
from models import IAMState, GENState, GENContract, CRIState
from groq_client import call_groq
from session_store import SESSION_STORE

# ----------------------------
# SYSTEM PROMPTS (Shortened)
# ----------------------------

def get_ds_decode(state: CRIState) -> CRIState:
    try:
        print("Get DS Decode")
        cri_ds_yaml = yaml.safe_load(state.cri_ds_statement)
        cri_block = cri_ds_yaml["cri_ds_statement"]
        diagnostic_statement = cri_block["diagnostic_statement"]
        response_guide = cri_block["ResponseGuide"]
        CRI_DS_INTERPRETATION = os.getenv("CRI_DS_INTERPRETATION")
       
        result = call_groq(
            system_prompt=CRI_DS_INTERPRETATION,
            user_payload={  "diagonesic_statement": diagnostic_statement, 
                            "response_guide": response_guide},
            model="openai/gpt-oss-120b"
        ) 
        print("Received Interpritation Result")
        state.cri_interpretation1 = result
        print(state.cri_interpretation1)
        return state
        
    except Exception as e:
        print("Unable interpret the DS. Error is: ", str(e))
        raise HTTPException(status_code=500, detail=str(e))     

def get_ds_classify(state: CRIState) -> CRIState:
    try:
        print("Get DS Classify from Decode")
        cri_ds_yaml = yaml.safe_load(state.cri_ds_statement)
        cri_block = cri_ds_yaml["cri_ds_statement"]
        diagnostic_statement = cri_block["diagnostic_statement"]
        response_guide = cri_block["ResponseGuide"]
        CRI_DS_CLASSIFY = os.getenv("CRI_DS_CLASSIFY")
        
        result = call_groq(
            system_prompt=CRI_DS_CLASSIFY,
            user_payload={"diagonesic_statement": diagnostic_statement, 
                            "response_guide": response_guide,
                        "understanding": state.cri_interpretation1
                        },
            model="openai/gpt-oss-120b"
        )
        state.ds_classification2 = result
        print(state.ds_classification2)
        return state
        
    except Exception as e:
        print("Unable classify the DS. Error is: ", str(e))
        raise HTTPException(status_code=500, detail=str(e)) 

def get_ds_validate_classify(state: CRIState) -> CRIState:
    try:
        print("Get Validate Classification")

        cri_ds_yaml = yaml.safe_load(state.cri_ds_statement)
        cri_block = cri_ds_yaml["cri_ds_statement"]
        diagnostic_statement = cri_block["diagnostic_statement"]
        response_guide = cri_block["ResponseGuide"]
        classification = state.ds_classification2
        print("\ninterim classification = \n", classification)
        CRI_DS_VALIDATE = os.getenv("CRI_DS_VALIDATE")
        result = call_groq(
            system_prompt=CRI_DS_VALIDATE,
            user_payload={  "diagonesic_statement": diagnostic_statement, 
                            "response_guide": response_guide, 
                            "Classification": state.ds_classification2},
            model="openai/gpt-oss-120b"
        ) 
        print("Received Final Classification")
        state.ds_classification_validated = result
        print(state.ds_classification_validated)        
        return state

    except Exception as e:
        print("Unable to validate classification. Error is: ", str(e))
        raise HTTPException(status_code=500, detail=str(e))     

def get_ds_regalignment(state: CRIState) -> CRIState:
    try:
        cri_ds_yaml = yaml.safe_load(state.cri_ds_statement)
        print("1")
        cri_block = cri_ds_yaml["cri_ds_statement"]
        print("2")
        diagnostic_statement = cri_block["diagnostic_statement"]
        print("3")
        response_guide = cri_block["ResponseGuide"]
        print("4")
        eee = cri_block["EEE"]
        print("5")
        fin = cri_block["FIN"]
        print("6")
        targetRegulation = cri_block["Regulations"]
        print("7")
        result = call_groq(
            system_prompt=CRI_DS_REG_ALIGNMENT,
            user_payload={  "diagonesic_statement": diagnostic_statement, 
                            "response_guide": response_guide, 
                            "EEE": eee, 
                            "FIN": fin, 
                            "target_regulation": targetRegulation},
            model="openai/gpt-oss-120b"
        )
        print("Raw Evidence Result:")
        if isinstance(result, str):
            import json
            result = json.loads(result)
            print("JSON Result is\n", result);

        if not isinstance(result, dict):
            raise ValueError(f"Expected dict from LLM, got {type(result)}")
        
        state.cri_regalignment = result
        
        return state
    except Exception as e:
        print("Unable get reg alignment data. Error is: ", str(e))
        with open("debug_input.json", "w", encoding="utf-8") as f:
            import json
            json.dump({
                "diagonesic_statement": diagnostic_statement,
                "response_guide": response_guide,
                "EEE": eee,
                "FIN": fin,
                "target_regulation": targetRegulation
            }, f, indent=2)
        raise HTTPException(status_code=500, detail=str(e)) 

def get_ds_interpret(state: CRIState) -> CRIState:
    try:
        cri_ds_yaml = yaml.safe_load(state.cri_ds_statement)
        cri_block = cri_ds_yaml["cri_ds_statement"]
        diagnostic_statement = cri_block["diagnostic_statement"]
        response_guide = cri_block["ResponseGuide"]
        eee = cri_block["EEE"]
        targetRegulation = cri_block["Regulations"]
        
        result = call_groq(
            system_prompt=CRI_DS_INTERPRET,
            user_payload={"diagonesic_statement": diagnostic_statement, "response_guide": response_guide, "EEE": eee, "target_regulation": targetRegulation},
            model="openai/gpt-oss-120b"
        ) 
        print("Raw Evidence Result:")
        state.cri_interpretation = result
        #print("Evidence requirement stored in state:\n", state.cri_interpretation)
        
        return state
    except Exception as e:
        print("Unable interpret the DS. Error is: ", str(e))
        raise HTTPException(status_code=500, detail=str(e)) 

def get_requireevidence_list(state: CRIState) -> CRIState:
    try:
        cri_ds_yaml = yaml.safe_load(state.cri_ds_statement)
        cri_block = cri_ds_yaml["cri_ds_statement"]
        diagnostic_statement = cri_block["diagnostic_statement"]
        response_guide = cri_block["ResponseGuide"]
        eee = cri_block["EEE"]
        targetRegulation = cri_block["Regulations"]
        
        result = call_groq(
            system_prompt=CRI_DS_EVIDENCE,
            user_payload={"diagonesic_statement": diagnostic_statement, "response_guide": response_guide, "EEE": eee, "target_regulation": targetRegulation},
            model="openai/gpt-oss-120b"
        ) 
        print("Raw Evidence Result:")
        state.evidence_requirement = result
        #print("Evidence requirement stored in state:\n", state.evidence_requirement)
        
        return state
    except Exception as e:
        print("Unable to get evidence list. Error is: ", str(e))
        raise HTTPException(status_code=500, detail=str(e)) 

def validate_input_agent(state: CRIState) -> CRIState:
    try:
        error_flag = False
        cri_ds_yaml = yaml.safe_load(state.cri_ds_statement)
        cri_block = cri_ds_yaml["cri_ds_statement"]
        
        # Check required fields
        required_fields = ["profile_id", "diagnostic_statement", "ResponseGuide", "EEE", "FIN"]
        
        for field in required_fields:
            if field not in cri_block or not cri_block[field]:
                print(f"ERROR: Missing required field '{field}'")
                error_flag = True
            else:
                print("exist: ", field)

        if not error_flag:
            print("All required fields exist.")
            #print("Profile ID =", cri_block["profile_id"])
            #print("Diagnostic Statement =", cri_block["diagnostic_statement"])        
        
        return state
    except Exception as e:
        print("Unable to validate input. Error is: ", str(e))
        raise HTTPException(status_code=500, detail=str(e))  

def get_classification_agent(state: CRIState) -> CRIState:
    try:
        print("LLM connection to get classification")
        cri_ds_yaml = yaml.safe_load(state.cri_ds_statement)
        cri_block = cri_ds_yaml["cri_ds_statement"]
        diagnostic_statement = cri_block["diagnostic_statement"]
        response_guide = cri_block["ResponseGuide"]
        
        result = call_groq(
            system_prompt=CRI_DS_CLASSIFICATION,
            user_payload={"diagonesic_statement": diagnostic_statement, "response_guide": response_guide},
            model="openai/gpt-oss-120b"
        ) 
        state.ds_classification = result
        #print("Result is###", state.ds_classification)
        
        return state
    except Exception as e:
        print("Unable to get classification. Error is: ", str(e))
        raise HTTPException(status_code=500, detail=str(e))           
