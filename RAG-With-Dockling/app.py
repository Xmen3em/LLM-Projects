import os
import gc
import tempfile
import uuid
import pandas as pd

from llama_index.core import Settings
from llama_index.core import PromptTemplate
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader
from llama_index.readers.docling import DoclingReader
from llama_index.core.node_parser import MarkdownNodeParser
from llama_index.llms.groq import Groq

import streamlit as st
from dotenv import load_dotenv
load_dotenv()

os.environ["HF_API_KEY"] = os.getenv("HF_API_KEY")

# Get Groq API key from environment variables
groq_api_key = os.getenv("groq_api_key")
if not groq_api_key:
    st.error("GROQ_API_KEY not found in environment variables. Please add it to your .env file.")
    st.stop()

if "id" not in st.session_state:
    st.session_state.id = uuid.uuid4()
    st.session_state.file_cache = {}

session_id = st.session_state.id
client = None

# Add these CSS styles at the top of the app, after the imports
def add_custom_css():
    st.markdown("""
    <style>
    .chat-message {
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
        display: flex;
        flex-direction: column;
    }
    .chat-message.user {
        background-color: #f0f2f6;
    }
    .chat-message.assistant {
        background-color: #e6f3ff;
        border-left: 5px solid #0078ff;
    }
    .chat-message .avatar {
        width: 40px;
        height: 40px;
        border-radius: 50%;
        object-fit: cover;
        margin-right: 1rem;
    }
    .chat-message .message {
        flex: 1;
    }
    .stApp {
        max-width: 1200px;
        margin: 0 auto;
    }
    .blinking-cursor {
        display: inline-block;
        animation: blink 1s step-end infinite;
    }
    @keyframes blink {
        50% { opacity: 0; }
    }
    code {
        background-color: #f8f8f8;
        border-radius: 3px;
        padding: 0.2em 0.4em;
        font-family: monospace;
    }
    pre {
        background-color: #f8f8f8;
        border-radius: 3px;
        padding: 1em;
        overflow: auto;
    }
    </style>
    """, unsafe_allow_html=True)

# Call this function at the beginning
add_custom_css()

@st.cache_resource
def load_llm():
    # Using Groq with LLama 3 model instead of Ollama
    # Configure with proper context window parameters
    return Groq(
        model="llama3-8b-8192", 
        api_key=groq_api_key,
        max_tokens=4000,  # Response token limit
        context_window=8192,  # Total context window size for llama3-8b-8192
        temperature=0.1  # Lower temperature for more deterministic answers
    )

@st.cache_resource
def load_embedding_model():
    # Use an embedding model from HuggingFace that doesn't require authentication
    from llama_index.embeddings.huggingface import HuggingFaceEmbedding
    
    try:
        # Use a small, reliable model that's commonly available without authentication
        return HuggingFaceEmbedding(
            model_name="sentence-transformers/all-MiniLM-L6-v2",
            trust_remote_code=False,  # For security
            embed_batch_size=10       # Process in small batches to reduce memory usage
        )
    except Exception as e:
        st.warning(f"Failed to load HuggingFace embedding model: {str(e)}")
        

def reset_chat():
    st.session_state.messages = []
    st.session_state.context = None
    gc.collect()


def display_excel(file):
    st.markdown("### Excel Preview")
    # Read the Excel file
    df = pd.read_excel(file)
    # Display the dataframe
    st.dataframe(df)


with st.sidebar:
    st.header(f"Add your documents!")
    
    uploaded_file = st.file_uploader("Choose your `.xlsx` file", type=["xlsx", "xls"])

    if uploaded_file:
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                file_path = os.path.join(temp_dir, uploaded_file.name)
                
                with open(file_path, "wb") as f:
                    f.write(uploaded_file.getvalue())
                
                file_key = f"{session_id}-{uploaded_file.name}"
                st.write("Indexing your document...")

                if file_key not in st.session_state.get('file_cache', {}):

                    if os.path.exists(temp_dir):
                            reader = DoclingReader()
                            loader = SimpleDirectoryReader(
                                input_dir=temp_dir,
                                file_extractor={".xlsx": reader},
                            )
                    else:    
                        st.error('Could not find the file you uploaded, please check again...')
                        st.stop()
                    
                    docs = loader.load_data()

                    # setup llm & embedding model
                    llm=load_llm()
                    embed_model = load_embedding_model()
                    # Creating an index over loaded data
                    Settings.embed_model = embed_model
                    
                    # Configure chunk size and overlap for better context management
                    from llama_index.core.node_parser import SentenceSplitter
                    node_parser = SentenceSplitter(
                        chunk_size=512,
                        chunk_overlap=50
                    )
                    
                    # Creating an index with the configured node parser
                    index = VectorStoreIndex.from_documents(
                        documents=docs, 
                        transformations=[node_parser],
                        show_progress=True
                    )
                    
                    # Configure the retriever for more conservative token usage
                    retriever = index.as_retriever(
                        similarity_top_k=3  # Reduce number of retrieved chunks
                    )
                    
                    # ====== Customise prompt template ======
                    qa_prompt_tmpl_str = (
                    "Context information is below.\n"
                    "---------------------\n"
                    "{context_str}\n"
                    "---------------------\n"
                    "Given the context information above I want you to think step by step to answer the query in a highly precise and crisp manner focused on the final answer, incase case you don't know the answer say 'I don't know!'.\n"
                    "Query: {query_str}\n"
                    "Answer: "
                    )
                    qa_prompt_tmpl = PromptTemplate(qa_prompt_tmpl_str)

                    # Create query engine with explicit token limits
                    from llama_index.core.response_synthesizers import CompactAndRefine
                    
                    # Set the LLM in Settings for the query engine
                    Settings.llm = llm
                    
                    # Create response synthesizer
                    response_synthesizer = CompactAndRefine(
                        text_qa_template=qa_prompt_tmpl,
                        streaming=True,
                    )
                    
                    # Create query engine directly from retriever to avoid parameter conflict
                    from llama_index.core.query_engine import RetrieverQueryEngine
                    query_engine = RetrieverQueryEngine(
                        retriever=retriever,
                        response_synthesizer=response_synthesizer,
                    )

                    # No need to update prompts as we've already set it in the response synthesizer
                    # query_engine.update_prompts(
                    #    {"response_synthesizer:text_qa_template": qa_prompt_tmpl}
                    # )
                    
                    st.session_state.file_cache[file_key] = query_engine
                else:
                    query_engine = st.session_state.file_cache[file_key]

                # Inform the user that the file is processed and Display the PDF uploaded
                st.success("Ready to Chat!")
                display_excel(uploaded_file)
        except Exception as e:
            st.error(f"An error occurred: {e}")
            st.stop()     

col1, col2 = st.columns([6, 1])

with col1:
    st.header(f"RAG over Excel using Dockling 🐥 & Llama-3")
    # Add a descriptive subheader
    st.markdown("📊 *Upload an Excel file and ask questions about its contents*")

with col2:
    st.button("Clear Chat ↺", on_click=reset_chat)

# Initialize chat history
if "messages" not in st.session_state:
    reset_chat()

# Display chat messages from history on app rerun
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Helper function to process and format the response for better display
def process_response(text):
    """Process the response text to improve formatting."""
    # Ensure code blocks are properly formatted
    if "```" in text:
        # Enhance code block styling
        text = text.replace("```python", '<pre><code class="language-python">')
        text = text.replace("```", '</code></pre>')
    
    # Enhance list formatting
    lines = text.split('\n')
    for i, line in enumerate(lines):
        # Improve bullet point appearance
        if line.strip().startswith('- '):
            lines[i] = '• ' + line.strip()[2:]
        # Enhance numbered lists
        elif line.strip() and line.strip()[0].isdigit() and '. ' in line:
            num, content = line.split('. ', 1)
            lines[i] = f"<strong>{num}.</strong> {content}"
    
    # Join the processed lines back into text
    return '\n'.join(lines)

# Accept user input
if prompt := st.chat_input("Ask a question about your data..."):
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})
    # Display user message in chat message container
    with st.chat_message("user"):
        st.markdown(prompt)

    # Display assistant response in chat message container
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""
        
        # Create a better loading indicator
        with st.spinner("Thinking..."):
            # Process the streaming response
            streaming_response = query_engine.query(prompt)
            
            for chunk in streaming_response.response_gen:
                full_response += chunk
                # Format the response with a blinking cursor
                formatted_response = full_response + '<span class="blinking-cursor">▌</span>'
                message_placeholder.markdown(formatted_response, unsafe_allow_html=True)
        
        # Format the final response for better readability
        # Remove the cursor and apply final formatting
        formatted_final = process_response(full_response)
        message_placeholder.markdown(formatted_final, unsafe_allow_html=True)

    # Add assistant response to chat history
    st.session_state.messages.append({"role": "assistant", "content": full_response})