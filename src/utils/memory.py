import uuid
from langchain_core.documents import Document
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from src.utils.prompts.system_prompts import chat_history_summary_prompt, incident_extraction_prompt, notes_extraction_prompt
from src.utils.models import IncidentExtraction, NotesExtraction
from src.utils.rag.ingestion_funcs import get_vector_store
from src.utils.pgdb import get_unprocessed_sessions, get_session_messages, mark_session_processed

async def summarize_chat_history(chat_history: list, llm) -> AIMessage:
    """
    Condense the accumulated chat_history into one summary message.
    
    Args:
        chat_history (list): A list of message objects representing the conversation history.
        llm: The LLM instance to use for summarization.

    Returns:
        AIMessage: A single AI message containing the summary of the chat history.
    """

    # Format the chat history into a string representation
    history_text = "\n".join(f"{type(msg).__name__}: {msg.content}" for msg in chat_history)

    response = await llm.ainvoke([
        SystemMessage(content = chat_history_summary_prompt),
        HumanMessage(content = history_text)
    ])
    return AIMessage(content=f"[Summary of earlier conversation]\n{response.content}")

async def extract_incident_memory(session_id: str, messages: list, llm) -> None:
    if not messages:
        return

    transcript_text = "\n".join(f"{m['role']}: {m['content']}" for m in messages)

    structured_llm = llm.with_structured_output(IncidentExtraction)
    result = await structured_llm.ainvoke([
        SystemMessage(content=incident_extraction_prompt),
        HumanMessage(content=transcript_text),
    ])

    if not result.incidents:
        print(f"  [incident memory] session {session_id}: no incidents found")
        return

    vector_store = get_vector_store(collection_name="incident_memory")
    documents = [
        Document(
            page_content=f"{incident.service} | {incident.symptoms} | {incident.diagnosis}",
            metadata={
                "session_id": session_id,
                "service": incident.service,
                "symptoms": incident.symptoms,
                "steps_taken": incident.steps_taken,
                "diagnosis": incident.diagnosis,
                "resolution_status": incident.resolution_status,
            },
            id=str(uuid.uuid4()),
        )
        for incident in result.incidents
    ]

    vector_store.add_documents(documents, ids=[d.id for d in documents])
    print(f"  [incident memory] session {session_id}: stored {len(documents)} incident(s)")
    for doc in documents:
        print(f"    + [{doc.id}] service={doc.metadata['service']} | symptoms={doc.metadata['symptoms']} | diagnosis={doc.metadata['diagnosis']}")


async def extract_notes_memory(session_id: str, messages: list, llm) -> None:
    if not messages:
        return

    vector_store = get_vector_store(collection_name="agent_notes")
    existing = vector_store.get(include=["documents"])
    existing_notes_text = "\n".join(
        f"[{doc_id}] {doc}" for doc_id, doc in zip(existing["ids"], existing["documents"])
    ) or "(none yet)"

    transcript_text = "\n".join(f"{m['role']}: {m['content']}" for m in messages)
    human_content = f"[EXISTING NOTES]\n{existing_notes_text}\n\n[NEW SESSION TRANSCRIPT]\n{transcript_text}"

    structured_llm = llm.with_structured_output(NotesExtraction)
    result = await structured_llm.ainvoke([
        SystemMessage(content=notes_extraction_prompt),
        HumanMessage(content=human_content),
    ])

    if not result.notes:
        print(f"  [notes memory] session {session_id}: nothing new")
        return

    to_add = []
    updated_count = 0
    for note in result.notes:
        if note.action == "update" and note.note_id:
            vector_store.update_documents(
                ids=[note.note_id],
                documents=[Document(
                    page_content=note.content,
                    metadata={"category": note.category, "service": note.service, "session_id": session_id},
                    id=note.note_id,
                )],
            )
            updated_count += 1
            print(f"    ~ updated [{note.note_id}] [{note.category}] {note.content}")
        else:
            to_add.append(Document(
                page_content=note.content,
                metadata={"category": note.category, "service": note.service, "session_id": session_id},
                id=str(uuid.uuid4()),
            ))

    if to_add:
        vector_store.add_documents(to_add, ids=[d.id for d in to_add])
        for doc in to_add:
            print(f"    + added [{doc.id}] [{doc.metadata['category']}] {doc.page_content}")

    print(f"  [notes memory] session {session_id}: {len(to_add)} added, {updated_count} updated")



async def run_memory_sweep(llm) -> None:
    session_ids = await get_unprocessed_sessions()
    print(f"[MEMORY SWEEP] {len(session_ids)} session(s) not yet processed")

    for session_id in session_ids:
        messages = await get_session_messages(session_id)
        print(f"[MEMORY SWEEP] session {session_id}: {len(messages)} message(s) to scan")

        await extract_incident_memory(session_id, messages, llm)
        await mark_session_processed(session_id, incident=True)

        await extract_notes_memory(session_id, messages, llm)
        await mark_session_processed(session_id, notes=True)

    print(f"[MEMORY SWEEP] done -- {len(session_ids)} session(s) processed")



def recall_from_collection(query: str, collection_name: str, threshold: float = 0.7, k: int = 2) -> list[dict]:
    """
    Vector-similarity recall from a memory collection (incident_memory or
    agent_notes) -- top-k matches, filtered to only those above threshold.
    """
    vector_store = get_vector_store(collection_name=collection_name)
    results = vector_store.similarity_search_with_relevance_scores(query, k=k)
    return [
        {**doc.metadata, "content": doc.page_content, "score": score}
        for doc, score in results
        if score > threshold
    ]
