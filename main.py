# set current directory to the main project directory
import os

curr_dir = os.getcwd()
print("Current directory: ", curr_dir)

if curr_dir.split(os.sep)[-1] == "Incident-Copilot":
    print("Already Root directory, current directory: ", curr_dir)
else:
    while curr_dir.split(os.sep)[-1] != "Incident-Copilot":
        os.chdir("..")
        curr_dir = os.getcwd()

    print("Changed to Root directory: ", curr_dir)


# importing llm related functions
from src.llm_funcs.llm_config import llm_instance

# importing prompt related functions
from src.prompts.system_prompts import incident_general_system_prompt, incident_rag_system_prompt
from src.prompts.prompt_template import get_incident_prompt_template, get_incident_rag_template
from src.data.sample_incident_queries import queries
from src.utils.rag.ingestion_funcs import ingestion_pipeline
from src.utils.rag.retrieval_funcs import retrieval_pipeline, format_retrieved_context

# importing dotenv to load environment variables
from dotenv import load_dotenv
load_dotenv()

def main():
    # Initialize the LLM instance
    llm = llm_instance(api_key=os.getenv("GROQ_API_KEY"))

    # Get the incident prompt template
    incident_rag_prompt_template = get_incident_rag_template(incident_rag_system_prompt)

    # run the ingestion pipeline to ingest the documents into the vector database
    vectordb_instance = ingestion_pipeline(data_folders=["corpus"], exclude_files=["sources.md"])

    # Get the sample incident queries for dry run
    incident_queries = queries

    for incident_query in incident_queries:

        # run the retrieval pipeline to get relevant context for the incident query
        retrieved_context = retrieval_pipeline(query=incident_query, vector_store=vectordb_instance, collection_name="incident_corpus")

        print(f"\n{'=' * 50}")
        print("\nIncident Query: ", incident_query)

        # Create a chain of the prompt template and the LLM
        incident_chain = incident_rag_prompt_template | llm

        # Generate a response from the LLM
        incident_response = incident_chain.invoke({"incident_query": incident_query, "retrieved_context": retrieved_context}).content

        # Print the response
        print("\nLLM Response:\n", incident_response)


if __name__ == "__main__":
    main()
