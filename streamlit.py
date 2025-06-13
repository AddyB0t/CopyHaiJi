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

# Use columns to place chat on the left and upload on the right
col1, col2 = st.columns([2, 1])

with col1:
    st.title("📚 Document Chatbot")
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])

    if prompt := st.chat_input("Ask a question about your document..."):
        st.chat_message("user").markdown(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        try:
            chat_data = {
                "message": prompt,
                "hash_code": st.session_state.current_hash_code
            }
            
            with st.spinner("Getting response..."):
                que = requests.post("https://dominant-splendid-airedale.ngrok-free.app/chat/", json=chat_data)
                response_data = que.json()
                
                if que.status_code == 200:
                    response = response_data.get('response', 'No response received')
                    
                    with st.chat_message("assistant"):
                        st.markdown(response)
                    st.session_state.messages.append({"role": "assistant", "content": response})
                else:
                    st.error(f"Error: {response_data.get('detail', 'Unknown error')}")
        
        except Exception as e:
            st.error(f"Error getting response: {str(e)}")

with col2:
    with st.container():
        st.markdown('<div class="upload-hover-box">', unsafe_allow_html=True)
        st.subheader("📄 Upload Document")
        uploaded_file = st.file_uploader("Choose a file", type=['txt', 'pdf', 'csv', 'md'])
        
        if uploaded_file is not None:
            try:
                os.makedirs("uploads", exist_ok=True)
                file_path = os.path.join("uploads", uploaded_file.name)
                with open(file_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                
                files = {'file': (uploaded_file.name, open(file_path, 'rb'), uploaded_file.type)}
                data = {
                    'chunk_size': 500,
                    'chunk_overlap': 200
                }
                
                with st.spinner("Uploading and processing document..."):
                    r = requests.post("https://dominant-splendid-airedale.ngrok-free.app/upload-document/", files=files, data=data)
                    response = r.json()
                    
                    hash_code = None
                    already_exists = False

                    if r.status_code == 200:
                        if 'file_info' in response:
                            hash_code = response['file_info'].get('hash_code')
                            already_exists = response['file_info'].get('existing', False)
                            embedding_id = response['file_info'].get('embedding_id') or response['file_info'].get('db_id')
                        else:
                            hash_code = response.get('hash_code')
                            already_exists = response.get('existing', False)
                            embedding_id = response.get('embedding_id') or response.get('db_id')

                        if not hash_code and embedding_id is not None:
                            details_resp = requests.get(f"https://dominant-splendid-airedale.ngrok-free.app/documents/{embedding_id}")
                            if details_resp.status_code == 200:
                                details = details_resp.json()
                                hash_code = details.get('hash_code')
                            else:
                                st.warning("Could not retrieve document details to get hash code.")

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
                
                os.remove(file_path)
                
            except Exception as e:
                st.error(f"Error uploading document: {str(e)}")
                if 'file_path' in locals() and os.path.exists(file_path):
                    os.remove(file_path)

        if st.session_state.current_hash_code:
            st.info(f"**Current Document Hash Code:** {st.session_state.current_hash_code}")
        st.markdown('</div>', unsafe_allow_html=True)

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
    .upload-hover-box {
        transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1), box-shadow 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        transform: scale(0.85);
        box-shadow: 0 2px 8px rgba(0,0,0,0.12);
        border-radius: 16px;
        padding: 8px 0 8px 0;
    }
    .upload-hover-box:hover {
        transform: scale(1.08);
        box-shadow: 0 8px 32px rgba(0,0,0,0.18);
        background: rgba(40,40,40,0.98);
    }
</style>
""", unsafe_allow_html=True)

