from langchain_core.prompts import ChatPromptTemplate, HumanMessagePromptTemplate, SystemMessagePromptTemplate

# Used until Week 1 Tasks 6-7 (ingestion + retrieval) exist. Once retrieval
# is wired in, callers should pass the actual formatted retrieved chunks
# (with source labels) as `retrieved_context` instead of this placeholder.
NO_CONTEXT_PLACEHOLDER = "(no retrieved context available yet — retrieval pipeline not implemented)"


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
        [RETRIEVED CONTEXT]
        {retrieved_context}

        [INPUT]
        Incident query: {incident_query}
        """),
    ])