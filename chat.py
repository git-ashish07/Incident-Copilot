# set current directory to the main project directory
import os
import json
import logging
from datetime import datetime
from typing import Iterator

curr_dir = os.getcwd()
print("Current directory: ", curr_dir)

if curr_dir.split(os.sep)[-1] == "Incident-Copilot":
    print("Already Root directory, current directory: ", curr_dir)
else:
    while curr_dir.split(os.sep)[-1] != "Incident-Copilot":
        os.chdir("..")
        curr_dir = os.getcwd()

    print("Changed to Root directory: ", curr_dir)


import gradio as gr
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

# importing llm related functions
from src.utils.llm_config import llm_instance, llm_openai_instance

# importing prompt related functions
from src.utils.prompts.system_prompts import incident_rag_system_prompt
from src.utils.prompts.prompt_template import get_incident_rag_template
from src.utils.rag.ingestion_funcs import ingestion_pipeline
from src.utils.rag.retrieval_funcs import retrieval_pipeline
from src.utils.tools import get_current_time, identify_service, get_logs, get_metrics

# importing dotenv to load environment variables
from dotenv import load_dotenv
load_dotenv()


# ----------------------- one-time setup (runs once at startup, not per message) -----------------------

# Get the incident prompt template
incident_rag_prompt_template = get_incident_rag_template(incident_rag_system_prompt)

# run the ingestion pipeline to ingest the documents into the vector database
vectordb_instance = ingestion_pipeline(data_folders=["corpus"], exclude_files=["sources.md"])

# getting the tools to be used by the LLM for retrieval and analysis
tools = [get_current_time, identify_service, get_logs, get_metrics]
TOOL_MAP = {tool.name: tool for tool in tools}  # tool map for dispatching tool calls

# Initialize the LLM instance, tools bound sequentially (not parallel -- a
# parallel call would let the model write get_logs's timeframe before it has
# llm = llm_instance(api_key=os.getenv("GROQ_API_KEY")).bind_tools(tools, parallel_tool_calls=False)
llm = llm_openai_instance(api_key=os.getenv("OPENAI_API_KEY")).bind_tools(tools, parallel_tool_calls=False)

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


def diagnose_incident(message: str, history: list) -> Iterator[str]:
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
        str: the assistant's diagnosis response so far, growing as the final
            answer streams in (grounded in retrieved context and any tool
            results gathered this turn). Gradio replaces the displayed
            message with each yielded value, so each yield carries the full
            text accumulated so far, not just the new delta.
    """
    setup_logger()

    logger.info("=" * 60)
    logger.info(f"USER QUERY:\n{message}\n")

    # run the retrieval pipeline to get relevant context for the incident query
    retrieved_context = retrieval_pipeline(
        query=message,
        vector_store=vectordb_instance,
        collection_name="incident_corpus",
    )

    logger.info(f"RETRIEVED CONTEXT:\n{retrieved_context}\n")

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
    max_iterations = 5

    for iteration in range(1, max_iterations + 1):
        response = None  # accumulates into a full AIMessageChunk as chunks merge via `+`
        streamed_text = ""

        for chunk in llm.stream(messages):
            response = chunk if response is None else response + chunk
            if chunk.content:
                streamed_text += chunk.content
                yield streamed_text

        messages.append(response)  # merged AIMessageChunk, possibly carrying tool_calls

        if not response.tool_calls:
            final_answer = response.content
            break

        print(f"\nIteration #{iteration}")
        for tool_call in response.tool_calls:
            tool_fn = TOOL_MAP[tool_call["name"]]
            result = tool_fn.invoke(tool_call["args"])

            logger.info(f"TOOL CALL: {tool_call['name']}({tool_call['args']})")
            logger.info(f"TOOL RESPONSE:\n{json.dumps(result, indent=2)}\n")

            messages.append(ToolMessage(
                content=json.dumps(result),
                tool_call_id=tool_call["id"],
            ))
            print(f"  [tool] {tool_call['name']}({tool_call['args']}) -> {result}")
    else:
        final_answer = "Reached max iterations without a final answer."

    logger.info(f"FINAL ANSWER:\n{final_answer}\n")
    logger.info("=" * 60)

    # Ensures the UI shows final_answer even on paths that never streamed
    # content (e.g. the max-iterations fallback) -- a generator's `return`
    # value isn't delivered to the caller, only yielded values are, so this
    # can't be a plain `return`. For the normal path, final_answer already
    # equals the last streamed_text, so this just re-yields the same text.
    yield final_answer


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
