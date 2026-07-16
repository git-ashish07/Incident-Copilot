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


import gradio as gr

# importing llm related functions
from src.llm_funcs.llm_config import llm_instance

# importing prompt related functions
from src.prompts.system_prompts import incident_rag_system_prompt
from src.prompts.prompt_template import get_incident_rag_template
from src.utils.rag.ingestion_funcs import ingestion_pipeline
from src.utils.rag.retrieval_funcs import retrieval_pipeline, format_retrieved_context

# importing dotenv to load environment variables
from dotenv import load_dotenv
load_dotenv()


# ----------------------- one-time setup (runs once at startup, not per message) -----------------------

# Initialize the LLM instance
llm = llm_instance(api_key=os.getenv("GROQ_API_KEY"))

# Build the RAG-aware prompt template and chain once, reused for every turn
incident_rag_prompt_template = get_incident_rag_template(incident_rag_system_prompt)
incident_chain = incident_rag_prompt_template | llm

# Ingest the corpus into the vector database once at startup. This is safe
# to call every time the app starts — ingestion skips chunks that already
# exist (see ingest_documents), so it won't re-embed the whole corpus on
# every restart.
vectordb_instance = ingestion_pipeline(data_folders=["corpus"], exclude_files=["sources.md"])


# ----------------------- per-message handler -----------------------

def diagnose_incident(message: str, history: list) -> str:
    """
    Handles one turn of the chat: retrieves grounding context for the
    incident description via the hybrid retrieval pipeline (BM25 + bi-encoder
    + RRF + cross-encoder), then generates a cited diagnosis summary.

    Args:
        message (str): the latest incident query typed by the user.
        history (list): prior turns in the conversation, supplied
            automatically by gr.ChatInterface. Not used yet — each query is
            diagnosed independently against the corpus; there's no cross-turn
            memory in Week 1.

    Returns:
        str: the assistant's diagnosis response, grounded in retrieved context.
    """
    retrieved_context = retrieval_pipeline(
        query=message,
        vector_store=vectordb_instance,
        collection_name="incident_corpus",
    )

    response = incident_chain.invoke({
        "incident_query": message,
        "retrieved_context": retrieved_context,
    }).content

    return response


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
        # the 6 sample queries from docs/requirements.md §3
        "API latency spiked 5x in the last 15 minutes, what's going on?",
        "Has this exact error pattern happened before?",
        "What does the runbook say to do for a connection-pool exhaustion?",
        "Roll back the last deploy.",
        "Open a GitHub issue to track this incident.",
        "Just push a hotfix directly to production now.",
    ],
)


if __name__ == "__main__":
    demo.launch(share=True)
