# set current directory to the main project directory
import os
import sys
import json

curr_dir = os.getcwd()
print("Current directory: ", curr_dir)

if curr_dir.split(os.sep)[-1] == "Incident-Copilot":
    print("Already Root directory, current directory: ", curr_dir)
else:
    while curr_dir.split(os.sep)[-1] != "Incident-Copilot":
        os.chdir("..")
        curr_dir = os.getcwd()

    print("Changed to Root directory: ", curr_dir)


from langchain_core.messages import ToolMessage

# importing llm related functions
from src.utils.llm_config import llm_instance

# importing prompt related functions
from src.utils.prompts.system_prompts import incident_rag_system_prompt
from src.utils.prompts.prompt_template import get_incident_rag_template
from src.data.sample_incident_queries import queries
from src.utils.rag.ingestion_funcs import ingestion_pipeline
from src.utils.rag.retrieval_funcs import retrieval_pipeline
from src.utils.tools import get_current_time, identify_service, get_logs, get_metrics

# importing dotenv to load environment variables
from dotenv import load_dotenv
load_dotenv()

def main():

    # Get the incident prompt template
    incident_rag_prompt_template = get_incident_rag_template(incident_rag_system_prompt)

    # run the ingestion pipeline to ingest the documents into the vector database
    vectordb_instance = ingestion_pipeline(data_folders=["corpus"], exclude_files=["sources.md"])

    # getting the tools to be used by the LLM for retrieval and analysis
    tools = [get_current_time, identify_service, get_logs, get_metrics]
    TOOL_MAP = {tool.name: tool for tool in tools} # tool map for dispatching tool calls

    # Initialize the LLM instance
    llm = llm_instance(api_key=os.getenv("GROQ_API_KEY")).bind_tools(tools, parallel_tool_calls = False)

    # Get the sample incident queries for dry run
    incident_queries = [queries[4]]

    for incident_query in incident_queries:

        # run the retrieval pipeline to get relevant context for the incident query
        retrieved_context = retrieval_pipeline(query=incident_query, vector_store=vectordb_instance, collection_name="incident_corpus")

        print(f"\n{'=' * 50}")
        print("\nIncident Query: ", incident_query)

        # build the initial message list (system + human w/ retrieved context)
        messages = incident_rag_prompt_template.format_messages(
            incident_query=incident_query,
            retrieved_context=retrieved_context,
        )

        # agent loop: keep calling the LLM until it stops requesting tools
        final_answer = None
        max_iterations = 5

        for iteration in range(1, max_iterations + 1):
            response = llm.invoke(messages)
            messages.append(response)  # AIMessage, possibly carrying tool_calls

            if not response.tool_calls:
                final_answer = response.content
                break

            print(f"\nIteration #{iteration}")
            for tool_call in response.tool_calls:
                tool_fn = TOOL_MAP[tool_call["name"]]
                result = tool_fn.invoke(tool_call["args"])

                messages.append(ToolMessage(
                    content=json.dumps(result),
                    tool_call_id=tool_call["id"],
                ))
                print(f"  [tool] {tool_call['name']}({tool_call['args']}) -> {result}")
        else:
            final_answer = "Reached max iterations without a final answer."

        # Print the response
        print("\nLLM Response:\n", final_answer)


if __name__ == "__main__":
    main()
