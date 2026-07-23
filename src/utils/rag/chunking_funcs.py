"""
This script has functions related to:
- identifying the files/corpus for the RAG pipeline
- parsing the files and extracting the text and metadata
- chunking the parsed text
- converting the chunks to documents for ingestion into the vector database 
"""


import os
import re
from pathlib import Path
from langchain_core.documents import Document

# function to get all file names from the specified data folders, excluding the specified files
def get_file_names(data_folders: list[str], exclude_files: list[str]):
    """
    Gets all file names from the specified data folders, excluding the specified files.

    Args:
        data_folders (list[str]): List of folders to search for files.
        exclude_files (list[str]): List of files to exclude.

    Returns:
        list[str]: List of file names found in the data folders, excluding the specified files.
    """

    # list to maintain all file names found in the data folders 
    file_names = []
    curr_dir = os.getcwd()

    # get all file names:
    for folder in data_folders:
        folder_path = os.path.join(curr_dir, "src", "data", folder)

        print(f"Reading files from folder: {folder_path}")
        if os.path.exists(folder_path):
            file_names = [f for f in os.listdir(folder_path) if os.path.isfile(os.path.join(folder_path, f)) and f not in exclude_files]

            # if no files found, then we go into sub-folders
            if not file_names:
                for subdir, _, files in os.walk(folder_path):
                    for file in files:
                        if file not in exclude_files:
                            file_names.append(os.path.join(subdir, file))
                            print(f"Found file in subfolder {{{subdir.split(os.sep)[-1]}}}: {file}")
                
            if not file_names:
                print(f"No files found in folder {folder_path} or its sub-folders.")

        else:
            print(f"Folder {folder} does not exist.") 

    print(f"\nTotal files found: {len(file_names)}")
    return file_names


# functions for extracting metadata and content from markdown files
def normalize_key(field: str) -> str:
    """
    Normalizes a string to be used as a dictionary key.
    Example:
        'Escalation Channel' -> 'escalation_channel'

    Args:
        field (str): The string to normalize.
    Returns:
        str: The normalized string suitable for use as a dictionary key.
    """

    # Replace spaces and special characters with underscores, convert to lowercase, and strip leading/trailing underscores
    return re.sub(r"[^a-z0-9]+", "_", field.strip().lower()).strip("_")

def extract_metadata(file_path: Path, corpus_root: Path) -> dict:
    """
    Extracts metadata from a markdown file, including the H1 title, a metadata table, and the document type based on the parent folder name.

    Args:
        file_path (Path): The path to the markdown file.
        corpus_root (Path): The root directory of the corpus, used to compute relative paths.
    Returns:
        dict: A dictionary containing the extracted metadata, including title, doc_type, source_file,
    """

    # Read the file content
    text = file_path.read_text(encoding="utf-8")

    # limiting the metadata extracting to the h1 section only
    h1_block = re.split(r"(?=^## )", text, maxsplit=1, flags=re.MULTILINE)[0]
    lines = h1_block.splitlines()

    # extract the H1 title (the first line that starts with "# ") or fallback to the filename stem if no title is found
    title = next((l[2:].strip() for l in lines if l.startswith("# ")), file_path.stem)

    # extract metadata table rows
    # regex to match table rows in the format "| Field | Value |"
    table_row = re.compile(r"^\|\s*(.+?)\s*\|\s*(.+?)\s*\|$")
    
    # dictionary to hold the extracted metadata
    metadata: dict[str, str] = {}
    for line in lines:
        m = table_row.match(line.strip())
        if not m:
            continue
        field, value = m.group(1).strip(), m.group(2).strip()
        # skip the header row ("Field | Value") and separator row ("---|---")
        if field.lower() == "field" or set(field) <= {"-"}:
            continue
        metadata[normalize_key(field)] = value

    # mapping of folder names to document types
    folder_to_doc_type = {
        "runbooks": "runbook",
        "postmortems": "postmortem",
        "code_docs": "code_doc",
    }

    # get the document type from the parent folder name, defaulting to the folder name itself if not in the mapping
    doc_type = folder_to_doc_type.get(file_path.parent.name, file_path.parent.name)

    return {
        "title": title,
        "doc_type": doc_type,
        "source_file": str(file_path.relative_to(corpus_root.parent)),
        **metadata,
    }

def parse_file_into_chunks(file_path: Path):
    """
    Parses and extracts the content of a markdown file into chunks, including metadata.

    Args:
        file_path (Path): The path to the markdown file.

    Returns:
        dict: A dictionary containing the extracted metadata under the key "metadata" and a list of text chunks under the key "chunks".
    """

    text = file_path.read_text(encoding="utf-8")

    metadata = extract_metadata(file_path, corpus_root=file_path.parent)

    # list to hold the extracted chunks of text
    chunks = []

    # extracting chunk from h2 section
    h2_section = text.split("## ")[1:]  # need to skip the first because it is the h1 section
    chunks.extend(h2_section)

    extracted_data = {
        "metadata": metadata,
        "chunks": chunks
    }

    return extracted_data


# function to create Document objects from the extracted chunks and metadata
def create_documents_from_chunks(chunks_dict: dict) -> list[Document]:
    """
    Creates a list of Document objects from the provided chunks dictionary.

    Args:
        chunks_dict (dict): A dictionary where keys are file names and values are dictionaries containing metadata and chunks.

    Returns:
        list[Document]: A list of Document objects created from the chunks.
    """

    documents = []
    
    # iterate through the chunks_dict to create Document objects
    for file_name, file_data in chunks_dict.items():
        file_metadata = file_data["metadata"]
    
        # iterate through the chunks in the file_data to create Document objects
        for raw_chunk in file_data["chunks"]:
            # first line is section heading, rest is the body
            heading, _, body = raw_chunk.partition("\n") # extract the heading and body
            heading = heading.strip() 
            body = body.strip()

            # if the body is empty, skip this chunk
            if not body: 
                continue

            # create the page content by combining the title(it was the header of the file), heading, and body
            page_content = f"{file_metadata['title']} — {heading}\n\n{body}"

            # create the chunk metadata by combining the file metadata and the section heading
            chunk_metadata = {
                **file_metadata,
                "section": heading,
            }

            # create a unique document ID by combining the file name and normalized section heading
            doc_id = f"{file_name}::{normalize_key(heading)}"

            # create a Document object and append it to the documents list
            documents.append(Document(page_content=page_content, metadata=chunk_metadata, id=doc_id))

    return documents