import httpx
from openai import AzureOpenAI
import streamlit as st

st.title("Selective RAG Chatbot")
st.sidebar.header("Selective RAG Chatbot")

#TODO: add list of selected documents to sidebar?

# Initialisation
system_msg = "You are a helpful assistant that provides information based on the provided database."
intro_msg = "Hello! Ask me about your uploaded documents!"
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "system", "content": system_msg},
                                {"role": "assistant", "content": intro_msg}]

# Connect to client
@st.cache_resource
def get_client():
    return AzureOpenAI(  
        azure_endpoint=st.secrets["AZURE_AI_ENDPOINT"],  
        api_key=st.secrets["AZURE_AI_API_KEY"],  
        api_version=st.secrets["AZURE_AI_API_VERSION"],
        http_client = httpx.Client(verify=False)
    )
client = get_client()

# Write all previous messages
for message in st.session_state.messages:
    if message["role"] == "system":
        continue
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Receive user input and generate a response
if prompt := st.chat_input("..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Send the prompt to the model and write the response
    with st.chat_message("assistant"):
        stream = client.chat.completions.create(
            model=st.secrets["AZURE_AI_CHAT_DEPLOYMENT"],
            messages=[
                {"role": m["role"], "content": m["content"]}
                for m in st.session_state.messages
            ],
            stream=True,
            extra_body={  
                "data_sources": [{  
                    "type": "azure_search",  
                    "parameters": {  
                        "endpoint": st.secrets["AZURE_AI_SEARCH_ENDPOINT"],  
                        "index_name": st.secrets["AZURE_AI_SEARCH_INDEX"],  
                        "authentication": {  
                            "type": "api_key",  
                            "key": st.secrets["AZURE_AI_SEARCH_API_KEY"]
                        } 
                    }  
                }]
            } 
        )
        response = st.write_stream(stream)
    st.session_state.messages.append({"role": "assistant", "content": response})