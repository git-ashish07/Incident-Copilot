from langchain_core.prompts import ChatPromptTemplate, HumanMessagePromptTemplate, SystemMessagePromptTemplate

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