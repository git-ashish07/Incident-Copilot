"""
This script has functions related to:
- initializng vector database
- ingesting documents into the vector database
"""

import os
from pathlib import Path
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma

# importing supporting functions from other modules
from src.utils.llm_config import embedding_instance
from src.utils.rag.chunking_funcs import get_file_names, parse_file_into_chunks, create_documents_from_chunks

# function that will trigger the entire ingestion pipeline, including chunking, embedding, and storing the documents in the vector database
def ingestion_pipeline(data_folders: list[str], exclude_files: list[str]) -> Chroma:
    """
    Runs the entire ingestion pipeline, including chunking, embedding, and storing the documents in the vector database.
    
    Args:
        data_folders (list[str]): List of folders to search for files to ingest.
        exclude_files (list[str]): List of files to exclude from ingestion.
    Returns:
        vector_store: An instance of the Chroma vector database containing the ingested documents.
    """

    # get the file names from the specified data folders, excluding the specified files
    file_names = get_file_names(data_folders=data_folders, exclude_files=exclude_files)

    # parse the file content, convert it into chunks, and store the chunks in a dictionary with the file name as the key
    chunks_dict = {}

    for file_name in file_names:
        file_data_dict = parse_file_into_chunks(Path(file_name))
        f_name = file_name.split(os.sep)[-1]
        chunks_dict[f_name] = file_data_dict

    # converting the chunks into Document objects for ingestion into the vector database
    documents = create_documents_from_chunks(chunks_dict)

    ## Now we need to ingest the chunks into the vector database 
    
    # get the current working directory and set the persist directory for the vector store
    vector_store = get_vector_store(collection_name="incident_corpus")

    # ingest the documents into the vector database
    ingest_documents(vector_store=vector_store, documents=documents)

    return vector_store

# function to initialize the vector database
def get_vector_store(collection_name: str):
    """
    Initializes a vector database using Chroma with the specified collection name and embeddings.
    
    Args:
        collection_name (str): The name of the collection in the vector database.
         
    Returns:
        vector_store (Chroma): An instance of the Chroma vector database initialized with the provided parameters.
    """
    
    # initialize the embedding model
    embeddings = embedding_instance()

    # Get the current working directory and set the persist directory for the vector store
    curr_dir = os.getcwd()
    persist_directory = os.path.join(curr_dir, "src", "data", "vector_store")

    # Initialize the Chroma vectordb instance with the specified collection name, embeddings, and persist directory
    vector_store = Chroma(
        collection_name = collection_name,
        embedding_function = embeddings,
        persist_directory = persist_directory,
        collection_metadata = {"hnsw:space": "cosine"}
    )

    return vector_store

# function to ingest documents into the vector database
def ingest_documents(vector_store: Chroma, documents: list) -> None:
    """
    Ingests only new documents into the specified vector store.
    
    Args:
        vector_store (Chroma): The vector store instance to ingest documents into.
        documents (list): A list of documents to be ingested.
    """

    # Get the document IDs for the documents to be ingested
    doc_ids = [doc.id for doc in documents]

    # Checking in vectordb which of these ids it already has
    existing = vector_store.get(ids=doc_ids)
    existing_ids = set(existing["ids"])

    # keep only the documents whose id ISN'T already in the collection
    new_documents = [doc for doc in documents if doc.id not in existing_ids]

    # if no new documents to ingest, print a message and return
    if not new_documents:
        print(f"Nothing to ingest — all {len(documents)} chunks already exist.")
        return

    # if there are new documents to ingest, get their IDs
    new_ids = [doc.id for doc in new_documents]

    # Ingest the documents into the vector store
    vector_store.add_documents(new_documents, ids=new_ids)

    print(f"Stored {len(new_documents)} documents in the vector database.")


