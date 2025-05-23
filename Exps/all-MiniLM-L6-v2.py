import streamlit as st
from langchain_groq import ChatGroq
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.chains import create_retrieval_chain
from langchain_core.prompts import ChatPromptTemplate
from langchain_community.document_loaders import PyPDFDirectoryLoader
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
import os
from dotenv import load_dotenv

load_dotenv()
HF_API_KEY = os.getenv("HF_API_KEY")
qroq_api = os.getenv("groq_api_key")

llm = ChatGroq(model_name = 'Llama3-8b-8192')

prompt = ChatPromptTemplate.from_template(
    """
    Answer the questions based on the provided context only.
    Please provide the most accurate respone based on the question
    <context>
    {context}
    <context>
    Question:{input}
    """
)

def get_embedding():
    if 'vectors' not in st.session_state:
        try:
            # Initialize the embeddings model
            st.session_state.embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
            
            # Check if Paper.pdf exists
            import os
            if not os.path.exists('Paper.pdf'):
                st.error("Paper.pdf not found in the current directory!")
                return
                
            # Use PyPDFLoader instead of PyPDFDirectoryLoader since we're working with a single file
            from langchain_community.document_loaders import PyPDFLoader
            st.session_state.loaders = PyPDFLoader('Paper.pdf')
            st.session_state.docs = st.session_state.loaders.load()
            
            if not st.session_state.docs:
                st.error("No content could be extracted from the PDF file!")
                return
                
            st.session_state.text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
            st.session_state.final_docs = st.session_state.text_splitter.split_documents(st.session_state.docs)
            
            if not st.session_state.final_docs:
                st.error("No documents after splitting!")
                return
                
            # Create FAISS index
            st.session_state.vectors = FAISS.from_documents(st.session_state.final_docs, st.session_state.embeddings)
            st.success("Document embedding completed successfully!")
        except Exception as e:
            st.error(f"Error creating embeddings: {str(e)}")
            import traceback
            st.error(traceback.format_exc())
        
st.title("all-MiniLM-L6-v2")

user_input = st.text_input("Enter your Query from the research papers")

if st.button("Document Embeddings"):
    get_embedding()
    if 'vectors' in st.session_state:
        st.write("Document Embeddings are ready")

if user_input:
    if 'vectors' not in st.session_state:
        st.error("Please create document embeddings first by clicking the 'Document Embeddings' button")
    else:
        try:
            first_chain = create_stuff_documents_chain(llm, prompt)
            retreivals = st.session_state.vectors.as_retriever()
            chain = create_retrieval_chain(retreivals, first_chain)
        
            response = chain.invoke({"input": user_input})
            
            st.write(response["answer"])
            
            with st.expander("Show Context"):
                for i, doc in enumerate(response["context"]):
                    st.write(f"Document {i}")
                    st.write(doc.page_content)
        except Exception as e:
            st.error(f"Error during query processing: {str(e)}")
            import traceback
            st.error(traceback.format_exc())