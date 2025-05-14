import streamlit as st
from langchain_groq import ChatGroq
from langchain_community.utilities import WikipediaAPIWrapper
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain, LLMMathChain
from langchain.agents import initialize_agent, Tool
from langchain.agents.agent_types import AgentType
from langchain.callbacks import StreamlitCallbackHandler
from dotenv import load_dotenv
import os

load_dotenv()
os.environ["groq_api_key"] = os.getenv("groq_api_key")

# define the congiguration for the streamlit app
st.set_page_config(page_title="Text to Math Problem Solver", page_icon="👨‍🔬🧮")
st.title("Text to Math Problem Solver")
st.write(
    "This app uses the Groq LLM to convert text into math problems. It can also solve math problems and provide explanations."
)

# define the llm model
llm = ChatGroq(model_name = 'gemma2-9b-it', )

# define the tools
wikipedia_wrapper = WikipediaAPIWrapper()
wikipedia_tool = Tool(
    name = 'wikipedia',
    func = wikipedia_wrapper.run, 
    description = "A tool for Searching the Internet to find the various information on the topics mentioned"
)

# define the math tool
math_llm = LLMMathChain.from_llm(llm=llm)
calculator = Tool(
    name = 'Calculator',
    func = math_llm.run,
    description= 'A tool for answering math related questions. Only input Mathematical expression need to be provided'
)

# define the prompt
prompt = """
    Your are an agent tasked for solving users mathematical questions, 
Logically arrive at the solution and provide a detailed explanation and display it point wise for the qustion below.
Question : {input}
Answer:
"""
prompt_template = PromptTemplate(
    input_variables = ["input"],
    template = prompt
)

# define the reasoning tool
chain = LLMChain(llm=llm, prompt=prompt_template)
reasoning_tool = Tool(
    name = 'reasoning tool',
    func = chain.run,
    description = 'A tool for answering logic-based and reasoning qustions.'
)

# define the agents
assistant = initialize_agent(
    tools = [wikipedia_tool, calculator, reasoning_tool],
    llm = llm,
    agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
    verbose = False,
    handle_parsing_errors = True
)

if "messages" not in st.session_state:
    st.session_state["messages"]=[
        {"role":"assistant","content":"Hi, I'm a MAth chatbot who can answer all your maths questions"}
    ]

for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg['content'])

## Lets start the interaction
question=st.text_area("Enter youe question:","I have 5 bananas and 7 grapes. I eat 2 bananas and give away 3 grapes. Then I buy a dozen apples and 2 packs of blueberries. Each pack of blueberries contains 25 berries. How many total pieces of fruit do I have at the end?")

if st.button("find my answer"):
    if question:
        with st.spinner("Generate response.."):
            st.session_state.messages.append({"role":"user","content":question})
            st.chat_message("user").write(question)

            st_cb=StreamlitCallbackHandler(st.container(),expand_new_thoughts=False)
            
            response = assistant.run(st.session_state.messages,callbacks=[st_cb]
                                         )
            st.session_state.messages.append({'role':'assistant',"content":response})
            st.write('### Response:')
            st.success(response)

    else:
        st.warning("Please enter the question")

# This code is a Streamlit app that uses the Groq LLM to convert text into math problems and solve them. It also provides explanations for the solutions.