import json
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage
from agents import AgentState, create_supervisor, create_search_agent, create_insights_researcher_agent, get_members

def build_graph():
    graph_builder = StateGraph(AgentState)
    supervisor = create_supervisor()
    search_agent = create_search_agent()
    insights_researcher_agent = create_insights_researcher_agent()
    
    # Add nodes with step tracking
    graph_builder.add_node("Supervisor", supervisor)
    graph_builder.add_node("Web_Searcher", search_agent)
    graph_builder.add_node("Insight_Researcher", insights_researcher_agent)
    
    members = get_members()
    for member in members:
        graph_builder.add_edge(member, "Supervisor")
    
    # Modified conditional edges with step tracking
    def route_next(state):
        if state.get("step", 0) >= 5:  # Max 5 steps
            return "FINISH"
        return state["next"]
    
    conditional_map = {member: member for member in members}
    conditional_map["FINISH"] = END
    
    graph_builder.add_conditional_edges(
        "Supervisor",
        route_next,  # Use updated routing function
        conditional_map
    )
    
    graph_builder.set_entry_point("Supervisor")
    return graph_builder.compile()

def run_graph(input_text):
    graph = build_graph()
    response = graph.invoke({"messages": [HumanMessage(content=input_text)],
                             'step': 0})
    
    #extract the content
    output = response["messages"][-1].content
    
    #initialize the results and references
    result = ""
    references = []
    
    #split content by lines and process
    lines = output.split("\n")
    for i, line in enumerate(lines):
        if line.strip().startswith("[^"):  # Assuming references start with [^
            references.append(line.strip())
        else:
            result += line + "\n"
            
    # format the references
    if references:
        result += "\n\n**References:**\n"
        for ref in references:
            result += f"{ref}\n"

    return result