import streamlit as st
from datetime import datetime
from azure.storage.blob import BlobServiceClient

st.title("Document Selection")
st.sidebar.header("Document Selection")

#TODO: choose which blob container to use
#TODO: uploading the same docmument?
system_msg = st.sidebar.text_area("System Message (Changes will clear history)", value="You are a helpful assistant that provides information based on the provided database.")

# Initialize blob client
@st.cache_resource
def get_blob_service_client():
    return BlobServiceClient.from_connection_string(st.secrets["AZURE_STORAGE_CONNECTION_STRING"])
blob_service_client = get_blob_service_client()
container_name = "rag-storage"

# List blobs in the container
def list_blobs():
    container_client = blob_service_client.get_container_client(container_name)
    blob_list = container_client.list_blobs()
    return [blob.name for blob in blob_list]

# Upload a file to the container
def upload_blob(file):
    blob_client = blob_service_client.get_blob_client(container=container_name, blob=file.name)
    blob_client.upload_blob(file, metadata = {"timestamp": datetime.now().isoformat()})
    st.success(f"Uploaded {file.name}")

# Delete a blob from the container
def delete_blob(blob_name):
    blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob_name)
    blob_client.delete_blob()
    st.success(f"Deleted {blob_name}")

# Display list of blobs that the user has uploaded
blobs = list_blobs()
selected_blobs = st.multiselect("Select documents to delete", blobs)

# File uploader
uploaded_file = st.file_uploader("Upload a document")

# Upload button
if uploaded_file and st.button("Upload"):
    upload_blob(uploaded_file)

# Delete button
if selected_blobs and st.button("Delete selected"):
    for blob_name in selected_blobs:
        delete_blob(blob_name)