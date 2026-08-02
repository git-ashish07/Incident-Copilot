from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from src.utils.prompts.system_prompts import chat_history_summary_prompt

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
