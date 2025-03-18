import httpx
from openai import AzureOpenAI, BadRequestError
import streamlit as st

st.title("Selective RAG Chatbot")
st.sidebar.header("Selective RAG Chatbot")

# MCP model context protocol

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

# Check validity of the given index name
def check_index_name(name):
    try:
        client.chat.completions.create(
            model=st.secrets["AZURE_AI_CHAT_DEPLOYMENT"],
            messages=[{"role": "user", "content": "What is in your database?"}],
            max_tokens=1,
            extra_body={  
                "data_sources": [{  
                    "type": "azure_search",  
                    "parameters": {  
                        "endpoint": st.secrets["AZURE_AI_SEARCH_ENDPOINT"],  
                        "index_name": name,  
                        "authentication": {  
                            "type": "api_key",  
                            "key": st.secrets["AZURE_AI_SEARCH_API_KEY"]
                        }
                    }  
                }]
            } 
        )
    except BadRequestError as e:
        st.sidebar.error(f"Index '{name}' is not valid.")

# Sidebar inputs for system message and other parameters
system_msg = st.sidebar.text_area("System Message (Changes will clear history)", value="You are a helpful assistant that provides information based on the provided database.")
index_name = st.sidebar.text_input("Index Name", value="rag-spike")
check_index_name(index_name)
past_messages_included = st.sidebar.slider("Past messages included", min_value=1, max_value=20, value=10)
max_response = st.sidebar.slider("Max response", min_value=1, max_value=16000, value=800)
temperature = st.sidebar.slider("Temperature", min_value=0.0, max_value=1.0, value=0.7)
top_p = st.sidebar.slider("Top P", min_value=0.0, max_value=1.0, value=0.95)
frequency_penalty = st.sidebar.slider("Frequency penalty", min_value=-2.0, max_value=2.0, value=0.0)
presence_penalty = st.sidebar.slider("Presence penalty", min_value=-2.0, max_value=2.0, value=0.0)

# Update System Message
if "messages" not in st.session_state or system_msg != st.session_state.messages[0]["content"]:
    st.session_state.messages = [{"role": "system", "content": system_msg}]

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
            max_tokens=max_response,
            temperature=temperature,
            top_p=top_p,
            frequency_penalty=frequency_penalty,
            presence_penalty=presence_penalty,
            extra_body={  
                "data_sources": [{  
                    "type": "azure_search",  
                    "parameters": {  
                        "endpoint": st.secrets["AZURE_AI_SEARCH_ENDPOINT"],  
                        "index_name": index_name,  
                        "authentication": {  
                            "type": "api_key",  
                            "key": st.secrets["AZURE_AI_SEARCH_API_KEY"]
                        }
                    }  
                }]
            } 
        )
        response = st.write_stream(stream)
        st.write(stream)
    st.session_state.messages.append({"role": "assistant", "content": response})