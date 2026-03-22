import yaml
from typing import Dict, Any
from models import IAMState, GENState, GENContract
from groq_client import call_groq
from session_store import SESSION_STORE

# ----------------------------
# SYSTEM PROMPTS (Shortened)
# ----------------------------
def replace_governance_section(yaml_str: str, new_governance: Dict[str, Any]) -> str:
    """
    Replace the entire governance_results section with new data
    """
    # Parse the YAML
    data = yaml.safe_load(yaml_str)
    
    # Completely replace the governance_results section
    data['governance_results'] = new_governance
    
    # Convert back to YAML string
    return yaml.dump(data, default_flow_style=False, sort_keys=False)

# ----------------------------
# AGENT NODES
# ----------------------------

def gen_agent_report_executive(state: GENState) -> GENState:
    try:
        print("in gen_agent_report_executive")

        #print(yaml.dump(state.gen_contract.dict(), sort_keys=False))
        final_prompt = replace_governance_section(EXECUTIVE_PROMPT, state.gen_contract.dict())
        #print("\nfinal prompt=\n", final_prompt)
        gen_result = call_groq(
            system_prompt=SYSTEM_CONTEXT_NARRATIVE,
            user_payload={"general_question": final_prompt},
            model="openai/gpt-oss-120b"
        )  
        #print("\nGen response=\n", gen_result)
        state.gen_output_executive = gen_result
        #print("\nGen response=\n", state.gen_output_executive)    
        return state     
    except Exception as e:
        print("Unable to GEN executive report. Error is: ", str(e))
        raise HTTPException(status_code=500, detail=str(e))

def gen_agent_report_executive_validate(state: GENState) -> GENState:
    print("in gen_agent_report_executive_validate")
    
    return state
    
def gen_agent_report_analyst(state: GENState) -> GENState:
    try:
        print("in gen_agent_report_analyst")
      
        #print(yaml.dump(state.gen_contract.dict(), sort_keys=False))
        final_prompt = replace_governance_section(ANALYST_PROMPT, state.gen_contract.dict())
        #print("\nfinal prompt=\n", final_prompt)
        gen_result = call_groq(
            system_prompt=SYSTEM_CONTEXT_NARRATIVE,
            user_payload={"general_question": final_prompt},
            model="openai/gpt-oss-120b"
        )  
        #print("\nGen response=\n", gen_result)
        state.gen_output_analyst = gen_result
        #print("\nGen response=\n", state.gen_output_analyst)    
        return state
    except Exception as e:
        print("Unable to generate GEN analyst report. Error is: ", str(e))
        raise HTTPException(status_code=500, detail=str(e))        

def gen_agent_report_analyst_validate(state: GENState) -> GENState:
    print("in gen_agent_report_analyst_validate")
    
    return state 
    
def gen_agent_report_validation(state: GENState) -> GENState:
    try:
        print("in gen_agent_report_validation")
        #print(yaml.dump(state.gen_contract.dict(), sort_keys=False))
        final_prompt = replace_governance_section(REMEDIATION_PROMPT, state.gen_contract.dict())
        #print("\nfinal prompt=\n", final_prompt)
        gen_result = call_groq(
            system_prompt=SYSTEM_CONTEXT_NARRATIVE,
            user_payload={"general_question": final_prompt},
            model="openai/gpt-oss-120b"
        )  
        #print("\nGen response=\n", gen_result)
        state.gen_output_remediation = gen_result
        print("\nGen response=\n", state.gen_output_remediation)    
        return state
    except Exception as e:
        print("Unable to generate GEN validation report. Error is: ", str(e))
        raise HTTPException(status_code=500, detail=str(e))         

def gen_agent_report_validation_validate(state: GENState) -> GENState:
    print("in gen_agent_report_validation_validate")

    return state     



def gen_agent(state: GENState) -> GENState:
    try:
        print("🧠 GEN AGENT RUNNING\n")

        gen_result = call_groq(
            system_prompt=SYSTEM_CONTEXT_GEN,
            user_payload={"general_question": state.user_inputs},
            model="openai/gpt-oss-120b"
        )

        # Mutate state instead of returning a dict
        state.gen_output = gen_result

        return state
    except Exception as e:
        print("Unable to get GEN assessment result. Error is: ", str(e))
        raise HTTPException(status_code=500, detail=str(e)) 



def gen_validator(state: GENState) -> GENState:
    try:
        print("🔍 VALIDATOR AGENT RUNNING")

        if not state.gen_output:
            raise Exception("Missing GEN output")

        required_keys = ["gen_assessment", "domain_caps", "confidence_level"]

        for key in required_keys:
            if key not in state.gen_output:
                print("\nDID NOT FIND ALL REQUIRED KEY, MEANS NO PROPER RESPONSE")
                raise Exception(f"GEN output missing required key: {key}")
        
        print("THE STATE FROM WERE WE WILL MAKE CONTRACT IS \n", state.gen_output)
        try:
            if state.gen_output:
                gen_assessment = state.gen_output.get("gen_assessment", {})
                
                # Build GENContract safely
                state.gen_contract = GENContract(
                    **gen_assessment,  # governance_summary, material_gaps, enforced_maturity_ceiling
                    domain_caps=state.gen_output.get("domain_caps", {}),
                    domain_expectations=state.gen_output.get("domain_expectations", {}),
                    confidence_level=state.gen_output.get("confidence_level", "Unknown")
                )
                
                print("\n✅ GENContract successfully built:")
                session_id = SESSION_STORE.create_session("sunilKPGEN")
                SESSION_STORE.set(session_id, state)
                print(yaml.dump(state.gen_contract.dict(), sort_keys=False))
            else:
                state.gen_contract = None
                print("⚠️ No gen_output found; GENContract not created.")

        except Exception as e:
            print("⚠️ Failed to build GENContract:", e)
            state.gen_contract = None
        
        print("\nGEN CONTRACT=\n", state.gen_contract)
        state.validation_status = "PASS"
        return state
    except Exception as e:
        print("Unable to validate GEN assessment result. Error is: ", str(e))
        raise HTTPException(status_code=500, detail=str(e)) 
