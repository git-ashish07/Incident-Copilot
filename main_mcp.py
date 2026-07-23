"""
This script shows how to run the tools through MCP framework.
"""

# set current directory to the main project directory
import os
import sys
import json
import asyncio

curr_dir = os.getcwd()
print("Current directory: ", curr_dir)

if curr_dir.split(os.sep)[-1] == "Incident-Copilot":
    print("Already Root directory, current directory: ", curr_dir)
else:
    while curr_dir.split(os.sep)[-1] != "Incident-Copilot":
        os.chdir("..")
        curr_dir = os.getcwd()

    print("Changed to Root directory: ", curr_dir)

import asyncio
import json
from langchain_core.messages import ToolMessage
from fastmcp import Client

# importing llm related functions
from src.utils.llm_config import llm_instance

# importing prompt related functions
from src.utils.prompts.system_prompts import incident_rag_system_prompt
from src.utils.prompts.prompt_template import get_incident_rag_template
from src.data.sample_incident_queries import queries
from src.utils.rag.ingestion_funcs import ingestion_pipeline
from src.utils.rag.retrieval_funcs import retrieval_pipeline
from src.utils.tools import mcp

# importing dotenv to load environment variables
from dotenv import load_dotenv
load_dotenv()

async def main():
    # Get the incident prompt template
    incident_rag_prompt_template = get_incident_rag_template(incident_rag_system_prompt)

    # run the ingestion pipeline to ingest the documents into the vector database
    vectordb_instance = ingestion_pipeline(data_folders=["corpus"], exclude_files=["sources.md"])

    # initialize the MCP client
    async with Client(mcp) as client:
        # get the list of tools registered with MCP
        mcp_tools = await client.list_tools()

        # create a list of tool schemas for the LLM to use
        tool_schemas = [
            {"type": "function", "function": {"name": t.name, "description": t.description or "", "parameters": t.inputSchema}}
            for t in mcp_tools
        ]

        # Initialize the LLM instance
        llm = llm_instance(api_key=os.getenv("GROQ_API_KEY")).bind_tools(tool_schemas, parallel_tool_calls=False)

        # Get the sample incident queries for dry run
        incident_queries = [queries[4]]

        for incident_query in incident_queries:

            # run the retrieval pipeline to get relevant context for the incident query
            retrieved_context = retrieval_pipeline(query=incident_query, vector_store=vectordb_instance, collection_name="incident_corpus")

            print(f"\n{'=' * 50}")
            print("\nIncident Query: ", incident_query)

            # build the initial message list (system + human w/ retrieved context)
            messages = incident_rag_prompt_template.format_messages(
                incident_query=incident_query, retrieved_context=retrieved_context,
            )

            # agent loop: keep calling the LLM until it stops requesting tools
            final_answer = None
            max_iterations = 5

            for iteration in range(1, max_iterations + 1):
                response = llm.invoke(messages)
                messages.append(response)  # AIMessage, possibly carrying tool_calls

                # check if the LLM has requested any tools to be called, if not, we have reached the final answer
                if not response.tool_calls:
                    final_answer = response.content
                    break

                # if the LLM has requested tools, we need to call those tools and append the results to the messages for the next iteration
                print(f"\nIteration #{iteration}")
                for tool_call in response.tool_calls:
                    result = await client.call_tool(tool_call["name"], tool_call["args"])
                    result_payload = result.data if result.data is not None else result.structured_content

                    # append the tool result to the messages for the next iteration
                    messages.append(ToolMessage(content=json.dumps(result_payload), tool_call_id=tool_call["id"]))
                    print(f"  [tool] {tool_call['name']}({tool_call['args']}) -> {result_payload}")
            else:
                final_answer = "Reached max iterations without a final answer."

            print("\nLLM Response:\n", final_answer)



if __name__ == "__main__":
    asyncio.run(main())
