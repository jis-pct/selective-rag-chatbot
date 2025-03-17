import streamlit as st
from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient

st.title("Document Selection")
st.sidebar.header("Document Selection")

# 1. displays a list of documents in sharepoint/everything user has uploaded
# 2. user selects/deselects documents in the list
# 3. user clicks a button that adds/removes documents from storage, triggering indexation
# 4. (maybe) update the chatbot in the other page to reflect updates?

# Initialize blob client
@st.cache_resource
def get_blob_service_client():
    return BlobServiceClient.from_connection_string(st.secrets["AZURE_STORAGE_CONNECTION_STRING"])
blob_service_client = get_blob_service_client()
container_name = "birds"

# List blobs in the container
def list_blobs():
    container_client = blob_service_client.get_container_client(container_name)
    blob_list = container_client.list_blobs()
    return [blob.name for blob in blob_list]

# Upload a file to the container
def upload_blob(file):
    blob_client = blob_service_client.get_blob_client(container=container_name, blob=file.name)
    blob_client.upload_blob(file)
    st.success(f"Uploaded {file.name}")

# Delete a blob from the container
def delete_blob(blob_name):
    blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob_name)
    blob_client.delete_blob()
    st.success(f"Deleted {blob_name}")

# # Display list of blobs
# blobs = list_blobs()
# selected_blobs = st.multiselect("Select documents to delete", blobs)

# File uploader
uploaded_file = st.file_uploader("Upload a document")

# Upload button
if uploaded_file and st.button("Upload"):
    upload_blob(uploaded_file)

# # Delete button
# if selected_blobs and st.button("Delete selected"):
#     for blob_name in selected_blobs:
#         delete_blob(blob_name)