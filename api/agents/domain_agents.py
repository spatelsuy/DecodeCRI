import yaml
from typing import Dict, Any
from models import IAMState, GENState, DomainState, GENContract
from groq_client import call_groq

# ----------------------------
# AGENT NODES
# ----------------------------

def dom_remediation_report_agent(state: DomainState) -> Dict[str, Any]:
    try:
        print("Domain remediation report")
        questionID = state.question_id
        result = state.question_results[questionID]

        assessment_context = {
            "assessment_context": {
                "governance_contract": {
                    "enforced_ceiling": state.gen_contract.enforced_maturity_ceiling,
                    "domain_caps": state.gen_contract.domain_caps,
                    "material_gaps": state.gen_contract.material_gaps,
                    "confidence_level": state.gen_contract.confidence_level,
                },
                "domain_question_result": {
                    "domain": state.domain_name,
                    "question_id": state.question_id,
                    "question_description": state.questions[questionID]["input"]["question_text"],
                    "selected_description": state.questions[questionID]["input"]["selected_description"],
                    "metrics_id": state.questions[questionID]["input"]["general_governance_context"]["additional_context"]["metrics_id"],
                    "metrics_description": state.questions[questionID]["input"]["general_governance_context"]["additional_context"]["metrics_description"],
                    "controls_id": state.questions[questionID]["input"]["general_governance_context"]["additional_context"]["controls_id"],
                    "controls_description": state.questions[questionID]["input"]["general_governance_context"]["additional_context"]["controls_description"],
                    "final_maturity_score": result["final_maturity_score"],
                    "adjusted_level": result["adjusted_level"],
                    "assessment_rationale": result["assessment_rationale"],
                    "suggested_improvement": result["suggested_improvement"],
                    "confidence_level": result.get("confidence_level", "Medium")
                }            
            }
        }
        gen_result = call_groq(
            system_prompt=DOMAIN_CONTEXT_REMEDIATION_NARRATIVE,
            user_payload={"general_question": yaml.dump(assessment_context, sort_keys=False, allow_unicode=True, default_flow_style=False)},
            model="openai/gpt-oss-120b"
        )
        state.question_results_narrative_remediation[questionID] = gen_result     
        print("Success")    
        return state
    except Exception as e:
        print("Unable to generate Remediation Report", str(e))
        raise HTTPException(status_code=500, detail=str(e))  


def dom_analyst_report_agent(state: DomainState) -> Dict[str, Any]:
    try:
        print("Domain analyst report")
        questionID = state.question_id
        result = state.question_results[questionID]

        assessment_context = {
            "assessment_context": {
                "governance_contract": {
                    "enforced_ceiling": state.gen_contract.enforced_maturity_ceiling,
                    "domain_caps": state.gen_contract.domain_caps,
                    "material_gaps": state.gen_contract.material_gaps,
                    "confidence_level": state.gen_contract.confidence_level,
                },
                "domain_question_result": {
                    "domain": state.domain_name,
                    "question_id": state.question_id,
                    "question_description": state.questions[questionID]["input"]["question_text"],
                    "selected_description": state.questions[questionID]["input"]["selected_description"],
                    "metrics_id": state.questions[questionID]["input"]["general_governance_context"]["additional_context"]["metrics_id"],
                    "metrics_description": state.questions[questionID]["input"]["general_governance_context"]["additional_context"]["metrics_description"],
                    "controls_id": state.questions[questionID]["input"]["general_governance_context"]["additional_context"]["controls_id"],
                    "controls_description": state.questions[questionID]["input"]["general_governance_context"]["additional_context"]["controls_description"],
                    "final_maturity_score": result["final_maturity_score"],
                    "adjusted_level": result["adjusted_level"],
                    "assessment_rationale": result["assessment_rationale"],
                    "suggested_improvement": result["suggested_improvement"],
                    "confidence_level": result.get("confidence_level", "Medium")
                }            
            }
        }
        gen_result = call_groq(
            system_prompt=DOMAIN_CONTEXT_ANALYST_NARRATIVE,
            user_payload={"general_question": yaml.dump(assessment_context, sort_keys=False, allow_unicode=True, default_flow_style=False)},
            model="openai/gpt-oss-120b"
        )
        state.question_results_narrative_analyst[questionID] = gen_result  
        print("Success")
        return state
    except Exception as e:
        print("Unable to generate Executive Report", str(e))
        raise HTTPException(status_code=500, detail=str(e))




def dom_executive_report_agent(state: DomainState) -> Dict[str, Any]:
    try:
        print("Domain executive report")
        questionID = state.question_id
        #print("\nQuestion Id=", questionID) 
        #print("\n###Question is=###", state.questions[questionID])
        result = state.question_results[questionID]
        #print("\n###Result is=###", result)
        #print("\n###Result is=###\n",yaml.dump(result, sort_keys=False, allow_unicode=True, default_flow_style=False))
        
        
        assessment_context = {
            "assessment_context": {
                "governance_contract": {
                    "enforced_ceiling": state.gen_contract.enforced_maturity_ceiling,
                    "domain_caps": state.gen_contract.domain_caps,
                    "material_gaps": state.gen_contract.material_gaps,
                    "confidence_level": state.gen_contract.confidence_level,
                },
                "domain_question_result": {
                    "domain": state.domain_name,
                    "question_id": state.question_id,
                    "question_description": state.questions[questionID]["input"]["question_text"],
                    "selected_description": state.questions[questionID]["input"]["selected_description"],
                    "metrics_id": state.questions[questionID]["input"]["general_governance_context"]["additional_context"]["metrics_id"],
                    "metrics_description": state.questions[questionID]["input"]["general_governance_context"]["additional_context"]["metrics_description"],
                    "controls_id": state.questions[questionID]["input"]["general_governance_context"]["additional_context"]["controls_id"],
                    "controls_description": state.questions[questionID]["input"]["general_governance_context"]["additional_context"]["controls_description"],
                    "final_maturity_score": result["final_maturity_score"],
                    "adjusted_level": result["adjusted_level"],
                    "assessment_rationale": result["assessment_rationale"],
                    "suggested_improvement": result["suggested_improvement"],
                    "confidence_level": result.get("confidence_level", "Medium")
                }            
            }
        }
        #print("\n####assessment_context####\n", yaml.dump(assessment_context, sort_keys=False, allow_unicode=True, default_flow_style=False))

        gen_result = call_groq(
            system_prompt=DOMAIN_CONTEXT_EXECUTIVE_NARRATIVE,
            user_payload={"general_question": yaml.dump(assessment_context, sort_keys=False, allow_unicode=True, default_flow_style=False)},
            model="openai/gpt-oss-120b"
        )
        state.question_results_narrative_executive[questionID] = gen_result
        #print("\nDomain Narrative response=\n", yaml.dump(gen_result, sort_keys=False, allow_unicode=True, default_flow_style=False))
        print("Success")
        return state
    except Exception as e:
        print("Unable to generate Executive Report", str(e))
        raise HTTPException(status_code=500, detail=str(e))

def validator_agent(state: DomainState) -> Dict[str, Any]:
    try:
        print("🔍 VALIDATOR AGENT RUNNING")

        questionID = state.question_id
        #print("\nQuestion Id=", questionID)
        response = state.question_results[questionID]
        print("\n###Response to validate=###", response)

        if not response:
            raise Exception("Missing DOMAIN output")
        else:
            print("\nprogressing with validation")

        required_keys = ["final_maturity_score", "weighted_score", "adjusted_level", "assessment_rationale"]

        for key in required_keys:
            print("\nKey = ", key)
            if key not in response:
                raise Exception(f"GEN output missing required key: {key}")
                
        print("\nFound required key in response, validation success")

        return state
    except Exception as e:
        print("Unable to validte assessment result. Error is: ", str(e))
        raise HTTPException(status_code=500, detail=str(e))


def domain_agent(state: DomainState) -> Dict[str, Any]:
    try:
        print("🏗 DOMAIN AGENT RUNNING")

        questionID = state.question_id
        print("\nQuestion Id=", questionID)
        #print("\n###Question to Evaluate=###", state.questions[questionID])
        
        domain_result = call_groq(
            system_prompt=SYSTEM_CONTEXT_DOMAIN,
            user_payload={"general_question": state.questions[questionID]},
            model="openai/gpt-oss-120b"
        )
        print("\nDomain assess result", domain_result)
        state.question_results[questionID] = domain_result

        return state
    except Exception as e:
        print("Unable to access domian question. Error is:", str(e))
        raise HTTPException(status_code=500, detail=str(e))        
