# set current directory to the main project directory
import os
import json
import logging
import asyncio
from datetime import datetime
from typing import Iterator, AsyncIterator

curr_dir = os.getcwd()
print("Current directory: ", curr_dir)

if curr_dir.split(os.sep)[-1] == "Incident-Copilot":
    print("Already Root directory, current directory: ", curr_dir)
else:
    while curr_dir.split(os.sep)[-1] != "Incident-Copilot":
        os.chdir("..")
        curr_dir = os.getcwd()

    print("Changed to Root directory: ", curr_dir)

from fastmcp import Client
import gradio as gr
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

# importing llm related functions
from src.utils.llm_config import llm_instance, llm_openai_instance

# importing prompt related functions
from src.utils.prompts.system_prompts import incident_rag_system_prompt
from src.utils.prompts.prompt_template import get_incident_rag_template
from src.utils.rag.ingestion_funcs import ingestion_pipeline
from src.utils.rag.retrieval_funcs import retrieval_pipeline
# from src.utils.tools import get_current_time, identify_service, get_logs, get_metrics
from src.utils.tools import mcp

# importing dotenv to load environment variables
from dotenv import load_dotenv
load_dotenv()


# ----------------------- one-time setup (runs once at startup, not per message) -----------------------

# Get the incident prompt template
incident_rag_prompt_template = get_incident_rag_template(incident_rag_system_prompt)

# run the ingestion pipeline to ingest the documents into the vector database
vectordb_instance = ingestion_pipeline(data_folders=["corpus"], exclude_files=["sources.md"])

# fetch the tool list from the MCP server once at startup and convert to 
# function schemas so bind_tools can pass them straight through
async def _discover_tool_schemas():
    async with Client(mcp) as client:
        mcp_tools = await client.list_tools()
        return [
            {"type": "function", "function": {"name": t.name, "description": t.description or "", "parameters": t.inputSchema}}
            for t in mcp_tools
        ]

tool_schemas = asyncio.run(_discover_tool_schemas())

# Initialize the LLM instance, tools bound sequentially (not parallel -- a
# parallel call would let the model write get_logs's timeframe before it has
# llm = llm_instance(api_key=os.getenv("GROQ_API_KEY")).bind_tools(tools, parallel_tool_calls=False)
llm = llm_openai_instance(api_key=os.getenv("OPENAI_API_KEY")).bind_tools(tool_schemas, parallel_tool_calls=False)

# Only the last N user/assistant interactions are replayed to the LLM as
# conversation history -- older turns are dropped as the conversation grows,
# rather than letting the context window grow unbounded.
MAX_HISTORY_INTERACTIONS = 5

# Runtime log: one file per app run -- user query, retrieved context, every
# tool call + its response, and the final answer, one turn after another.
RUN_LOGS_DIR = os.path.join(curr_dir, "run_logs")
os.makedirs(RUN_LOGS_DIR, exist_ok=True)

logger = logging.getLogger("incident_copilot_chat")
logger.setLevel(logging.INFO)
logger.propagate = False  # don't also dump these through the root logger to stdout


def setup_logger() -> None:
    """
    Lazily creates the log file handler on first actual use, not at module
    import time. Gradio can execute this module more than once per app
    launch (a reload/respawn pass) -- creating the file eagerly at import
    time leaves an empty, unused file from whichever pass isn't the one that
    actually serves requests. Creating it lazily means only the process
    instance that actually logs something ever creates a file.
    """
    if logger.handlers:
        return
    timestamp = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
    log_path = os.path.join(RUN_LOGS_DIR, f"chat_{timestamp}.log")
    handler = logging.FileHandler(log_path, mode="w", encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s | %(message)s"))
    logger.addHandler(handler)
    print(f"Logging this run to: {log_path}")


# ----------------------- per-message handler -----------------------

def build_history_messages(history: list) -> list:
    """
    Converts Gradio's chat history (list of {"role", "content"} dicts) into
    LangChain messages, keeping only the last MAX_HISTORY_INTERACTIONS
    user/assistant pairs -- older turns are dropped rather than replayed to
    the LLM, so the context sent per request stays bounded as the
    conversation grows.

    Args:
        history (list): the full chat history supplied by gr.ChatInterface.

    Returns:
        list: LangChain HumanMessage/AIMessage objects for the retained turns.
    """
    trimmed = history[-(MAX_HISTORY_INTERACTIONS * 2):]

    history_messages = []
    for turn in trimmed:
        if turn["role"] == "user":
            history_messages.append(HumanMessage(content=turn["content"]))
        elif turn["role"] == "assistant":
            history_messages.append(AIMessage(content=turn["content"]))

    return history_messages


async def diagnose_incident(message: str, history: list) -> AsyncIterator[list]:
    """
    Handles one turn of the chat: retrieves grounding context for the
    incident description via the hybrid retrieval pipeline (BM25 + bi-encoder
    + RRF + cross-encoder), then runs the tool-calling agent loop
    (get_current_time, identify_service, get_logs, get_metrics -- called only
    when the model decides it needs them) to produce a cited diagnosis.

    Args:
        message (str): the latest incident query typed by the user.
        history (list): the chat history, as a list of {"role", "content"}
            dicts supplied by gr.ChatInterface. Only the last
            MAX_HISTORY_INTERACTIONS turns are replayed to the LLM.

    Yields:
        list: the growing list of assistant bubbles for this turn -- one
            collapsible status bubble per phase (retrieval, thinking, tool
            use), each carrying a `metadata` dict so Gradio renders it as a
            Claude-style "thought" accordion, plus a final plain bubble (no
            metadata) that streams in the actual diagnosis. Gradio replaces
            the whole turn with each yielded list, so every yield carries
            the full set of bubbles so far, not just what's new.
    """
    setup_logger()

    logger.info("=" * 60)
    logger.info(f"USER QUERY:\n{message}\n")

    ui_messages = []

    def snapshot() -> list:
        return list(ui_messages)

    # Single collapsible status bubble for the whole turn -- its title
    # tracks the current phase and its content accumulates a step-by-step
    # log, so the UI shows one compact "working..." accordion instead of a
    # growing stack of bubbles. It collapses (status -> "done") the moment
    # the model starts streaming its actual answer.
    status = {"role": "assistant", "content": "", "metadata": {"title": "🔎 Looking into corpus...", "status": "pending"}}
    ui_messages.append(status)

    def log_step(line: str) -> None:
        status["content"] += (("\n" if status["content"] else "") + f"- {line}")

    yield snapshot()

    retrieved_context = retrieval_pipeline(
        query=message,
        vector_store=vectordb_instance,
        collection_name="incident_corpus",
    )

    logger.info(f"RETRIEVED CONTEXT:\n{retrieved_context}\n")
    log_step("Looked into the corpus for relevant runbooks/postmortems")

    # build the initial message list (system + human w/ retrieved context),
    # then splice in the trimmed conversation history between the two so the
    # model sees prior turns before this turn's retrieved context/query
    system_message, human_message = incident_rag_prompt_template.format_messages(
        incident_query=message,
        retrieved_context=retrieved_context,
    )
    history_messages = build_history_messages(history)
    messages = [system_message, *history_messages, human_message]

    # agent loop: keep calling the LLM until it stops requesting tools.
    final_answer = None
    final_bubble = None  # the plain (no metadata) bubble the final answer streams into, created lazily
    max_iterations = 5

    # open one MCP client connection for the whole turn -- every tool call
    # across every iteration of this message's agent loop reuses it, rather
    # than reconnecting to the MCP server on each individual tool call
    async with Client(mcp) as client:
        for iteration in range(1, max_iterations + 1):
            # ---- phase: thinking (deciding whether to answer or call a tool) ----
            status["metadata"]["title"] = "🤔 Thinking..."
            yield snapshot()

            response = None  # accumulates into a full AIMessageChunk as chunks merge via `+`

            # astream (not stream) since we're inside an async generator now
            async for chunk in llm.astream(messages):
                response = chunk if response is None else response + chunk
                if chunk.content:
                    # the model is streaming its final answer, not a tool call --
                    # collapse the status bubble and start the real one
                    if final_bubble is None:
                        status["metadata"]["title"] = "✅ Done"
                        status["metadata"]["status"] = "done"
                        final_bubble = {"role": "assistant", "content": ""}
                        ui_messages.append(final_bubble)
                    final_bubble["content"] += chunk.content
                    yield snapshot()

            messages.append(response)  # merged AIMessageChunk, possibly carrying tool_calls

            if not response.tool_calls:
                status["metadata"]["title"] = "✅ Done"
                status["metadata"]["status"] = "done"
                final_answer = response.content
                break

            # ---- phase: tool use ----
            tool_names = ", ".join(tool_call["name"] for tool_call in response.tool_calls)
            status["metadata"]["title"] = f"🛠️ Using {tool_names}..."
            yield snapshot()

            print(f"\nIteration #{iteration}")
            for tool_call in response.tool_calls:
                # dispatch the call through the MCP client instead of a local TOOL_MAP
                result = await client.call_tool(tool_call["name"], tool_call["args"])
                # .data is the tool's actual return value; fall back to structured_content if unset
                result_payload = result.data if result.data is not None else result.structured_content

                logger.info(f"TOOL CALL: {tool_call['name']}({tool_call['args']})")
                logger.info(f"TOOL RESPONSE:\n{json.dumps(result_payload, indent=2)}\n")

                messages.append(ToolMessage(
                    content=json.dumps(result_payload),
                    tool_call_id=tool_call["id"],
                ))
                print(f"  [tool] {tool_call['name']}({tool_call['args']}) -> {result_payload}")

            log_step(f"Used {tool_names}")
            yield snapshot()
        else:
            final_answer = "Reached max iterations without a final answer."
            status["metadata"]["title"] = "✅ Done"
            status["metadata"]["status"] = "done"
            ui_messages.append({"role": "assistant", "content": final_answer})

    logger.info(f"FINAL ANSWER:\n{final_answer}\n")
    logger.info("=" * 60)

    # Ensures the UI shows final_answer even on paths that never streamed
    # content into final_bubble (e.g. the max-iterations fallback). For the
    # normal path this just re-yields the same bubbles already shown.
    yield snapshot()


# ----------------------- Gradio chat UI -----------------------

demo = gr.ChatInterface(
    fn=diagnose_incident,
    title="Incident Pilot",
    description=(
        "Describe a production incident and get a cited, RAG-grounded diagnosis. "
        "This assistant never executes deploys/rollbacks — it will only draft recommended "
        "steps for a human on-call engineer to review and run themselves."
    ),
    examples=[
        # one per targeted service (implied by symptom, not named directly), one rollback (no-action-rule) query, one generic/service-agnostic query
        "Refund requests are failing left and right and logs are full of ConnectionPoolTimeoutException, what should I check?",
        "p95 latency on completing purchases just spiked right after a deploy, can you help me figure out what's going on?",
        "A bunch of users can't log in and something's spiking hard on our side, any idea what's happening?",
        "Error rate on completing purchases jumped right after we shipped v2.1.0 this afternoon, just roll it back for me.",
        "What's our policy for handling a production incident before a human gets paged?",
    ],
)


if __name__ == "__main__":
    demo.launch(share=True)
