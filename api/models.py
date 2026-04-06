from pydantic import BaseModel
from typing import List, Dict, Any, Optional


class CRIDSGeneral(BaseModel):
    user_name: str
    cri_ds_statement: str  # YAML string

    
class CRIState(BaseModel):
    #keep CRI DS
    cri_ds_statement: str | None = None
    
    # Stage 1
    #The direct interpretation of DS and Response Guide
    cri_interpretation: Optional[Dict[str, Any]] = None   
    #Deterministic rule applied on interpretation data
    code_classification: Optional[Dict[str, Any]] = None  

    # Stage 2 - Classification (raw)
    ds_classification: Optional[Dict[str, Any]] = None
    validated_classification_input: Optional[Dict[str, Any]] = None

    # Stage 3 - Validation (final classification)
    ds_classification_validated: Optional[Dict[str, Any]] = None
