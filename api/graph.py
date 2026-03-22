from langgraph.graph import StateGraph
from models import IAMState, GENState, DomainState, CRIState
from agents.gen_agents import gen_agent, gen_validator, gen_agent_report_executive, gen_agent_report_executive_validate
from agents.gen_agents import gen_agent_report_analyst, gen_agent_report_analyst_validate 
from agents.gen_agents import gen_agent_report_validation, gen_agent_report_validation_validate
from agents.domain_agents import validator_agent, domain_agent, dom_executive_report_agent, dom_analyst_report_agent, dom_remediation_report_agent

from agents.cri_agents import validate_input_agent, get_classification_agent, get_requireevidence_list, get_ds_interpret, get_ds_regalignment
from agents.cri_agents import get_ds_decode, get_ds_classify, get_ds_validate_classify

# ----------------------------
# BUILD AGENT WORKFLOW
# ----------------------------

#This is Graph.py

gen_graph = StateGraph(GENState)

gen_graph.add_node("report-executive", gen_agent_report_executive)
gen_graph.add_node("report-executive-validator", gen_agent_report_executive_validate)
gen_graph.add_node("report-analyst", gen_agent_report_analyst)
gen_graph.add_node("report-analyst-validator", gen_agent_report_analyst_validate)
gen_graph.add_node("report-validation", gen_agent_report_validation)
gen_graph.add_node("report-validation-validator", gen_agent_report_validation_validate)

gen_graph.set_entry_point("report-executive")
gen_graph.add_edge("report-executive", "report-executive-validator")
gen_graph.add_edge("report-executive-validator", "report-analyst")
gen_graph.add_edge("report-analyst", "report-analyst-validator")
gen_graph.add_edge("report-analyst-validator", "report-validation")
gen_graph.add_edge("report-validation", "report-validation-validator")
genagent_runtime = gen_graph.compile()


domain_graph = StateGraph(DomainState)
domain_graph.add_node("gen", domain_agent)
domain_graph.add_node("validate", validator_agent)
domain_graph.add_node("dom-executive-report", dom_executive_report_agent)
domain_graph.add_node("dom-analyst-report", dom_analyst_report_agent)
domain_graph.add_node("dom-remediation-report", dom_remediation_report_agent)

domain_graph.set_entry_point("gen")
domain_graph.add_edge("gen", "validate")
domain_graph.add_edge("validate", "dom-executive-report")
domain_graph.add_edge("dom-executive-report", "dom-analyst-report")
domain_graph.add_edge("dom-analyst-report", "dom-remediation-report")

domainagent_runtime = domain_graph.compile()

cri_graph = StateGraph(CRIState)
cri_graph.add_node("validate_input", validate_input_agent)
cri_graph.add_node("classification", get_classification_agent)

cri_graph.set_entry_point("validate_input")
cri_graph.add_edge("validate_input", "classification")
cri_ds_runtime = cri_graph.compile()



cri_evd_graph = StateGraph(CRIState)
cri_evd_graph.add_node("validate_input", validate_input_agent)
cri_evd_graph.add_node("evidence_list", get_requireevidence_list)

cri_evd_graph.set_entry_point("validate_input")
cri_evd_graph.add_edge("validate_input", "evidence_list")

cri_ds_evd_runtime = cri_evd_graph.compile()



cri_interpret_graph = StateGraph(CRIState)
cri_interpret_graph.add_node("validate_input", validate_input_agent)
cri_interpret_graph.add_node("ds_interpret", get_ds_interpret)

cri_interpret_graph.set_entry_point("validate_input")
cri_interpret_graph.add_edge("validate_input", "ds_interpret")
cri_ds_interpret_runtime = cri_interpret_graph.compile()


cri_ds_regalignment_graph = StateGraph(CRIState)
cri_ds_regalignment_graph.add_node("validate_input", validate_input_agent)
cri_ds_regalignment_graph.add_node("ds_regalignment", get_ds_regalignment)

cri_ds_regalignment_graph.set_entry_point("validate_input")
cri_ds_regalignment_graph.add_edge("validate_input", "ds_regalignment")
cri_ds_regalignment_runtime = cri_ds_regalignment_graph.compile()


cri_decodeclassify_graph = StateGraph(CRIState)
cri_decodeclassify_graph.add_node("validate_input", validate_input_agent)
cri_decodeclassify_graph.add_node("interpret_analyze", get_ds_decode)
cri_decodeclassify_graph.add_node("classify", get_ds_classify)
cri_decodeclassify_graph.add_node("validate_classify", get_ds_validate_classify)

cri_decodeclassify_graph.set_entry_point("validate_input")
cri_decodeclassify_graph.add_edge("validate_input", "interpret_analyze")
cri_decodeclassify_graph.add_edge("interpret_analyze", "classify")
cri_decodeclassify_graph.add_edge("classify", "validate_classify")
cri_ds_decodeClassify_runtime = cri_decodeclassify_graph.compile()
