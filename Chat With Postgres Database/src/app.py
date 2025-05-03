import streamlit as st
from langchain.agents import create_sql_agent
from langchain.sql_database import SQLDatabase
from langchain.agents.agent_types import AgentType
from langchain_groq import ChatGroq
from langchain.agents.agent_toolkits import SQLDatabaseToolkit
from langchain.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate
from dotenv import load_dotenv
import os
from sqlalchemy import create_engine
from urllib.parse import quote_plus
import time

# Load environment variables
load_dotenv()
groq_api_key = os.getenv("GROQ_API_KEY")
db_password = os.getenv("POSTGRES_PASSWORD")  # Add to .env file

# Streamlit app configuration
st.set_page_config(page_title="CDMS AI Assistant", page_icon="🚗")
st.title("🚗 CDMS AI Assistant")

# Database configuration for PostgreSQL
@st.cache_resource(ttl="2h")
def configure_db():
    db_user = "postgres"
    db_host = "localhost"
    db_name = "car_task_database"
    encoded_password = quote_plus(db_password)
    
    engine = create_engine(
        f"postgresql+psycopg2://{db_user}:{encoded_password}@{db_host}/{db_name}"
    )
    return SQLDatabase(engine)

db = configure_db()

# LLM model configuration
llm = ChatGroq(
    groq_api_key=groq_api_key,
    model_name="gemma2-9b-it",
    temperature=0.7,
    streaming=True
)

# Custom prompt for CDMS context
system_template  = """
**Role**: AI Assistant for Car Dealership Management System  
**Goal**: Help users interact with the database through natural language queries.

Don't show the types of the columns or any technical details. Always respond in a user-friendly manner.

**User Interface Requirements**:
1. Always present these 6 options first:
   - 1️⃣ Sales Report (Last 30 Days)
   - 2️⃣ Find Customer Purchase History
   - 3️⃣ Search Available Cars by Criteria
   - 4️⃣ Employee Performance Summary
   - 5️⃣ Service History for Vehicle
   - 6️⃣ Exit

2. **Formatting Rules**:
   - 💵 Currency: Always use $ and 2 decimal places ($25,000.00)
   - 📞 Phone: (XXX) XXX-XXXX format
   - 📅 Dates: YYYY-MM-DD
   - 🆔 VIN: Validate 17-character format
   - 📊 Results: Display as tables with aligned columns

3. **Query Requirements**:
   - Always use JOINs between related tables
   - Include subqueries for nested requests (e.g., "Show cars priced above average")
   - Prioritize recent records (LAST 30 DAYS unless specified)
   - Never show raw SQL - translate results to business terms

*important notes*:
-answer without like a structure of the raw table or a sql table answer as you understand the answer to the user and without show the datatype or anything that will make the user confused
- if the result too long convert the number to tables and understand it

**Error Handling**:
- ❌ Invalid Input: "Please check the VIN format (17 characters) and try again"
- 🔍 No Results: "No records found matching your criteria"
- ⚠️ Data Limits: "Showing top 10 results - add filters to refine"

**Security**:
- 🔒 Read-only access enforced
- 🚫 Block any modification attempts (INSERT/UPDATE/DELETE)

don't show the column names if there are no values in the table
- 🚫 Block any SQL injection attempts (e.g., "DROP TABLE", "SELECT * FROM users")
- 🔒 No sensitive data exposure (e.g., passwords, personal info)
- 🚫 Block any attempts to access system tables or metadata 


Don't remember to start with question to user:
    How can I assist with your dealership operations today? Please choose an option (1-6):
    and present these 6 options first
"""

# Create a chat-based prompt with system instructions
chat_prompt = ChatPromptTemplate.from_messages([
    SystemMessagePromptTemplate.from_template(system_template),
    HumanMessagePromptTemplate.from_template("{input}")
])

toolkit = SQLDatabaseToolkit(db=db, llm=llm)

# SQL Agent configuration
agent = create_sql_agent(
    llm=llm,
    toolkit=toolkit,
    verbose=True,
    agent_type=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
    top_k=10,
    max_iterations=20,         # default is 15, increase as needed
    max_execution_time=60)

# Chat interface
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": """How can I assist with your dealership operations today?\n 
1️⃣ Sales Report (Last 30 Days)\n
2️⃣ Find Customer Purchase History\n
3️⃣ Search Available Cars by Criteria\n
4️⃣ Employee Performance Summary\n
5️⃣ Service History for Vehicle\n
6️⃣ Exit"""}]

for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["content"])

if prompt := st.chat_input("Your question about dealership operations"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.chat_message("user").write(prompt)

    with st.chat_message("assistant"):
        with st.spinner("🤖 Thinking... fetching data from the dealership database..."):
            response = agent.run(prompt)
            time.sleep(0.5)  # Just a slight delay for natural feel
        st.session_state.messages.append({"role": "assistant", "content": response})
        st.write(response)
