import functools
import operator
from typing import Annotated, Sequence, TypedDict
from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, BaseMessage
from langchain.output_parsers.openai_functions import JsonOutputFunctionsParser
from tools import get_tools
import os

load_dotenv()

groq_api_key = os.getenv("groq_api_key")
llm = ChatGroq(model_name="deepseek-r1-distill-llama-70b", groq_api_key=groq_api_key)
tools = get_tools()

class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]
    next: str
    step: Annotated[int, operator.add]  

def create_agent(llm: ChatGroq, tools: list, system_prompt: str):
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        MessagesPlaceholder(variable_name="messages"),
        MessagesPlaceholder(variable_name="agent_scratchpad")
    ])
    agent = create_openai_tools_agent(llm, tools, prompt)
    return AgentExecutor(agent=agent, tools=tools, verbose=True)

def agent_node(state, agent, agent_name):
    try:
        result = agent.invoke(state)
        return {
            "messages": [HumanMessage(content=result["output"], name=agent_name)],
            "step": state.get("step", 0) + 1  # Increment step count
        }
    except Exception as e:
        return {
            "messages": [HumanMessage(content=f"Error in {agent_name}: {str(e)}", name=agent_name)],
            "step": state.get("step", 0) + 1
        }

def get_members():
    return ["Web_Searcher", "Insight_Researcher"]

def create_supervisor():
    members = get_members()
    system_prompt = (
        "You are a supervisor managing workers: {members}. "
        "Follow these rules:\n"
        "1. Maximum 5 steps allowed\n"
        "2. Current step: {step}\n"
        "3. Return FINISH when:\n"
        "   - Answer is complete\n"
        "   - Step limit reached\n"
        "   - No further actions needed"
    )
    options = ["FINISH"] + members
    
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        MessagesPlaceholder(variable_name="messages"),
        ("system", "Choose next agent or FINISH. Options: {options}")
    ]).partial(
        options=str(["FINISH"] + members),
        members=", ".join(members)
    )
    
    return (
        prompt
        | llm.bind_functions(functions=[{
            "name": "route",
            "description": "Select next agent or finish",
            "parameters": {
                "type": "object",
                "properties": {
                    "next": {"enum": ["FINISH"] + members}
                },
                "required": ["next"]
            }
        }], function_call="route")
        | JsonOutputFunctionsParser()
    )

def create_search_agent():
    search_agent = create_agent(
        llm, 
        tools, 
        "You are a web search engine. Search for information on the internet and return the results."
    )
    return functools.partial(
        agent_node, 
        agent=search_agent, 
        agent_name="Web_Searcher"  # Correct parameter name
    )

def create_insights_researcher_agent():
    insights_research_agent = create_agent(
        llm,
        tools,
        """You are an Insight Researcher. Do step by step:
        1. Identify key topics from provided content
    
        2. Search for more information on the topics
        
        3. Summarize the information
        
        4. Provide references
        """
    )
    return functools.partial(
        agent_node, 
        agent=insights_research_agent, 
        agent_name="Insight_Researcher"  # Fixed parameter name
    )