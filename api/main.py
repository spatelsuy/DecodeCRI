import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

import yaml
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi import Response

from models import AgentRequestGeneral, AgentRequestDomain, AgentRequestResult, IAMState, GENState, DomainState, GENContract, CRIDSGeneral, CRIState

from graph import genagent_runtime
from graph import domainagent_runtime
from graph import cri_ds_runtime
from graph import cri_ds_evd_runtime
from graph import cri_ds_interpret_runtime
from graph import cri_ds_regalignment_runtime
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

def eval_trigger(trig: str, gen_state: Dict[str, bool]) -> bool:
    """
    Evaluate trigger expression dynamically
    Fixed to handle Python boolean literals
    """
    # Replace gen.Qx with corresponding boolean from gen_state
    def replace_gen_ref(match):
        q_key = match.group(1)  # Get Q1, Q2, etc.
        return str(gen_state.get(q_key, False)).lower()
    
    # Replace all gen.Qx references
    expr = re.sub(r'gen\.(Q\d+)', replace_gen_ref, trig)
    
    # Convert JavaScript boolean literals to Python boolean literals
    expr = expr.replace('true', 'True').replace('false', 'False')
    expr = expr.replace('&&', ' and ').replace('||', ' or ')
    
    try:
        # Use eval with restricted globals for safety
        # Provide True and False in the evaluation context
        result = eval(expr, {"__builtins__": {}, "True": True, "False": False}, {})
        return bool(result)
    except Exception as e:
        print(f"Error evaluating expression '{expr}': {e}")
        return False


def execute_policy_engine(gen_state: Dict[str, bool], policy: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Main policy engine function - equivalent to JS executePolicyEngine
    """
    try:
        # policy is already parsed YAML/dictionary
        material_gaps = []
        ceiling_rationale = []
        enforced_maturity_ceiling = 5  # start with max maturity
        domain_caps = {}
        triggered_rules = {}
        
        # 3. Process governance rules
        rules = policy.get('rules', {}).get('governance_rules', {})
        
        for rule_name, rule in rules.items():
            triggered = False
            triggers = rule.get('triggers', [])
            
            if isinstance(triggers, list):
                for trig in triggers:
                    if eval_trigger(trig, gen_state):
                        triggered = True
                        material_gaps.append(f"Rule triggered: {rule_name} -> {rule.get('description', '')}")
                        ceiling_rationale.append(f"{rule_name}: Triggered. Ceiling reduced to {rule.get('ceiling', 5)}")
                        triggered_rules[rule_name] = True
                        enforced_maturity_ceiling = min(enforced_maturity_ceiling, rule.get('ceiling', 5))
        
        # 4. Compute domain caps
        domains = policy.get('rules', {}).get('domain_caps', {})
        
        for domain_name, domain_info in domains.items():
            domain_ceiling = 5  # max
            governed_by = domain_info.get('governed_by', [])
            
            for rule_name in governed_by:
                if triggered_rules.get(rule_name):
                    rule_ceiling = rules.get(rule_name, {}).get('ceiling', 5)
                    domain_ceiling = min(domain_ceiling, rule_ceiling)
            
            domain_caps[domain_name] = domain_ceiling
        
        # 5. Determine confidence level
        gaps_count = len(material_gaps)
        if gaps_count > 5:
            confidence_level = "Low"
        elif gaps_count > 2:
            confidence_level = "Medium"
        else:
            confidence_level = "High"
        
        print("###enforced_maturity_ceiling", enforced_maturity_ceiling)
        return {
            "enforcedMaturityCeiling": enforced_maturity_ceiling,
            "domainCaps": domain_caps,
            "materialGaps": material_gaps,
            "ceilingRationale": ceiling_rationale,
            "confidenceLevel": confidence_level
        }
        
    except Exception as err:
        print(f"Policy Engine Error: {err}")
        import traceback
        traceback.print_exc()
        return None
        

def build_gen_state(all_answers: Dict[str, bool]) -> Dict[str, bool]:
    """
    Convert question answers to genState format
    Equivalent to JS buildGenState function
    """
    gen_state = {}
    
    for i in range(1, 19):
        key = f"Q{i}"
        # Assuming all_answers has keys like "Q1", "Q2", etc.
        gen_state[key] = all_answers.get(key, False)
    
    return gen_state
    

# ----------------------------
# AGENT MAIN ENTRYPOINT
# ----------------------------
@app.post("/cri_ds_regulatoralignment")
def assess(request: CRIDSGeneral):
    try:
        print("Getting EVIDENCE List")
        cri_ds_data = yaml.safe_load(request.cri_ds_statement)
        #print("\nCRI_DS_DATA=\n", cri_ds_data)
        if "cri_ds_statement" in cri_ds_data:
            cri_ds = cri_ds_data["cri_ds_statement"]
            #print("\n###cri_ds_statement=###\n", cri_ds)
        print("\nCRI_DS_Statement\n", cri_ds_data["cri_ds_statement"]["diagnostic_statement"])
        print("\nResponse Guide\n", cri_ds_data["cri_ds_statement"]["ResponseGuide"])
        print("\nEEE\n", cri_ds_data["cri_ds_statement"]["EEE"])
        print("\FIN\n", cri_ds_data["cri_ds_statement"]["FIN"])
        print("\Regulations\n", cri_ds_data["cri_ds_statement"]["Regulations"])

        state = CRIState(cri_ds_statement = request.cri_ds_statement)
        result = cri_ds_regalignment_runtime.invoke(state)

        #print("\nResult is=", result["ds_classification"]["Classification"])
        #print("\nCRI Regulation Alignment:\n", yaml.dump(result["cri_regalignment"], sort_keys=False))
        print("\nCRI Regulation Alignment:\n", json.dumps(result["cri_regalignment"], indent=2))

        return JSONResponse({
            "reg_alignment": result["cri_regalignment"]
        })
    except Exception as e:
        print("Error in getting Regulation Alignment\n", str(e))
        raise HTTPException(status_code=500, detail=str(e))
    

@app.post("/cri_ds_interpret")
def assess(request: CRIDSGeneral):
    try:
        print("Getting EVIDENCE List")
        cri_ds_data = yaml.safe_load(request.cri_ds_statement)
        #print("\nCRI_DS_DATA=\n", cri_ds_data)
        if "cri_ds_statement" in cri_ds_data:
            cri_ds = cri_ds_data["cri_ds_statement"]
            #print("\n###cri_ds_statement=###\n", cri_ds)
        print("\nCRI_DS_Statement\n", cri_ds_data["cri_ds_statement"]["diagnostic_statement"])
        print("\nResponse Guide\n", cri_ds_data["cri_ds_statement"]["ResponseGuide"])
        print("\nEEE\n", cri_ds_data["cri_ds_statement"]["EEE"])

        state = CRIState(cri_ds_statement = request.cri_ds_statement)
        result = cri_ds_interpret_runtime.invoke(state)

        #print("\nResult is=", result["ds_classification"]["Classification"])
        print("\nCRI Interpretation:\n", yaml.dump(result["cri_interpretation"], sort_keys=False))

        return JSONResponse({
            "interpret": result["cri_interpretation"]
        })

    except Exception as e:
        print("Error in getting CRI DS category\n", str(e))
        raise HTTPException(status_code=500, detail=str(e))


    

@app.post("/cri_ds_evidence")
def assess(request: CRIDSGeneral):
    try:
        print("Getting EVIDENCE List")
        cri_ds_data = yaml.safe_load(request.cri_ds_statement)
        #print("\nCRI_DS_DATA=\n", cri_ds_data)
        if "cri_ds_statement" in cri_ds_data:
            cri_ds = cri_ds_data["cri_ds_statement"]
            #print("\n###cri_ds_statement=###\n", cri_ds)
        print("\nCRI_DS_Statement\n", cri_ds_data["cri_ds_statement"]["diagnostic_statement"])
        print("\nResponse Guide\n", cri_ds_data["cri_ds_statement"]["ResponseGuide"])
        print("\nEEE\n", cri_ds_data["cri_ds_statement"]["EEE"])

        state = CRIState(cri_ds_statement = request.cri_ds_statement)
        result = cri_ds_evd_runtime.invoke(state)

        #print("\nResult is=", result["ds_classification"]["Classification"])
        print("\nList of Evidence:\n", yaml.dump(result["evidence_requirement"]))

        return JSONResponse({
            "RequireEvidence": result["evidence_requirement"]["artifacts"]
        })

    except Exception as e:
        print("Error in getting CRI DS category\n", str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/cri_ds_decodeClassify")
def assess(request: CRIDSGeneral):
    try:
        cri_ds_data = yaml.safe_load(request.cri_ds_statement)
        print("\nCRI_DS_DATA DECODE=\n", cri_ds_data)
        if "cri_ds_statement" in cri_ds_data:
            cri_ds = cri_ds_data["cri_ds_statement"]
            print("\n###cri_ds_statement=###\n", cri_ds)
        
        state = CRIState(cri_ds_statement = request.cri_ds_statement)
        result = cri_ds_decodeClassify_runtime.invoke(state)
        print("\nCRI INTERPRITATION :\n", json.dumps(result["cri_interpretation1"], indent=2))
        print("\nCRI CLASSIFICATION :\n", json.dumps(result["ds_classification2"], indent=2))
        print("\nCRI VALIDATED CLASSIFICATION :\n", json.dumps(result["ds_classification_validated"], indent=2))

        return JSONResponse({
            "cri_interpretation": result["cri_interpretation1"], 
            "ds_classification": result["ds_classification2"],
            "cri_validated_classification": result["ds_classification_validated"]
        })        
        
    except Exception as e:
        print("Error in getting CRI DS Decode & Classify\n", str(e))
        raise HTTPException(status_code=500, detail=str(e))



@app.post("/cri_ds_category")
def assess(request: CRIDSGeneral):
    try:
        cri_ds_data = yaml.safe_load(request.cri_ds_statement)
        #print("\nCRI_DS_DATA=\n", cri_ds_data)
        if "cri_ds_statement" in cri_ds_data:
            cri_ds = cri_ds_data["cri_ds_statement"]
            #print("\n###cri_ds_statement=###\n", cri_ds)
        print("\nCRI_DS_Statement\n", cri_ds_data["cri_ds_statement"]["diagnostic_statement"])
        print("\nResponse Guide\n", cri_ds_data["cri_ds_statement"]["ResponseGuide"])
        print("\nEEE\n", cri_ds_data["cri_ds_statement"]["EEE"])

        state = CRIState(cri_ds_statement = request.cri_ds_statement)
        result = cri_ds_runtime.invoke(state)

        #print("\nResult is=", result["ds_classification"]["Classification"])
        print("YAML dump\n", yaml.dump(result["ds_classification"]["Classification"], sort_keys=False, allow_unicode=True, default_flow_style=False))

        return JSONResponse({
            "Classification": result["ds_classification"]["Classification"]
        })

    except Exception as e:
        print("Error in getting CRI DS category\n", str(e))
        raise HTTPException(status_code=500, detail=str(e))





@app.post("/assess_new")
def assess(request: AgentRequestGeneral):
    try:
        user_data = yaml.safe_load(request.general_question)
        #print("\nUSER_DATA=\n", user_data)
        if "user_gen_question_answer" in user_data:
            question_data = user_data["user_gen_question_answer"]
        #print("\n###question_data=###\n", question_data)
        
        state = GENState(user_inputs=user_data)
        print("\n5-state is saved, invoking agent")        
                
        if "RULES_TO_APPLY" in user_data:
            rules_data = user_data["RULES_TO_APPLY"]
            
            if isinstance(rules_data, dict):
                # Already parsed
                #print("\nNO PARSING REQUIRED")
                policy_data = rules_data
                industry = policy_data.get('rules', {}).get('industry')
            elif isinstance(rules_data, str):
                # Need to parse
                #print("\nNO PARSING\n")
                policy_data = yaml.safe_load(rules_data)
                industry = parsed.get('rules', {}).get('industry')
            else:
                industry = None
            
            print(f"####Industry: {industry}") 
            
        analysis_result = execute_policy_engine(build_gen_state(question_data), policy_data)
        state.engine_output = analysis_result
        
        ceiling = state.engine_output.get("enforcedMaturityCeiling")
        if not ceiling or not 1 <= ceiling <= 5:
            ceiling = 1  # Default to 1 maturity
    
        gen_contract = GENContract(
            governance_summary="unknown",
            material_gaps=state.engine_output.get("materialGaps", []),
            enforced_maturity_ceiling= ceiling,
            domain_caps=state.engine_output.get("domainCaps", {}),
            ceiling_rationale=state.engine_output.get("ceilingRationale", []),
            confidence_level=state.engine_output.get("confidenceLevel", "unknown")
        )
        state.gen_contract = gen_contract
    
        print("\n✅ GENContract successfully built:")
        session_id = SESSION_STORE.create_session("sunilKPGEN")
        SESSION_STORE.set(session_id, state)
        print(yaml.dump(state.gen_contract.dict(), sort_keys=False))
        
        result = genagent_runtime.invoke(state)
        if not isinstance(result, GENState):
            result = GENState(**dict(result))
        print("\n✅ SUCCESS GEN OUTPUT\n")
        #print(yaml.dump(result.gen_output_executive, sort_keys=False, allow_unicode=True, default_flow_style=False))
        #print(yaml.dump(result.gen_output_analyst, sort_keys=False, allow_unicode=True, default_flow_style=False))
        #print(yaml.dump(result.gen_output_remediation, sort_keys=False, allow_unicode=True, default_flow_style=False))
        
        #return Response(
        #    content=yaml.dump(state.engine_output, sort_keys=False),
        #    media_type="text/yaml"
        #)

        return JSONResponse({
            "engine_output": yaml.dump(state.engine_output, sort_keys=False),
            "executive_summary": yaml.dump(result.gen_output_executive, sort_keys=False, allow_unicode=True, default_flow_style=False),
            "analyst_report": yaml.dump(result.gen_output_analyst, sort_keys=False, allow_unicode=True, default_flow_style=False),
            "remediation_plan": yaml.dump(result.gen_output_remediation, sort_keys=False, allow_unicode=True, default_flow_style=False)
        })

        
    except Exception as e:
        print("@@@@@GERTING EXCEPTION@@@\n", str(e))
        raise HTTPException(status_code=500, detail=str(e))



@app.post("/assess")
def assess(request: AgentRequestGeneral):
    try:
        user_data = yaml.safe_load(request.general_question)
        print("\nUSER_DATA=\n", user_data)
        if "general_question_user_analysis" in user_data:
            question_data = user_data["general_question_user_analysis"]
        else:
            print("\n3-No proper data format")

        if not isinstance(user_data, dict):
            raise HTTPException(status_code=400, detail="Invalid YAML input")

        state = GENState(user_inputs=user_data)
        print("\n5-state is saved, invoking agent")

        result = genagent_runtime.invoke(state)
        if not isinstance(result, GENState):
            result = GENState(**dict(result))  

        return Response(
            content=yaml.dump(result.gen_output, sort_keys=False),
            media_type="text/yaml"
        )
    except Exception as e:
        print("@@@@@ GERTING EXCEPTION")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/domainspecific")
def assess(request: AgentRequestDomain):
    try:
        domain_question = yaml.safe_load(request.domain_question)
        if "domain_specific_question" in domain_question:
            question_data = domain_question["domain_specific_question"]
            domainName = question_data["input"]["domain"]
            questionID = question_data["input"]["question_id"]
        else:
            raise HTTPException(status_code=400, detail="Missing domain_specific_question key")  

        if not isinstance(domain_question, dict):
            raise HTTPException(status_code=400, detail="Invalid YAML input")
        
        gen_state = SESSION_STORE.get("sunilKPGEN")
        if not gen_state:
            print("Run GEN Assessment first")
            raise HTTPException(400, "Run GEN assessment first")
        
        domain_state = SESSION_STORE.get("sunilKPDOM")
        if not domain_state:
            print("\nNo DOMAIN State, initiating one\n")
            SESSION_STORE.create_session("sunilKPDOM")
            domain_state = DomainState(gen_contract=gen_state.gen_contract, domain_name=domainName, question_id=questionID)
        
        domain_state.question_id = questionID
        domain_state.questions[questionID] = question_data
        print("\n%%%%%domain state is created%%%%\n", domain_state.question_id)
        result = domainagent_runtime.invoke(domain_state)
        print("\nProcessing SUCCESS")
        if not isinstance(result, DomainState):
            result = DomainState(**dict(result))
        
        SESSION_STORE.set("sunilKPDOM", result)
        return Response(
            content=yaml.dump(result.question_results[result.question_id], sort_keys=False),
            media_type="text/yaml"
        )        
            
    except Exception as e:
        print("@@@@@ GERTING EXCEPTION")
        raise HTTPException(status_code=500, detail=str(e))        


@app.post("/domainspecific_new")
def assess(request: AgentRequestDomain):
    try:
        domain_question = yaml.safe_load(request.domain_question)
        #print("###domain_question###=\n", domain_question)
        if "domain_specific_question" in domain_question:
            question_data = domain_question["domain_specific_question"]
            print("question_data=\n", question_data)
            domainName = question_data["input"]["domain"]
            questionID = question_data["input"]["question_id"]
        else:
            raise HTTPException(status_code=400, detail="Missing domain_specific_question key")  

        if not isinstance(domain_question, dict):
            raise HTTPException(status_code=400, detail="Invalid YAML input")

        gen_state = SESSION_STORE.get("sunilKPGEN")
        if not gen_state:
            print("Run GEN Assessment first")
            raise HTTPException(400, "Run GEN assessment first")
                
        domain_state = SESSION_STORE.get("sunilKPDOM")
        if not domain_state:
            print("\nNo DOMAIN State, initiating one\n")
            SESSION_STORE.create_session("sunilKPDOM")
            domain_state = DomainState(gen_contract=gen_state.gen_contract, domain_name=domainName, question_id=questionID)
        
        domain_state.question_id = questionID
        domain_state.questions[questionID] = question_data
        print("\n%%%%%domain state is created%%%%\n", domain_state.question_id)
        #print("\n%%%%%domain state is created%%%%\n", domain_state.questions[questionID]["input"]["question_text"])
        result = domainagent_runtime.invoke(domain_state)
        print("\nProcessing SUCCESS")
        if not isinstance(result, DomainState):
            result = DomainState(**dict(result))
        
        SESSION_STORE.set("sunilKPDOM", result)
        print("Domain Executive Narrative=\n", yaml.dump(result.question_results_narrative_executive[result.question_id], sort_keys=False, allow_unicode=True, default_flow_style=False))

        print("Domain Analyst Narrative=\n", yaml.dump(result.question_results_narrative_analyst[result.question_id], sort_keys=False, allow_unicode=True, default_flow_style=False)) 

        print("Domain Remediation Narrative=\n", yaml.dump(result.question_results_narrative_remediation[result.question_id], sort_keys=False, allow_unicode=True, default_flow_style=False))        
        
        return JSONResponse({
            "question_results": yaml.dump(result.question_results[result.question_id], sort_keys=False),
            "domain_executive_summary": yaml.dump(result.question_results_narrative_executive[result.question_id], sort_keys=False, allow_unicode=True, default_flow_style=False), 
            "domain_analyst_summary": yaml.dump(result.question_results_narrative_analyst[result.question_id], sort_keys=False, allow_unicode=True, default_flow_style=False), 
            "domain_remediation_summary": yaml.dump(result.question_results_narrative_remediation[result.question_id], sort_keys=False, allow_unicode=True, default_flow_style=False)
        })

        #return Response(
        #    content=yaml.dump(result.question_results[result.question_id], sort_keys=False),
        #    media_type="text/yaml"
        #)        
            
    except Exception as e:
        print("@@@@@ GERTING EXCEPTION")
        raise HTTPException(status_code=500, detail=str(e))        


# ----------------------------
# AGENT MAIN ENTRYPOINT
# ----------------------------
@app.post("/calculate_result")
def assess(request: AgentRequestResult):
    try:
        print("\n***Calculating Final Assessment Result***\n")
        result_question = yaml.safe_load(request.domain_result)
        print("\nresult_question=", result_question)

        response = "Maturity: High"
        domain_state = SESSION_STORE.get("sunilKPDOM")
        if not domain_state:
            response = "Error: No assessment performed"        
            return Response(
                content=yaml.dump(response, sort_keys=False),
                media_type="text/yaml"
            )
        else:
            result = finalize_domain_maturity(domain_state)
            if not isinstance(result, DomainState):
                result = DomainState(**dict(result))
            
            print("\n###FINAL MATURITY###", result.final_maturity)
            return JSONResponse(content=result.final_maturity)       
        
    except Exception as e:
        print("@@@@@ UNABLE TO CALCULATE FINAL RESULT")
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


def finalize_domain_maturity(state: DomainState) -> DomainState:
    if not state.question_results:
        raise ValueError("No question results found — cannot finalize domain maturity")

    #print("\nGEN Contract in Domain\n")
    #print(yaml.dump(state.gen_contract.dict(), sort_keys=False))
    total_weighted_score = 0.0
    total_weight = 0.0
    confidence_scores = []

    per_question_summary = []

    for qid, result in state.question_results.items():
        try:
            #print("\n####QID=", qid)
            final_score = float(result["final_maturity_score"])
            #print("\n%%%%final_score=", final_score)
            weighted = float(result["weighted_score"])
            #print("\n%%%%weighted=", weighted)
            confidence = result.get("confidence_level", "Medium")
            #print("\n%%%%confidence=", confidence)
        except Exception as e:
            raise ValueError(f"Invalid result format for {qid}: {e}")

        # Recover weight safely
        question = state.questions.get(qid, {})
        #print("\n%%%%question=", question)
        weight = float(
            question.get("input", {})
                    .get("question_weight", 1)
        )
        #print("\n%%%%weight=", weight)
        total_weighted_score += weighted
        total_weight += weight
        confidence_scores.append(CONFIDENCE_MAP.get(confidence, 2))

        per_question_summary.append({
            "question_id": qid,
            "score": final_score,
            "weight": weight,
            "confidence": confidence
        })

    if total_weight == 0:
        raise ValueError("Total question weight is zero — cannot compute maturity")

    #print("\n%%%%total_weight=", total_weight)
    domain_score = round(total_weighted_score / total_weight, 2)
    #print("\n%%%%domain_score=", domain_score)

    # Apply GEN-enforced ceiling
    #domain_key = normalize_domain_key(state.domain_name)
    domain_key = "identity_lifecycle"
    #print("\n%%%%domain_key=", domain_key)
    
    #print(state.gen_contract.enforced_maturity_ceiling)
    #print(state.gen_contract.domain_caps.get(domain_key, 5))
    max_allowed = min(
        state.gen_contract.enforced_maturity_ceiling,
        state.gen_contract.domain_caps.get(domain_key, 5)
    )
    #print("\n%%%%max allowed=",max_allowed)
    if domain_score > max_allowed:
        domain_score = float(max_allowed)

    # Map score to maturity label
    level = math.floor(domain_score)
    #print("\n###level###", level)
    level_label = {
        1: "Initial",
        2: "Repeatable",
        3: "Defined",
        4: "Managed",
        5: "Optimized"
    }.get(level, "Defined")

    #print("\n###level_label###", level_label)
    avg_confidence = round(mean(confidence_scores))
    #print("\n###avg_confidence###", avg_confidence)
    domain_confidence = REVERSE_CONFIDENCE_MAP.get(avg_confidence, "Medium")
    #print("\n###domain_confidence###", domain_confidence)

    # Executive Summary
    executive_summary = (
        f"The {state.domain_name} domain demonstrates an overall maturity of "
        f"Level {level} ({level_label}) with a weighted score of {domain_score}. "
        f"Scoring reflects governance constraints enforced by upstream IAM policy "
        f"and domain-specific control effectiveness observed across "
        f"{len(state.question_results)} assessment questions."
    )
    #print("\n###executive_summary###", executive_summary)
    #print("\n###state.domain_name###", state.domain_name)
    #print("\n###domain_score###", domain_score)
    #print("\n###adjusted_level###", f"Level {level} – {level_label}")
    #print("\n###per_question_summary###", per_question_summary)
    #print("\n###state.gen_contract.enforced_maturity_ceiling###", state.gen_contract.enforced_maturity_ceiling)
    #print("\n###max_allowed###", max_allowed)
    #print("\n###state.gen_contract.material_gaps###", state.gen_contract.material_gaps)
    
    state.final_maturity = {
        "domain": state.domain_name,
        "final_maturity_score": domain_score,
        "adjusted_level": f"Level {level} – {level_label}",
        "confidence_level": domain_confidence,
        "executive_summary": executive_summary,
        "per_question_breakdown": per_question_summary,
        "governance": {
            "enforced_ceiling": state.gen_contract.enforced_maturity_ceiling,
            "domain_cap": max_allowed,
            "material_gaps": state.gen_contract.material_gaps
        }
    }
    print("\n###state.final_maturity###", state.final_maturity)
    return state
