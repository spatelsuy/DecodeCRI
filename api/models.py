from pydantic import BaseModel
from typing import List, Dict, Any, Optional


class IAMState(BaseModel):
    user_inputs: Dict[str, Any]

    gen_output: Optional[Dict[str, Any]] = None
    domain_output: Optional[Dict[str, Any]] = None

    validation_status: Optional[str] = None
    confidence_level: Optional[str] = None


class GENContract(BaseModel):
    enforced_maturity_ceiling: int
    domain_caps: Dict[str, int] = {}
    material_gaps: List[str] = []
    ceiling_rationale: List[str] = []
    confidence_level: str | None = None


class GENState(BaseModel):
    user_inputs: dict
    engine_output: dict | None = None
    gen_output: Optional[Dict[str, Any]] = None
    gen_output_remediation: Optional[Dict[str, Any]] = None
    gen_output_analyst: Optional[Dict[str, Any]] = None
    gen_output_executive: Optional[Dict[str, Any]] = None
    gen_contract: GENContract | None = None
    validation_status: str | None = None

class DomainState(BaseModel):
    gen_contract: GENContract = None
    domain_name: str
    question_id: str
    questions: Dict[str, Dict] = {}

    question_results: Dict[str, Dict] = {}
    question_results_narrative_executive: Dict[str, Dict] = {}
    question_results_narrative_analyst: Dict[str, Dict] = {}
    question_results_narrative_remediation: Dict[str, Dict] = {}
    final_maturity: Dict | None = None
    
class CRIState(BaseModel):
    cri_ds_statement: str | None = None
    ds_classification: Optional[Dict[str, Any]] = None
    evidence_requirement: Optional[Dict[str, Any]] = None
    cri_interpretation: Optional[Dict[str, Any]] = None
    cri_regalignment: Optional[Dict[str, Any]] = None
    
    # Stage 1 - Interpreter
    cri_interpretation1: Optional[Dict[str, Any]] = None

    # Stage 2 - Classification (raw)
    ds_classification2: Optional[Dict[str, Any]] = None

    # Stage 3 - Validation (final classification)
    ds_classification_validated: Optional[Dict[str, Any]] = None
    

class CRIDSGeneral(BaseModel):
    user_name: str
    cri_ds_statement: str  # YAML string

class AgentRequestGeneral(BaseModel):
    user_name: str
    general_question: str  # YAML string

class AgentRequestDomain(BaseModel):
    user_name: str
    domain_question: str  # YAML string

class AgentRequestResult(BaseModel):
    user_name: str
    domain_result: str
