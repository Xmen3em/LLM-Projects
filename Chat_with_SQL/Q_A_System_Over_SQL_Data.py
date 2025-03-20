import streamlit as st
from pathlib import Path
from langchain.agents import create_sql_agent
from langchain.sql_database import SQLDatabase
from langchain.agents.agent_types import AgentType
from langchain.callbacks import StreamlitCallbackHandler
from langchain.agents.agent_toolkits import SQLDatabaseToolkit
from sqlalchemy import create_engine
import sqlite3
from langchain_groq import ChatGroq
from dotenv import load_dotenv
import os
from langchain_community.utilities import SQLDatabase
from typing_extensions import TypedDict, Annotated
from langchain.prompts import ChatPromptTemplate
from langchain_community.tools.sql_database.tool import QuerySQLDataBaseTool
from langgraph.graph import StateGraph, END, START
from urllib.parse import quote_plus

# Load environment variables
load_dotenv()
api_key = os.getenv("GROQ_API_KEY")

# Set up Langsmith tracing
os.environ["LANGSMITH_TRACING"] = os.getenv("LANGSMITH_TRACING")
os.environ["LANGSMITH_API_KEY"] = os.getenv("LANGSMITH_API_KEY")
os.environ["LANGSMITH_ENDPOINT"] = os.getenv("LANGSMITH_ENDPOINT")
os.environ["LANGSMITH_PROJECT"] = os.getenv("LANGSMITH_PROJECT")

# Streamlit app configuration
st.set_page_config(page_title="LangChain: Chat with SQL DB", page_icon="🦜")
st.title("🦜 LangChain: Chat with SQL DB")

# Database selection
LOCALDB = "USE_LOCALDB"
MYSQL = "USE_MYSQL"
radio_opt = ["Use SQLLite 3 Database- Chinook.db", "Connect to your MySQL Database"]
selected_opt = st.sidebar.radio(label="Choose the DB which you want to chat", options=radio_opt)

if radio_opt.index(selected_opt) == 1:
    db_uri = MYSQL
    mysql_host = st.sidebar.text_input("Provide MySQL Host")
    mysql_user = st.sidebar.text_input("MYSQL User")
    mysql_password = st.sidebar.text_input("MYSQL password", type="password")
    mysql_db = st.sidebar.text_input("MySQL database")
else:
    db_uri = LOCALDB

if not db_uri:
    st.info("Please enter the database information and uri")

# LLM model
llm = ChatGroq(groq_api_key=api_key, model_name="Llama3-8b-8192", streaming=True)

@st.cache_resource(ttl="2h")
def configure_db(db_uri, mysql_host=None, mysql_user=None, mysql_password=None, mysql_db=None):
    if db_uri == LOCALDB:
        dbfilepath = (Path(__file__).parent / "Chinook.db").absolute()
        creator = lambda: sqlite3.connect(f"file:{dbfilepath}?mode=ro", uri=True)
        return SQLDatabase(create_engine("sqlite:///", creator=creator))
    elif db_uri == MYSQL:
        if not (mysql_host and mysql_user and mysql_password and mysql_db):
            st.error("Please provide all MySQL connection details.")
            st.stop()
        encoded_password = quote_plus(mysql_password)
        return SQLDatabase(create_engine(f"mysql+mysqlconnector://{mysql_user}:{encoded_password}@{mysql_host}/{mysql_db}"))

if db_uri==MYSQL:
    db=configure_db(db_uri,mysql_host,mysql_user,mysql_password,mysql_db)
else:
    db=configure_db(db_uri)
    
# SQLDatabaseToolkit
toolkit = SQLDatabaseToolkit(db=db, llm=llm)

# SQL Agent
agent = create_sql_agent(
    llm=llm,
    toolkit=toolkit,
    verbose=True,
    agent_type=AgentType.ZERO_SHOT_REACT_DESCRIPTION
)

# State definition for LangGraph
class State(TypedDict):
    question: str
    query: str
    query_result: str
    answer: str

class QueryOutput(TypedDict):
    query: Annotated[str, "Syntactically valid SQL query."]

# Function to write SQL query
def write_query(state: State):
    chat_prompt = ChatPromptTemplate.from_template(
        """
        Given an input question, create a syntactically correct {dialect} query to run to help find the answer.  
        Unless the user specifies in their question a specific number of examples they wish to obtain,  
        always limit your query to at most {top_k} results.  
        You can order the results by a relevant column to return the most interesting examples in the database.  
        Never query for all the columns from a specific table, only ask for the few relevant columns given the question.  
        Pay attention to use only the column names that you can see in the schema description.  
        Be careful not to query for columns that do not exist. Also, pay attention to which column is in which table.  
        Only use the following tables:  
        {table_info}  
        Question: {input}  
        SQL Query:
        """
    )
    query_prompt = chat_prompt.format(
        input=state['question'],
        table_info=db.get_table_info(),
        dialect=db.dialect,
        top_k=3
    )
    structured_llm = llm.with_structured_output(QueryOutput)
    result = structured_llm.invoke(query_prompt)
    return {'query': result['query']}

# Function to execute SQL query
def execute_query(state: State):
    execute_query_tool = QuerySQLDataBaseTool(db=db)
    return {'query_result': execute_query_tool.invoke(state['query'])}

# Function to generate answer
def generate_answer(state: State):
    prompt = (
        "Given the following user question, corresponding SQL query, "
        "and SQL result, answer the user question.\n\n"
        f'Question: {state["question"]}\n'
        f'SQL Query: {state["query"]}\n'
        f'SQL Result: {state["query_result"]}'
    )
    response = llm.invoke(prompt)
    return {'answer': response.content}

# LangGraph orchestration
graph_builder = StateGraph(State).add_sequence(
    [write_query, execute_query, generate_answer]
)
graph_builder.add_edge(START, 'write_query')
graph = graph_builder.compile()

# Streamlit chat interface
if "messages" not in st.session_state or st.sidebar.button("Clear message history"):
    st.session_state["messages"] = [{"role": "assistant", "content": "How can I help you?"}]

for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["content"])

user_query = st.chat_input(placeholder="Ask anything from the database")

if user_query:
    st.session_state.messages.append({"role": "user", "content": user_query})
    st.chat_message("user").write(user_query)

    with st.chat_message("assistant"):
        streamlit_callback = StreamlitCallbackHandler(st.container())
        response = agent.run(user_query, callbacks=[streamlit_callback])
        st.session_state.messages.append({"role": "assistant", "content": response})
        st.write(response)