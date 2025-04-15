import httpx
from openai import AzureOpenAI, BadRequestError
from dotenv import load_dotenv
import streamlit as st
import re
import os

load_dotenv()

st.title("Selective RAG Chatbot")
st.sidebar.header("Selective RAG Chatbot")

# Connect to client
@st.cache_resource
def get_client():
    return AzureOpenAI(  
        azure_endpoint=os.environ["AZURE_AI_ENDPOINT"],  
        api_key=os.environ["AZURE_AI_API_KEY"],  
        api_version=os.environ["AZURE_AI_API_VERSION"],
        http_client = httpx.Client(verify=False)
    )
client = get_client()

# Check validity of the given index name
def check_index_name(name):
    try:
        client.chat.completions.create(
            model=os.environ["AZURE_AI_CHAT_DEPLOYMENT"],
            messages=[{"role": "user", "content": "What is in your database?"}],
            max_tokens=1,
            extra_body={  
                "data_sources": [{  
                    "type": "azure_search",  
                    "parameters": {  
                        "endpoint": os.environ["AZURE_AI_SEARCH_ENDPOINT"],  
                        "index_name": name,  
                        "authentication": {  
                            "type": "api_key",  
                            "key": os.environ["AZURE_AI_SEARCH_API_KEY"]
                        }
                    }  
                }]
            } 
        )
    except BadRequestError as e:
        st.sidebar.error(f"Index '{name}' is not valid.")

# Display response with proper citations
def display_chatbot_response(content, citation_list):
    def citation_replacer(res, citation_list):
        return re.sub(r"\[doc\d+\]", lambda x: '[' + citation_list[int(x.group()[4:-1]) - 1] + ']', res)
    def duplicate_citation_remover(res):
        return re.sub(r"(\[\[.+\]\(.+\)\])\1+", r'\1', res)
    st.markdown(duplicate_citation_remover(citation_replacer(content, citation_list)))

# Sidebar inputs for system message and other parameters
system_msg = st.sidebar.text_area("System Message (Changes will clear history)", value=
"""You are an AI assistant that helps users find information. \
Please answer using retrieved documents only \
and without using your own knowledge. Generate citations to retrieved documents for \
every claim in your response. Do not answer using your own knowledge.""")
index_name = st.sidebar.text_input("Index Name", value="rag-storage")
check_index_name(index_name) #TODO: network doesnt let me retrieve list of indexes

# Search parameters
st.sidebar.header("Search Parameters")
scope = st.sidebar.checkbox("Limit responses to data content", value = True)
strictness = st.sidebar.slider("Strictness", min_value=1, max_value=5, value=3)
top_n_documents = st.sidebar.slider("Retrieved documents", min_value=3, max_value=20, value=5)

# Model parameters
st.sidebar.header("Model Parameters")
past_messages_included = st.sidebar.slider("Past messages included", min_value=1, max_value=20, value=10)
max_response = st.sidebar.slider("Max response", min_value=1, max_value=16000, value=800)
temperature = st.sidebar.slider("Temperature", min_value=0.0, max_value=2.0, value=1.0)
top_p = st.sidebar.slider("Top P", min_value=0.0, max_value=1.0, value=0.95)
stop_phrase = [st.sidebar.text_input("Stop phrase")]
phrases = stop_phrase if stop_phrase[0] != '' else None
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
        if message["role"] == "user":
            st.markdown(message["content"])
        elif message["role"] == "assistant":
            display_chatbot_response(message["content"], message["citation_list"])

# Receive user input and generate a response
if prompt := st.chat_input("..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Send the prompt to the model and write the response
    response = client.chat.completions.create(
        model=os.environ["AZURE_AI_CHAT_DEPLOYMENT"],
        messages=[
            {"role": m["role"], "content": m["content"]}
            for m in st.session_state.messages
        ],
        max_tokens=max_response,
        temperature=temperature,
        stop=phrases,
        top_p=top_p,
        frequency_penalty=frequency_penalty,
        presence_penalty=presence_penalty,
        extra_body={  
            "data_sources": [{  
                "type": "azure_search",  
                "parameters": {  
                    "endpoint": os.environ["AZURE_AI_SEARCH_ENDPOINT"],  
                    "index_name": index_name, 
                    "semantic_configuration": f"{index_name}-semantic-configuration",
                    "query_type": "vector_semantic_hybrid",
                    "in_scope": scope,
                    "strictness": strictness,
                    "top_n_documents": top_n_documents,
                    "authentication": {  
                        "type": "api_key",  
                        "key": os.environ["AZURE_AI_SEARCH_API_KEY"]
                    },
                    "fields_mapping": {
                        "content_fields_separator": "\\n",
                        "title_field": "title",
                        "url_field": "url"
                    },
                    "embedding_dependency": {
                        "type": "deployment_name",
                        "deployment_name": os.environ["AZURE_AI_EMBEDDING_NAME"]
                    }
                }  
            }]
        } 
    )

    # Show response and add to chat history
    citation_list = [f"[{x['title']}]({x["url"]})" for x in response.choices[0].message.context['citations']]
    with st.chat_message("assistant"):
        display_chatbot_response(response.choices[0].message.content, citation_list)
    st.session_state.messages.append({"role": "assistant", "content": response.choices[0].message.content, "citation_list": citation_list})