import streamlit as st
import requests
import json
import os
from pathlib import Path

# Set page config
st.set_page_config(
    page_title="Document Chatbot",
    page_icon="🤖",
    layout="wide"
)

# Initialize session state for chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Initialize session state for current document hash_code
if "current_hash_code" not in st.session_state:
    st.session_state.current_hash_code = None

# Sidebar for document upload
with st.sidebar:
    # Document upload section
    st.subheader("📄 Upload Document")
    uploaded_file = st.file_uploader("Choose a file", type=['txt', 'pdf', 'csv', 'md'])
    
    if uploaded_file is not None:
        try:
            # Create uploads directory if it doesn't exist
            os.makedirs("uploads", exist_ok=True)
            
            # Save the uploaded file temporarily
            file_path = os.path.join("uploads", uploaded_file.name)
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            # Prepare the file for upload
            files = {'file': (uploaded_file.name, open(file_path, 'rb'), uploaded_file.type)}
            data = {
                'chunk_size': 500,
                'chunk_overlap': 200
            }
            
            # Send to FastAPI endpoint
            with st.spinner("Uploading and processing document..."):
                r = requests.post("http://127.0.0.1:8000/upload-document/", files=files, data=data)
                response = r.json()
                
                # Try to get hash_code and existence info
                hash_code = None
                already_exists = False

                if r.status_code == 200:
                    # Unified handling whether 'file_info' nested or flat
                    if 'file_info' in response:
                        hash_code = response['file_info'].get('hash_code')
                        already_exists = response['file_info'].get('existing', False)
                        embedding_id = response['file_info'].get('embedding_id') or response['file_info'].get('db_id')
                    else:
                        hash_code = response.get('hash_code')
                        already_exists = response.get('existing', False)
                        embedding_id = response.get('embedding_id') or response.get('db_id')

                    # If hash_code still missing but we have embedding_id, fetch details from backend
                    if not hash_code and embedding_id is not None:
                        details_resp = requests.get(f"http://127.0.0.1:8000/documents/{embedding_id}")
                        if details_resp.status_code == 200:
                            details = details_resp.json()
                            hash_code = details.get('hash_code')
                            # Determine if document existed before based on is_active flag and created_at? If the endpoint worked, already_exists True if id existed before upload
                        else:
                            st.warning("Could not retrieve document details to get hash code.")

                    # Show appropriate message
                    if hash_code:
                        st.session_state.current_hash_code = hash_code
                        if already_exists:
                            st.info(f"Document already exists! Hash Code: {hash_code}")
                        else:
                            st.success(f"Document processed successfully! Hash Code: {hash_code}")
                    else:
                        st.error(f"Unexpected response, hash code not found: {response}")
                else:
                    st.error(f"Error uploading document: {response}")
            
            # Clean up temporary file
            os.remove(file_path)
            
        except Exception as e:
            st.error(f"Error uploading document: {str(e)}")
            if 'file_path' in locals() and os.path.exists(file_path):
                os.remove(file_path)

    # Display the hash_code if available
    if st.session_state.current_hash_code:
        st.info(f"**Current Document Hash Code:** {st.session_state.current_hash_code}")

# Main chat interface
st.title("📚 Document Chatbot")

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])

# Chat input
if prompt := st.chat_input("Ask a question about your document..."):
    # Display user message in chat message container
    st.chat_message("user").markdown(prompt)
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    try:
        # Prepare chat request
        chat_data = {
            "message": prompt,
            "hash_code": st.session_state.current_hash_code
        }
        
        # Send request to chatbot API
        with st.spinner("Getting response..."):
            que = requests.post("http://127.0.0.1:8000/chat/", json=chat_data)
            response_data = que.json()
            
            if que.status_code == 200:
                response = response_data.get('response', 'No response received')
                
                # Display assistant response
                with st.chat_message("assistant"):
                    st.markdown(response)
                # Add assistant response to chat history
                st.session_state.messages.append({"role": "assistant", "content": response})
            else:
                st.error(f"Error: {response_data.get('detail', 'Unknown error')}")
        
    except Exception as e:
        st.error(f"Error getting response: {str(e)}")

# Add some styling
st.markdown("""
<style>
    .stApp {
        max-width: 1200px;
        margin: 0 auto;
    }
    .stButton>button {
        width: 100%;
    }
</style>
""", unsafe_allow_html=True)

