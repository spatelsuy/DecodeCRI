from langgraph.graph import StateGraph
from models import CRIState
from models import AudioProcessingState

from agents.cri_agents import validate_input_agent
from agents.cri_agents import get_ds_decode, get_ds_classify, get_ds_validate_classify, generate_code_classification, apply_hard_rules, guard_hard_rule_reversals
from agents.a2t_agents import transcribe_audio_text, categorize_text

# ----------------------------
# BUILD AGENT WORKFLOW
# ----------------------------

#This is Graph.py
cri_decodeclassify_graph = StateGraph(CRIState)
cri_decodeclassify_graph.add_node("validate_input", validate_input_agent)
cri_decodeclassify_graph.add_node("interpret_analyze", get_ds_decode)
cri_decodeclassify_graph.add_node("generate_code_classification", generate_code_classification)
cri_decodeclassify_graph.add_node("classify", get_ds_classify)
cri_decodeclassify_graph.add_node("apply_hard_rules", apply_hard_rules)
cri_decodeclassify_graph.add_node("validate_classify", get_ds_validate_classify)
cri_decodeclassify_graph.add_node("guard_hard_rule_reversals", guard_hard_rule_reversals)

cri_decodeclassify_graph.set_entry_point("validate_input")
cri_decodeclassify_graph.add_edge("validate_input", "interpret_analyze")
cri_decodeclassify_graph.add_edge("interpret_analyze", "generate_code_classification")
cri_decodeclassify_graph.add_edge("generate_code_classification", "classify")
cri_decodeclassify_graph.add_edge("classify", "apply_hard_rules")
cri_decodeclassify_graph.add_edge("apply_hard_rules", "validate_classify")
cri_decodeclassify_graph.add_edge("validate_classify", "guard_hard_rule_reversals")
cri_ds_decodeClassify_runtime = cri_decodeclassify_graph.compile()




workflow_a2t = StateGraph(AudioProcessingState)

# Add our two structural nodes
workflow_a2t.add_node("transcribe_audio_text", transcribe_audio_text)
workflow_a2t.add_node("categorize_text", categorize_text)

# Establish the sequential dependency pipeline
workflow_a2t.set_entry_point("transcribe_audio_text")
workflow_a2t.add_edge("transcribe_audio_text", "categorize_text")

workflow_a2t_runtime = workflow_a2t.compile()
