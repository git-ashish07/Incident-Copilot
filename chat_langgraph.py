# set current directory to the main project directory
import os
import json
import logging
import asyncio
from datetime import datetime
from typing import AsyncIterator

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
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import InMemorySaver

# importing llm related functions
from src.utils.llm_config import llm_instance, llm_openai_instance

# importing prompt related functions
from src.utils.prompts.system_prompts import incident_rag_system_prompt
from src.utils.prompts.prompt_template import get_incident_rag_template
from src.utils.rag.ingestion_funcs import ingestion_pipeline
from src.utils.tools import mcp
from src.utils.models import AgentState
from src.utils.nodes import make_retrieve_node, make_llm_call_node, make_tools_node, give_up, make_router
from src.utils.memory import summarize_chat_history

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
llm = llm_openai_instance(api_key=os.getenv("OPENAI_API_KEY")).bind_tools(tool_schemas, parallel_tool_calls=False)

# plain, non-tool-bound instance for chat_history summarization
plain_llm = llm_openai_instance(api_key=os.getenv("OPENAI_API_KEY"))

# these two don't depend on the per-message MCP client, so they're built once, not per message
retrieve_node = make_retrieve_node(vectordb_instance, incident_rag_prompt_template)
llm_call_node = make_llm_call_node(llm)

max_iterations = 5
router = make_router(max_iterations)

# one checkpointer shared across every message and every user -- this is what makes chat_history/
# query_count persist turn to turn, keyed per browser tab via thread_id (see diagnose_incident)
checkpointer = InMemorySaver()

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

def _build_memory_markdown(chat_history: list) -> str:
    if not chat_history:
        return "_Nothing in memory yet._"
    lines = [f"**{type(msg).__name__.replace('Message', '')}:** {msg.content}" for msg in chat_history]
    return "\n\n".join(lines)

def _build_corpus_markdown(retrieved_context: str) -> str:
    return retrieved_context if retrieved_context else "_Nothing retrieved yet._"

def _get_tool_payload(call: dict) -> dict | None:
    try:
        return json.loads(call["result"])
    except (TypeError, ValueError):
        return None

def _build_metrics_rows(tool_calls: list) -> list[list]:
    rows = []
    for call in tool_calls:
        if call["name"] != "get_metrics":
            continue
        payload = _get_tool_payload(call)
        for entry in (payload or {}).get("metrics", []):
            m = json.loads(entry) if isinstance(entry, str) else entry
            rows.append([m.get("timestamp"), m.get("service"), m.get("metric"), m.get("value")])
    return rows

def _build_logs_markdown(tool_calls: list) -> str:
    lines = []
    for call in tool_calls:
        if call["name"] != "get_logs":
            continue
        payload = _get_tool_payload(call)
        for entry in (payload or {}).get("logs", []):
            log = json.loads(entry) if isinstance(entry, str) else entry
            lines.append(f"`{log.get('timestamp')}` **[{log.get('level')}]** {log.get('message')}")
    return "\n\n".join(lines) if lines else "_No logs retrieved yet._"


async def diagnose_incident(message: str, history: list, request: gr.Request) -> AsyncIterator[list]:
    """
    Handles one turn of the chat via the LangGraph agent (retrieve -> llm_call
    -> tools (if needed) -> llm_call -> ... -> end/give_up), with chat_history
    persisted per browser session and folded into a summary every 3 turns.

    Args:
        message (str): the latest incident query typed by the user.
        history (list): Gradio's chat history -- no longer read directly here,
            since conversation memory now lives in the graph's own state.
        request (gr.Request): injected by Gradio -- request.session_hash is
            used as this session's thread_id, so state never leaks between users.

    Yields:
        tuple: (chat bubbles, memory panel markdown, tools panel markdown).
            The two panel values are gr.skip() until the final yield.
    """

    setup_logger()

    thread_id = request.session_hash

    logger.info("=" * 60)
    logger.info(f"USER QUERY (thread {thread_id}):\n{message}\n")

    ui_messages = list(history) if history else []
    ui_messages.append({"role": "user", "content": message})

    def snapshot() -> list:
        return list(ui_messages)

    status = {"role": "assistant", "content": "", "metadata": {"title": "🔎 Looking into corpus...", "status": "pending"}}
    ui_messages.append(status)

    def log_step(line: str) -> None:
        status["content"] += (("\n" if status["content"] else "") + f"- {line}")

    yield snapshot(), gr.skip(), gr.skip(), gr.skip(), gr.skip(), gr.skip()

    final_answer = None
    final_bubble = None
    tool_names = ""  # remembered between the llm_call update and the following tools update, for log_step

    # accumulated over the whole turn, for the two side panels
    retrieved_context_this_turn = ""
    pending_tool_calls = []       # this round's {name, args} -- paired with results as soon as the tools update arrives
    tool_calls_this_turn = []     # {name, args, result} for every tool call made this turn, across every round

    # open one MCP client connection for this message -- tools_node/the graph are rebuilt per
    # message because they close over this client, but the checkpointer (built once, above) is
    # what actually carries chat_history/query_count forward between messages
    async with Client(mcp) as client:
        tools_node = make_tools_node(client)

        graph = StateGraph(AgentState)
        graph.add_node("retrieve", retrieve_node)
        graph.add_node("llm_call", llm_call_node)
        graph.add_node("tools", tools_node)
        graph.add_node("give_up", give_up)

        graph.add_edge(start_key=START, end_key="retrieve")
        graph.add_edge(start_key="retrieve", end_key="llm_call")
        graph.add_conditional_edges(source="llm_call", path=router, path_map={"end": END, "tools": "tools", "give_up": "give_up"})
        graph.add_edge("tools", "llm_call")
        graph.add_edge("give_up", END)

        app_graph = graph.compile(checkpointer=checkpointer)

        # two stream modes at once: "messages" gives token-by-token chunks (for live streaming
        # into the UI), "updates" gives one complete message per finished node (for phase changes)
        async for mode, payload in app_graph.astream(
            input={"incident_query": message, "messages": [], "iterations": 0},
            config={"recursion_limit": 50, "configurable": {"thread_id": thread_id}},
            stream_mode=["updates", "messages"],
        ):
            if mode == "messages":
                chunk, metadata = payload
                # only llm_call's tokens are streamed into the answer bubble -- retrieve/tools don't call the LLM directly
                if metadata.get("langgraph_node") == "llm_call" and chunk.content:
                    if final_bubble is None:
                        status["metadata"]["title"] = "✅ Done"
                        status["metadata"]["status"] = "done"
                        final_bubble = {"role": "assistant", "content": ""}
                        ui_messages.append(final_bubble)
                    final_bubble["content"] += chunk.content
                    yield snapshot(), gr.skip(), gr.skip(), gr.skip(), gr.skip(), gr.skip()
                continue

            # mode == "updates"
            for node_name, node_output in payload.items():
                logger.info(f"NODE: {node_name} -> {node_output}")

                if node_name == "retrieve":
                    retrieved_context_this_turn = node_output.get("retrieved_context", "")
                    log_step("Looked into the corpus for relevant runbooks/postmortems")
                    status["metadata"]["title"] = "🤔 Thinking..."
                    yield snapshot(), gr.skip(), gr.skip(), gr.skip(), gr.skip(), gr.skip()

                elif node_name == "llm_call" and node_output.get("messages"):
                    last_msg = node_output["messages"][-1]
                    if last_msg.tool_calls:
                        # this round wasn't the final answer -- discard anything streamed into
                        # final_bubble during it
                        if final_bubble is not None:
                            ui_messages.remove(final_bubble)
                            final_bubble = None
                        pending_tool_calls = [{"name": tc["name"], "args": tc["args"]} for tc in last_msg.tool_calls]
                        tool_names = ", ".join(tc["name"] for tc in last_msg.tool_calls)
                        status["metadata"]["title"] = f"🛠️ Using {tool_names}..."
                        yield snapshot(), gr.skip(), gr.skip(), gr.skip(), gr.skip(), gr.skip()
                    else:
                        # authoritative final text -- overwrite the bubble wholesale, discarding
                        # anything streamed into it, regardless of why it might be wrong
                        final_answer = last_msg.content
                        if final_bubble is None:
                            final_bubble = {"role": "assistant", "content": ""}
                            ui_messages.append(final_bubble)
                        final_bubble["content"] = final_answer
                        status["metadata"]["title"] = "✅ Done"
                        status["metadata"]["status"] = "done"
                        yield snapshot(), gr.skip(), gr.skip(), gr.skip(), gr.skip(), gr.skip()



                elif node_name == "tools":
                    tool_msgs = node_output.get("messages", [])
                    for tc_msg in tool_msgs:
                        logger.info(f"TOOL RESPONSE:\n{tc_msg.content}\n")

                    for call, result_msg in zip(pending_tool_calls, tool_msgs):
                        tool_calls_this_turn.append({**call, "result": result_msg.content})
                    pending_tool_calls = []

                    if tool_names:
                        log_step(f"Used {tool_names}")
                        yield snapshot(), gr.skip(), gr.skip(), gr.skip(), gr.skip(), gr.skip()

                elif node_name == "give_up":
                    # give_up never calls the LLM, so no "messages"-mode tokens arrive for it -- add it directly
                    final_answer = node_output["messages"][-1].content
                    status["metadata"]["title"] = "✅ Done"
                    status["metadata"]["status"] = "done"
                    ui_messages.append({"role": "assistant", "content": final_answer})
                    yield snapshot(), gr.skip(), gr.skip(), gr.skip(), gr.skip(), gr.skip()

        # fold check happens after the answer is already streamed back, so it never delays the response
        current_state = await app_graph.aget_state({"configurable": {"thread_id": thread_id}})
        if current_state.values.get("query_count", 0) >= 3:
            summary = await summarize_chat_history(current_state.values["chat_history"], plain_llm)
            await app_graph.aupdate_state(
                {"configurable": {"thread_id": thread_id}},
                values={"chat_history": [summary], "query_count": 0},
            )
            logger.info("[MEMORY] chat_history folded into a summary, query_count reset to 0")

    logger.info(f"FINAL ANSWER:\n{final_answer}\n")
    logger.info("=" * 60)

    corpus_markdown = _build_corpus_markdown(retrieved_context_this_turn)
    metrics_rows = _build_metrics_rows(tool_calls_this_turn)
    has_metrics = bool(metrics_rows)
    logs_markdown = _build_logs_markdown(tool_calls_this_turn)
    memory_markdown = _build_memory_markdown(current_state.values.get("chat_history") or [])

    yield (
        snapshot(),
        corpus_markdown,
        gr.update(visible=not has_metrics),
        gr.update(value=metrics_rows, visible=has_metrics),
        logs_markdown,
        memory_markdown,
    )


# ----------------------- Gradio chat UI -----------------------

# demo = gr.ChatInterface(
#     fn=diagnose_incident,
#     title="Incident Pilot",
#     description=(
#         "Describe a production incident and get a cited, RAG-grounded diagnosis. "
#         "This assistant never executes deploys/rollbacks — it will only draft recommended "
#         "steps for a human on-call engineer to review and run themselves."
#     ),
#     examples=[
#         # one per targeted service (implied by symptom, not named directly), one rollback (no-action-rule) query, one generic/service-agnostic query
#         "Refund requests are failing left and right and logs are full of ConnectionPoolTimeoutException, what should I check?",
#         "p95 latency on completing purchases just spiked right after a deploy, can you help me figure out what's going on?",
#         "A bunch of users can't log in and something's spiking hard on our side, any idea what's happening?",
#         "Error rate on completing purchases jumped right after we shipped v2.1.0 this afternoon, just roll it back for me.",
#         "What's our policy for handling a production incident before a human gets paged?",
#     ],
# )

custom_css = """
#hero {
    background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 50%, #ec4899 100%);
    border-radius: 16px;
    padding: 32px 24px;
    margin-bottom: 12px;
}
#hero h1, #hero p { color: white !important; }
#hero p { opacity: 0.92; }
"""

with gr.Blocks(
    title="Incident Pilot",
    theme=gr.themes.Default(
        primary_hue="indigo",
        secondary_hue="pink",
        neutral_hue="slate",
        font=[gr.themes.GoogleFont("Inter"), "ui-sans-serif", "system-ui", "sans-serif"],
    ),
    css=custom_css,
) as demo:
    gr.Markdown(
        "<div id='hero' style='text-align:center'>"
        "<h1 style='margin:0'>🚨 Incident Pilot</h1>"
        "<p style='font-size:1.05em;margin-top:8px'>"
        "Describe a production incident and get a cited, RAG-grounded diagnosis. <br>"
        "This assistant never executes deploys/rollbacks — it only drafts recommended "
        "steps for a human on-call engineer to review and run."
        "</p></div>"
    )


    with gr.Tabs():
        with gr.Tab("💬 Chat"):
            chatbot = gr.Chatbot(
                height=500,
                examples=[
                    {"text": "Refund requests are failing left and right and logs are full of ConnectionPoolTimeoutException, what should I check?"},
                    {"text": "p95 latency on completing purchases just spiked right after a deploy, can you help me figure out what's going on?"},
                    {"text": "A bunch of users can't log in and something's spiking hard on our side, any idea what's happening?"},
                    {"text": "Error rate on completing purchases jumped right after we shipped v2.1.0 this afternoon, just roll it back for me."},
                ],
            )
            with gr.Row():
                msg_box = gr.Textbox(placeholder="Describe the incident...", show_label=False, scale=5)

        with gr.Tab("📚 Corpus References"):
            corpus_panel = gr.Markdown("_Nothing retrieved yet._")

        with gr.Tab("📊 Logs & Metrics"):
            gr.Markdown("### Metrics")
            metrics_empty_note = gr.Markdown("_No metrics retrieved yet._")
            metrics_table = gr.Dataframe(headers=["timestamp", "service", "metric", "value"], value=[], visible=False)
            gr.Markdown("### Logs")
            logs_panel = gr.Markdown("_No logs retrieved yet._")

        with gr.Tab("🧠 Memory"):
            memory_panel = gr.Markdown("_Nothing in memory yet._")

    outputs = [chatbot, corpus_panel, metrics_empty_note, metrics_table, logs_panel, memory_panel]

    msg_box.submit(diagnose_incident, inputs=[msg_box, chatbot], outputs=outputs).then(lambda: "", None, msg_box)

    example_state = gr.State("")

    def _example_text(evt: gr.SelectData) -> str:
        return evt.value["text"]

    chatbot.example_select(_example_text, None, example_state).then(
        diagnose_incident, inputs=[example_state, chatbot], outputs=outputs
    )



if __name__ == "__main__":
    demo.launch(share=True)

