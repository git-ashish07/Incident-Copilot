from langchain_core.prompts import ChatPromptTemplate, HumanMessagePromptTemplate, SystemMessagePromptTemplate
from langchain_core.documents import Document

def get_incident_prompt_template(system_prompt: str) -> ChatPromptTemplate:
    """
    Returns a ChatPromptTemplate for incident response triage.

    Args:
        system_prompt (str): The system prompt to use in the template.

    Returns:
        ChatPromptTemplate: A chat prompt template for incident response triage.
    """
    return ChatPromptTemplate.from_messages([
        SystemMessagePromptTemplate.from_template(system_prompt),
        HumanMessagePromptTemplate.from_template("""
        [INPUT]
        Incident query: {incident_query}
        """),    
    ])


def get_incident_rag_template(system_prompt: str) -> ChatPromptTemplate:
    """
    Returns a ChatPromptTemplate for incident response triage that's grounded
    in retrieved context (runbook/postmortem/service-doc chunks from the RAG
    pipeline).

    Args:
        system_prompt (str): The RAG-aware system prompt to use in the
            template (see incident_rag_system_prompt).

    Returns:
        ChatPromptTemplate: expects `incident_query`, `retrieved_context`,
            and `tool_response` when invoked — use format_retrieved_context()
            to build `retrieved_context` from a list of retrieved Documents.
            `tool_response` should be an empty string when no tool was
            called this turn (it's shown as a blank section, not omitted).
    """
    return ChatPromptTemplate.from_messages([
        SystemMessagePromptTemplate.from_template(system_prompt),
        HumanMessagePromptTemplate.from_template("""
        [RETRIEVED CONTEXT]
        {retrieved_context}

        [TOOL RESPONSE]
        {tool_response}

        [INPUT]
        Incident query: {incident_query}
        """),
    ])