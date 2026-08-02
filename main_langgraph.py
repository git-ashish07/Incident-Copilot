"""
This script shows how to run the tools through MCP framework.
"""

# set current directory to the main project directory
import os
import sys
import json
import asyncio
import logging
from datetime import datetime

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
from langchain_core.messages import ToolMessage, AIMessage
from fastmcp import Client
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import InMemorySaver

# importing llm related functions
from src.utils.llm_config import llm_instance

# importing prompt related functions
from src.utils.prompts.system_prompts import incident_rag_system_prompt
from src.utils.prompts.prompt_template import get_incident_rag_template
from src.data.sample_incident_queries import queries
from src.utils.rag.ingestion_funcs import ingestion_pipeline
from src.utils.rag.retrieval_funcs import retrieval_pipeline
from src.utils.tools import mcp
from src.utils.models import AgentState
from src.utils.nodes import make_retrieve_node, make_llm_call_node, make_tools_node, give_up, make_router
from src.utils.memory import summarize_chat_history

# importing dotenv to load environment variables
from dotenv import load_dotenv
load_dotenv()

# one log file per run, full trace goes here instead of the terminal
RUN_LOGS_DIR = os.path.join(curr_dir, "run_logs")
os.makedirs(RUN_LOGS_DIR, exist_ok=True)

logger = logging.getLogger("incident_copilot_langgraph")
logger.setLevel(logging.INFO)
logger.propagate = False  # don't also dump this through the root logger to stdout

log_path = os.path.join(RUN_LOGS_DIR, f"langgraph_{datetime.now().strftime('%Y-%m-%dT%H-%M-%S')}.log")
handler = logging.FileHandler(log_path, mode="w", encoding="utf-8")
handler.setFormatter(logging.Formatter("%(asctime)s | %(message)s"))
logger.addHandler(handler)
print(f"Logging full trace to: {log_path}")

async def main():
    # Get the incident prompt template
    incident_rag_prompt_template = get_incident_rag_template(incident_rag_system_prompt)

    # run the ingestion pipeline to ingest the documents into the vector database
    vectordb_instance = ingestion_pipeline(data_folders=["corpus"], exclude_files=["sources.md"])

    # build the retrieve node for the incident-diagnosis agent
    retrieve_node = make_retrieve_node(vectordb_instance, incident_rag_prompt_template)

    # initialize the MCP client
    async with Client(mcp) as client:
        # build the tools node now
        tools_node = make_tools_node(client)

        # get the list of tools registered with MCP
        mcp_tools = await client.list_tools()

        # create a list of tool schemas for the LLM to use
        tool_schemas = [
            {"type": "function", "function": {"name": t.name, "description": t.description or "", "parameters": t.inputSchema}}
            for t in mcp_tools
        ]

        # Initialize the LLM instances for tool & non-tool bound calls
        llm = llm_instance(api_key=os.getenv("GROQ_API_KEY")).bind_tools(tool_schemas, parallel_tool_calls=False)
        plain_llm = llm_instance(api_key=os.getenv("GROQ_API_KEY"))


        # build the LLM call node for the incident-diagnosis agent
        llm_call_node = make_llm_call_node(llm)

        # build the router node for the incident-diagnosis agent
        max_iterations = 5
        router = make_router(max_iterations)

        # assemble the graph: register each node under a name, then wire the edges b/w them
        graph = StateGraph(AgentState)
        graph.add_node("retrieve", retrieve_node)
        graph.add_node("llm_call", llm_call_node)
        graph.add_node("tools", tools_node)
        graph.add_node("give_up", give_up)

        # add the edges
        graph.add_edge(start_key=START, end_key="retrieve")
        graph.add_edge(start_key="retrieve", end_key="llm_call")
        graph.add_conditional_edges(source="llm_call", path=router, path_map={"end": END, "tools": "tools", "give_up": "give_up"})
        graph.add_edge("tools", "llm_call")
        graph.add_edge("give_up", END)

        # a checkpointer lets the SAME graph.ainvoke/astream call be run repeatedly with a shared thread_id and have state (chat_history, query_count, etc.) persist and
        # carry forward between calls, instead of every call starting from a completely empty state
        checkpointer = InMemorySaver()
        app_graph = graph.compile(checkpointer=checkpointer)

        # Get the sample incident queries for dry run
        incident_queries = queries[:5]

        # all 5 queries share this thread_id, so the checkpointer treats them as one continuous conversation 
        thread_id = "dry-run-session"

        for turn_num, incident_query in enumerate(incident_queries, start=1):
            # kept on the terminal -- lightweight progress marker, full detail goes to the log file
            print(f"[Turn {turn_num}] {incident_query[:80]}...")

            # TURN banner ('#') -- the widest, outermost separator, one per user query
            logger.info(f"\n{'#' * 80}")
            logger.info(f"# TURN {turn_num} | Query: {incident_query}")
            logger.info(f"{'#' * 80}")

            final_answer = None

            # run the whole graph for this query, logging each node as it finishes so we can see the flow live
            async for update in app_graph.astream(
                input={"incident_query": incident_query, "messages": [], "iterations": 0},
                config={"recursion_limit": 50, "configurable": {"thread_id": thread_id}},
                stream_mode="updates",
            ):
                for node_name, node_output in update.items():
                    # NODE banner ('-') -- one per node execution within this turn, nested under the turn
                    logger.info(f"\n  {'-' * 60}")
                    logger.info(f"  [NODE] {node_name}")
                    logger.info(f"  {'-' * 60}")

                    if node_output.get("messages"):
                        last_msg = node_output["messages"][-1]
                        logger.info(f"    message: {type(last_msg).__name__} -> {str(last_msg.content)[:200]}")
                        if getattr(last_msg, "tool_calls", None):
                            logger.info(f"    requested tools: {[tc['name'] for tc in last_msg.tool_calls]}")
                        final_answer = last_msg.content

                    if "iterations" in node_output:
                        logger.info(f"    iterations now: {node_output['iterations']}")

            # FINAL ANSWER banner ('=') -- clearly marks where the turn's actual answer sits
            logger.info(f"\n  {'=' * 60}")
            logger.info(f"  FINAL ANSWER (Turn {turn_num})")
            logger.info(f"  {'=' * 60}")
            logger.info(f"  {final_answer}")

            # kept on the terminal too, trimmed -- so you see the outcome without opening the log file
            print(f"  -> {str(final_answer)[:150]}")

            # fold check happens AFTER the answer is already printed, so it never delays the response
            current_state = await app_graph.aget_state({"configurable": {"thread_id": thread_id}})
            chat_history = current_state.values.get("chat_history") or []
            query_count = current_state.values.get("query_count", 0)

            # STATE snapshot -- what chat_history/query_count actually hold after this turn
            logger.info(f"\n  [STATE after Turn {turn_num}] query_count={query_count} | chat_history has {len(chat_history)} entries")
            for i, msg in enumerate(chat_history):
                logger.info(f"    {i}. {type(msg).__name__}: {str(msg.content)[:150]}")

            if query_count >= 3:
                # FOLD banner ('*') -- rare event, made visually distinct from regular per-turn logging
                logger.info(f"\n  {'*' * 60}")
                logger.info(f"  [MEMORY FOLD] query_count reached {query_count} -- summarizing chat_history")

                summary = await summarize_chat_history(chat_history, plain_llm)

                await app_graph.aupdate_state(
                    {"configurable": {"thread_id": thread_id}},
                    values={"chat_history": [summary], "query_count": 0},
                )
                logger.info(f"  chat_history replaced with 1 summary message | query_count reset to 0")
                logger.info(f"  summary: {summary.content[:300]}")
                logger.info(f"  {'*' * 60}")
                print(f"  [memory folded, see log for summary]")


        # for incident_query in incident_queries:
        #     print(f"\n{'=' * 50}")
        #     print("\nIncident Query: ", incident_query)

        #     # # run the whole graph for this query: retrieve -> llm_call -> tools (if needed) -> llm_call -> ... until we reach a final answer or give up
        #     # final_state = await app_graph.ainvoke(
        #     #     input = {"incident_query": incident_query, "messages": [], "iterations": 0},
        #     #     config = {"recursion_limit": 7}
        #     # )

        #     # final_answer = final_state["messages"][-1].content

        #     # run the whole graph for this query, logging each node as it finishes so we can see the flow live
        #     final_answer = None

        #     async for update in app_graph.astream(
        #         input={"incident_query": incident_query, "messages": [], "iterations": 0},
        #         config={"recursion_limit": 50, "configurable": {"thread_id": thread_id}},
        #         stream_mode="updates",
        #     ):
        #         for node_name, node_output in update.items():
        #             print(f"\n[NODE] {node_name}")

        #             if node_output.get("messages"):
        #                 last_msg = node_output["messages"][-1]
        #                 print(f"  message: {type(last_msg).__name__} -> {str(last_msg.content)[:200]}")
        #                 if getattr(last_msg, "tool_calls", None):
        #                     print(f"  requested tools: {[tc['name'] for tc in last_msg.tool_calls]}")
        #                 final_answer = last_msg.content

        #             if "iterations" in node_output:
        #                 print(f"  iterations now: {node_output['iterations']}")

        #     print("\nLLM Response:\n", final_answer)

        #     # fold check happens AFTER the answer is already printed, so it never delays the response
            
        #     # get the current state from the checkpointer to see if we need to fold the chat_history into a summary
        #     current_state = await app_graph.aget_state({"configurable": {"thread_id": thread_id}})

        #     # if the query_count has reached 3, we fold the chat_history into a summary and reset the query_count to 0
        #     if current_state.values.get("query_count", 0) >= 3:
        #         summary = await summarize_chat_history(current_state.values["chat_history"], plain_llm)

        #         # update the state with the summary and reset the query_count to 0
        #         await app_graph.aupdate_state(
        #             {"configurable": {"thread_id": thread_id}},
        #             values={"chat_history": [summary], "query_count": 0},
        #         )
        #         print("\n[MEMORY] chat_history folded into a summary, query_count reset to 0")


if __name__ == "__main__":
    asyncio.run(main())
