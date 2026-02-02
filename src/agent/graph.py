from langgraph.graph import StateGraph, END
from agent.state import AgentState
from agent.nodes import detector_node, filter_node, parse_input_node, minifier_node, reasoner_node, verification_node, mutator_node

def router(state: AgentState):
    if state["consecutive_failure_count"] >= 10 or state["iteration"] >= 20: # 连续失败次数达到 10 次或迭代次数达到 20 次则结束，进入推理节点
        return "reasoner"
    return "minify"

def build_graph():
    workflow = StateGraph(AgentState)
    
    # 注册节点
    workflow.add_node("parse", parse_input_node)
    workflow.add_node("minify", minifier_node)
    workflow.add_node("verify", verification_node)
    workflow.add_node("reasoner", reasoner_node)
    workflow.add_node("filter", filter_node)
    workflow.add_node("mutator", mutator_node)
    workflow.add_node("detector", detector_node)
    
    # 定义流程
    workflow.set_entry_point("parse")
    workflow.add_edge("parse", "minify")
    workflow.add_edge("minify", "verify")
    
    # 条件跳转
    workflow.add_conditional_edges(
        "verify",
        router,
        {"minify": "minify", "reasoner": "reasoner"}
    )
    workflow.add_edge("reasoner", "filter")
    workflow.add_edge("filter", "mutator")
    workflow.add_edge("mutator", "detector")
    workflow.add_edge("detector", END)
    
    return workflow.compile()