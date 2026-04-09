import yaml
import time
from typing import Dict, Any
from models import CRIState
from groq_client import call_groq
from session_store import SESSION_STORE

# ----------------------------
# SYSTEM PROMPTS (Shortened)
# ----------------------------
CRI_DS_INTERPRETATION = """
Dummy
"""

CRI_DS_CLASSIFY = """
Dummy
"""

CRI_DS_VALIDATE = """
Dummy
"""


# ----------------------------
# Stage - 1 (Prompt 1) - Interpret the DS and response guide
# ----------------------------
def get_ds_decode(state: CRIState) -> CRIState:
    try:
        print("INTERPRET THE DS AND ITS RESPONSE GUIDE PROMOT is \n", state.CRI_DS_INTERPRETATION)
        cri_ds_yaml = yaml.safe_load(state.cri_ds_statement)
        cri_block = cri_ds_yaml["cri_ds_statement"]
        diagnostic_statement = cri_block["diagnostic_statement"]
        response_guide = cri_block["ResponseGuide"]
        
        result = call_groq(
            system_prompt=state.CRI_DS_INTERPRETATION,
            user_payload={  "diagonesic_statement": diagnostic_statement, 
                            "response_guide": response_guide},
            model="openai/gpt-oss-120b"
        ) 
        state.cri_interpretation = result
        print("Result = ")
        print(state.cri_interpretation)
        return state
        
    except Exception as e:
        print("Unable interpret the DS. Error is: ", str(e))
        raise HTTPException(status_code=500, detail=str(e))     


# -----------------------------------
# Stage - 2 (deterministic rules)
# Consider respose from prompt-1 and apply deterministic rules to get classification
# This classification is considered as code_classification
# -----------------------------------
def generate_code_classification(state: CRIState) -> CRIState:
    """
    Generate code_classification from Prompt 1 understanding output.
    Applies deterministic characteristic-based rules only.
    Returns classification with source tags for Prompt 2.
    """
    print("Apply rules before prompt-2 to get code_classification")
    # ── Extract characteristics safely ──────────────────────────
    understanding = state.cri_interpretation
    chars = (
        understanding
        .get("understanding", {}).get("control_characteristics", {})
    )
    print("########")
    raw_layer = chars.get("implementation_layer", {})
    raw_mode  = chars.get("execution_mode", {})
    raw_freq  = chars.get("frequency", {})

    # Handle both flat string and evolved dict format
    # Flat:    "implementation_layer": "policy+process"
    # Evolved: "implementation_layer": {"value": "policy+process", ...}
    layer = (
        raw_layer.get("value", "")
        if isinstance(raw_layer, dict)
        else str(raw_layer)
    ).lower()

    mode = (
        raw_mode.get("value", "")
        if isinstance(raw_mode, dict)
        else str(raw_mode)
    ).lower()

    freq = (
        raw_freq.get("value", "")
        if isinstance(raw_freq, dict)
        else str(raw_freq)
    ).lower()

    # ── Helper ───────────────────────────────────────────────────
    def layer_contains(*keywords):
        return any(kw in layer for kw in keywords)

    # ── GovernanceIntent ─────────────────────────────────────────
    # Code fires TRUE only when layer explicitly contains
    # policy or process.
    # If layer is technology-only — code cannot decide —
    # LLM must read DS text for implied governance.
    if layer_contains("policy", "process"):
        governance = {
            "value":  True,
            "source": "code",
            "basis":  (
                f"implementation_layer '{layer}' contains "
                f"policy or process — GovernanceIntent rule fires."
            )
        }
    else:
        governance = {
            "value":  None,
            "source": "unknown",
            "basis":  (
                f"implementation_layer '{layer}' does not contain "
                f"policy or process — LLM must check DS text for "
                f"implied governance or policy requirement."
            )
        }

    # ── TechnicalEnforcement ─────────────────────────────────────
    # Code decides fully — rule fires directly from layer value.
    if layer_contains("technology"):
        tech = {
            "value":  True,
            "source": "code",
            "basis":  (
                f"implementation_layer '{layer}' contains "
                f"technology — TechnicalEnforcement rule fires."
            )
        }
    else:
        tech = {
            "value":  False,
            "source": "code",
            "basis":  (
                f"implementation_layer '{layer}' does not contain "
                f"technology — TechnicalEnforcement = FALSE."
            )
        }

    # ── Monitoring ───────────────────────────────────────────────
    # Code fires TRUE only for continuous frequency.
    # Periodic or event-driven — code cannot decide —
    # LLM must read DS for detection/visibility language.
    if freq == "continuous":
        monitoring = {
            "value":  True,
            "source": "code",
            "basis":  (
                "frequency = continuous — "
                "Monitoring rule fires."
            )
        }
    else:
        monitoring = {
            "value":  None,
            "source": "unknown",
            "basis":  (
                f"frequency = '{freq}' — code cannot determine "
                f"Monitoring. LLM must check DS text for "
                f"detection, logging, or visibility language."
            )
        }

    # ── Automation ───────────────────────────────────────────────
    # Code decides fully — rule fires directly from mode value.
    if mode == "automated":
        automation = {
            "value":  True,
            "source": "code",
            "basis":  (
                "execution_mode = automated — "
                "Automation rule fires."
            )
        }
    else:
        automation = {
            "value":  False,
            "source": "code",
            "basis":  (
                f"execution_mode = '{mode}' — "
                f"Automation = FALSE."
            )
        }

    # ── Lifecycle ────────────────────────────────────────────────
    # Code fires TRUE when layer contains process or policy.
    # Technology-only layer — code cannot decide —
    # LLM must read DS for ongoing management language.
    if layer_contains("policy", "process"):
        lifecycle = {
            "value":  True,
            "source": "code",
            "basis":  (
                f"implementation_layer '{layer}' contains "
                f"policy or process — Lifecycle rule fires."
            )
        }
    else:
        lifecycle = {
            "value":  None,
            "source": "unknown",
            "basis":  (
                f"implementation_layer '{layer}' does not contain "
                f"policy or process — LLM must check DS text for "
                f"ongoing management, periodic review, or "
                f"recurring activity language."
            )
        }

    # ── StrategicIntent ──────────────────────────────────────────
    # Never set by code at this stage.
    # Requires all other five dimensions to be resolved first.
    # Computed in Code Layer B after Prompt 2 output.
    strategic = {
        "value":  None,
        "source": "pending",
        "basis":  (
            "StrategicIntent resolved after all other "
            "dimensions confirmed by LLM in Prompt 2."
        )
    }

    # ── Assemble output ──────────────────────────────────────────
    print("GovernanceIntent", governance)
    print("TechnicalEnforcement", tech)
    print("Monitoring", monitoring)
    print("Automation", automation)
    print("Lifecycle", lifecycle)
    print("StrategicIntent", strategic)
    
    code_classification =  {
        "code_classification": {
            "GovernanceIntent":     governance,
            "TechnicalEnforcement": tech,
            "Monitoring":           monitoring,
            "Automation":           automation,
            "Lifecycle":            lifecycle,
            "StrategicIntent":      strategic
        }
    }
    state.code_classification = code_classification
    return state


# -----------------------------------
# Stage - 3 (promot-2)
# Now call prompt-2 to get classification by providing code_classification, prompt-1 result (interpritation/understanding), DS and response guide
# This classification is considered as code_classification
# -----------------------------------
def get_ds_classify(state: CRIState) -> CRIState:
    try:
        print("Get DS Classify from Decode - prompt2")
        cri_ds_yaml = yaml.safe_load(state.cri_ds_statement)
        cri_block = cri_ds_yaml["cri_ds_statement"]
        diagnostic_statement = cri_block["diagnostic_statement"]
        response_guide = cri_block["ResponseGuide"]
        
        result = call_groq(
            system_prompt=state.CRI_DS_CLASSIFY,
            user_payload={"diagonesic_statement": diagnostic_statement, 
                            "response_guide": response_guide,
                            "understanding": state.cri_interpretation, 
                            "code_classification": state.code_classification
                        },
            model="openai/gpt-oss-120b"
        )
  
        state.ds_classification = result
        print(state.ds_classification)
                
        return state
        
    except Exception as e:
        print("Unable classify the DS. Error is: ", str(e))
        raise HTTPException(status_code=500, detail=str(e)) 


# -----------------------------------
# Stage - 4.1 
# Apply hard rules after prompt-2, this will also build prompt-3 input "validated_classification_input"
# -----------------------------------
def apply_hard_rules(state: CRIState) -> CRIState:
    """
    Apply deterministic hard rules after Prompt 2 output.
    Returns corrected classification and list of adjustments.
    """
    print("APPLY HARD RULES NOW")    
    understanding = state.cri_interpretation
    classification = state.ds_classification
    
    chars = (
        understanding.get("understanding", {}).get("control_characteristics", {})
    )

    raw_freq  = chars.get("frequency", {})
    raw_layer = chars.get("implementation_layer", {})

    freq = (
        raw_freq.get("value", "")
        if isinstance(raw_freq, dict)
        else str(raw_freq)
    ).lower()

    layer = (
        raw_layer.get("value", "")
        if isinstance(raw_layer, dict)
        else str(raw_layer)
    ).lower()

    # Work on a copy
    dims = classification["Classification"]

    # Extract just the boolean values for rule checking
    c = {k: v["value"] for k, v in dims.items()}    
    adj = []

    def record(component, old, new, rule):
        adj.append({
            "component":      component,
            "previous_value": old,
            "updated_value":  new,
            "reason":         rule
        })


    # ── Hard rule 1 ──────────────────────────────────────────────
    # Automation = TRUE → TechnicalEnforcement MUST = TRUE
    if c["Automation"] and not c["TechnicalEnforcement"]:
        record(
            "TechnicalEnforcement", False, True,
            "Hard rule: Automation=TRUE requires "
            "TechnicalEnforcement=TRUE."
        )
        c["TechnicalEnforcement"] = True

    # ── Hard rule 2 ──────────────────────────────────────────────
    # GovernanceIntent = TRUE → Lifecycle MUST = TRUE
    if c["GovernanceIntent"] and not c["Lifecycle"]:
        record(
            "Lifecycle", False, True,
            "Hard rule: GovernanceIntent=TRUE requires "
            "Lifecycle=TRUE."
        )
        c["Lifecycle"] = True

    # ── Hard rule 3 ──────────────────────────────────────────────
    # implementation_layer contains policy or process
    # → Lifecycle MUST = TRUE
    if any(kw in layer for kw in ["policy", "process"]):
        if not c["Lifecycle"]:
            record(
                "Lifecycle", False, True,
                f"Hard rule: implementation_layer '{layer}' "
                f"contains policy or process — "
                f"Lifecycle=TRUE."
            )
            c["Lifecycle"] = True

    # ── Hard rule 4 ──────────────────────────────────────────────
    # frequency = periodic → Lifecycle MUST = TRUE
    if freq == "periodic" and not c["Lifecycle"]:
        record(
            "Lifecycle", False, True,
            "Hard rule: frequency=periodic requires "
            "Lifecycle=TRUE."
        )
        c["Lifecycle"] = True

    # ── Hard rule 5 ──────────────────────────────────────────────
    # StrategicIntent = TRUE only if ALL others FALSE
    others = [
        "GovernanceIntent", "TechnicalEnforcement",
        "Monitoring", "Automation", "Lifecycle"
    ]
    if any(c[d] for d in others) and c["StrategicIntent"]:
        record(
            "StrategicIntent", True, False,
            "Hard rule: StrategicIntent=TRUE only if all "
            "other dimensions are FALSE."
        )
        c["StrategicIntent"] = False

    print("VALIDATED=", c)
    print("ADJUSTMENTS = ", adj)
    validated_classification_input = build_prompt3_input(state.ds_classification, c, adj)
    print("VALIDATED CLASSIFICATION INPUT= ", validated_classification_input)
    state.validated_classification_input = validated_classification_input    
    return state

# -----------------------------------
# Stage - 4.2
# This create "validated_classification_input" with section prompt2_output, validated_classification, and code_adjustments
# -----------------------------------
def build_prompt3_input(prompt2_output: dict, validated: dict, adjustments: list) -> dict:
    """
    Merge Prompt 2 output, hard rule validated classification,
    and adjustments into a single classification object
    for Prompt 3.
    """
    return {
        "classification": {
            # What Prompt 2 classified with justifications
            "prompt2_output": prompt2_output["Classification"],

            # What the classification looks like after
            # hard rules applied by code
            "validated_classification": validated,

            # What hard rules changed — Prompt 3 must not
            # re-apply these
            "code_adjustments": adjustments
        }
    }


def get_ds_validate_classify(state: CRIState) -> CRIState:
    try:
        print("Get Validate Classification")

        cri_ds_yaml = yaml.safe_load(state.cri_ds_statement)
        cri_block = cri_ds_yaml["cri_ds_statement"]
        diagnostic_statement = cri_block["diagnostic_statement"]
        response_guide = cri_block["ResponseGuide"]
        classification = state.ds_classification
        #print("\ninterim classification = \n", classification)
        time.sleep(60) 
        result = call_groq(
            system_prompt=state.CRI_DS_VALIDATE,
            user_payload={  "diagonesic_statement": diagnostic_statement, 
                            "response_guide": response_guide, 
                            "Classification": state.validated_classification_input},
            model="openai/gpt-oss-120b"
        ) 
        print("Received Final Classification")
        
        state.ds_classification_validated = result
        print(result)
        #print(state.ds_classification_validated)        
        return state

    except Exception as e:
        print("Unable to validate classification. Error is: ", str(e))
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


def guard_hard_rule_reversals_OLD(state: CRIState ) -> CRIState:
    prompt3_output = state.ds_classification_validated
    code_adjustments = state.validated_classification_input["classification"]["code_adjustments"]

    """
    Safety net after Prompt 3 runs.
    
    Ensures Prompt 3 has not reversed any hard rule
    corrections made by Code Layer B (apply_hard_rules).
    
    If Prompt 3 reversed a hard rule correction:
    - Restores the correct value
    - Removes the bad Prompt 3 adjustment
    - Documents the restoration
    
    If code_adjustments is empty — nothing to guard,
    returns prompt3_output unchanged.
    
    Args:
        prompt3_output:   Raw output dict from Prompt 3
        code_adjustments: List of adjustments from 
                          apply_hard_rules()
    
    Returns:
        Final verified output dict
        
        
    return {
        "classification": {
            # What Prompt 2 classified with justifications
            "prompt2_output": prompt2_output["Classification"],

            # What the classification looks like after
            # hard rules applied by code
            "validated_classification": validated,

            # What hard rules changed — Prompt 3 must not
            # re-apply these
            "code_adjustments": adjustments
        }        
    """

    # Nothing to guard if no hard rules fired
    if not code_adjustments:
        print("code adjustment is empty")
        #return prompt3_output
        return state

    # Work on copies — do not mutate inputs
    validated  = dict(prompt3_output["validated_classification"])
    p3_adj     = list(prompt3_output.get("adjustments", []))
    restored   = []

    for code_adj in code_adjustments:
        component  = code_adj["component"]
        hard_value = code_adj["updated_value"]
        current    = validated.get(component)

        # Check if Prompt 3 reversed the hard rule correction
        if current != hard_value:

            # Restore the hard rule value
            validated[component] = hard_value

            # Remove the bad Prompt 3 adjustment for this component
            p3_adj = [
                a for a in p3_adj
                if a["component"] != component
            ]

            # Document the restoration
            restored.append({
                "component":      component,
                "previous_value": current,
                "updated_value":  hard_value,
                "reason":         (
                    f"System restored — Prompt 3 reversed a "
                    f"hard rule correction. "
                    f"Hard rule: {code_adj['reason']}"
                )
            })

    # Rebuild final output
    final = dict(prompt3_output)
    final["validated_classification"] = validated
    final["adjustments"] = p3_adj + restored

    # Update validation_summary if restorations were made
    if restored:
        final["validation_summary"] = dict(
            prompt3_output.get("validation_summary", {})
        )
        final["validation_summary"]["adjustments_made"] = True
        final["validation_summary"]["system_restored"]  = True
        final["validation_summary"]["restored_count"]   = len(restored)

    state.ds_classification_validated = final
    print("GUARD_hard_rule_reversals = ", state.ds_classification_validated)
    return state
    
    
    
def guard_hard_rule_reversals(state: CRIState ) -> CRIState:


    prompt3_output = state.ds_classification_validated
    code_adjustments = state.validated_classification_input["classification"]["code_adjustments"]
    understanding = state.cri_interpretation
    prompt2_output = state.validated_classification_input["classification"]["prompt2_output"]
    
    """
    Extended guard — checks both:
    1. Values corrected by Code B (existing behaviour)
    2. Values that hard rules require regardless of 
       whether Code B fired
    """
    validated = dict(prompt3_output["validated_classification"])
    p3_adj    = list(prompt3_output.get("adjustments", []))
    restored  = []

    # ── Guard 1: Protect Code B corrections ──────────────────
    for code_adj in code_adjustments:
        component  = code_adj["component"]
        hard_value = code_adj["updated_value"]
        current    = validated.get(component)
        if current != hard_value:
            validated[component] = hard_value
            p3_adj = [a for a in p3_adj 
                      if a["component"] != component]
            restored.append({
                "component":      component,
                "previous_value": current,
                "updated_value":  hard_value,
                "reason": f"System restored — Prompt 3 reversed "
                          f"Code B correction. Rule: "
                          f"{code_adj['reason']}"
            })

    # ── Guard 2: Re-run hard rules against Prompt 3 output ───
    # This catches reversals of values Code B did not need
    # to correct (they were already correct from Prompt 2)
    chars = (understanding
             .get("understanding", {})
             .get("control_characteristics", {}))

    raw_layer = chars.get("implementation_layer", {})
    raw_freq  = chars.get("frequency", {})

    layer = (raw_layer.get("value","")
             if isinstance(raw_layer, dict)
             else str(raw_layer)).lower()

    freq = (raw_freq.get("value","")
            if isinstance(raw_freq, dict)
            else str(raw_freq)).lower()

    def restore(component, required_value, rule):
        if validated.get(component) != required_value:
            old = validated[component]
            validated[component] = required_value
            # Remove bad Prompt 3 adjustment
            nonlocal p3_adj
            p3_adj = [a for a in p3_adj
                      if a["component"] != component]
            restored.append({
                "component":      component,
                "previous_value": old,
                "updated_value":  required_value,
                "reason": f"System restored — {rule}"
            })

    # Re-apply all five hard rules
    if validated.get("Automation"):
        restore("TechnicalEnforcement", True,
                "Automation=TRUE requires TechnicalEnforcement=TRUE")

    if validated.get("GovernanceIntent"):
        restore("Lifecycle", True,
                "GovernanceIntent=TRUE requires Lifecycle=TRUE")

    if "policy" in layer or "process" in layer:
        restore("Lifecycle", True,
                f"implementation_layer '{layer}' requires Lifecycle=TRUE")

    if freq == "periodic":
        restore("Lifecycle", True,
                "frequency=periodic requires Lifecycle=TRUE")

    others = ["GovernanceIntent","TechnicalEnforcement",
              "Monitoring","Automation","Lifecycle"]
    if any(validated.get(d) for d in others):
        restore("StrategicIntent", False,
                "StrategicIntent=FALSE — other dimensions are TRUE")

    # ── Rebuild output ────────────────────────────────────────
    final = dict(prompt3_output)
    final["validated_classification"] = validated
    final["adjustments"] = p3_adj + restored

    if restored:
        final["validation_summary"] = dict(
            prompt3_output.get("validation_summary", {}))
        final["validation_summary"]["adjustments_made"] = True
        final["validation_summary"]["system_restored"]  = True
        final["validation_summary"]["restored_count"]   = len(restored)

    state.ds_classification_validated = final
    print("GUARD_hard_rule_reversals = ", state.ds_classification_validated)
    return state   
