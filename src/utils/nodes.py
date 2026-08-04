"""
LangGraph node definitions for the incident-diagnosis agent.
"""

import json
from groq import BadRequestError
from langchain_core.messages import ToolMessage, AIMessage, HumanMessage, RemoveMessage
from langgraph.graph.message import REMOVE_ALL_MESSAGES
from src.utils.models import AgentState
from src.utils.rag.retrieval_funcs import retrieval_pipeline
from src.utils.memory import recall_from_collection


def _format_chat_history(chat_history: list | None) -> str:
    """
    Format the chat history into a string representation for use in prompts.
    """
    # chat_history holds real message objects (query/tool_response/final_answer), render them as plain text for the prompt
    if not chat_history:
        return "(no prior conversation)"
    return "\n".join(f"{type(msg).__name__.replace('Message', '')}: {msg.content}" for msg in chat_history)

def _format_recalled_incidents(incidents: list[dict]) -> str:
    """
    Format a list of recalled incidents into a string representation for use in prompts.
    """
    if not incidents:
        return "(none found)"
    return "\n".join(
        f"- Service: {inc.get('service')} | Symptoms: {inc.get('symptoms')} | "
        f"Diagnosis: {inc.get('diagnosis')} | Status: {inc.get('resolution_status')} "
        f"(similarity: {inc.get('score'):.2f})"
        for inc in incidents
    )

def _format_relevant_notes(notes: list[dict]) -> str:
    """
    Format a list of relevant notes into a string representation for use in prompts.
    """
    if not notes:
        return "(none found)"
    return "\n".join(f"- [{n.get('category')}] {n.get('content')}" for n in notes)

# the reason to have nodes within functions is to inject dependencies through these functions into the node
def make_retrieve_node(vectordb_instance, prompt_template):
    """
    Retrieve node for the incident-diagnosis agent.

    Args:
        vectordb_instance: The vector database instance to use for retrieval.
        prompt_template: The prompt template to format the retrieved context.

    Returns:
        A function that takes an AgentState and returns a dictionary with messages and iterations.
    """

    async def retrieve(state: AgentState):
        """
        Retrieve relevant context for the incident query and format messages.

        Args:
            state (AgentState): The current state of the agent, containing the incident query and iteration count. Langgraph will pass the state to this function automatically on invoke.
        
        Returns:
            dict: A dictionary containing the formatted messages and the current iteration count.
        """

        # retrieval only ever uses the raw query, chat_history has no influence here
        retrieved_context = retrieval_pipeline(
            query = state["incident_query"],
            vector_store = vectordb_instance,
            collection_name = "incident_corpus"
        )

        # fallback for turn 1, when there's no prior conversation yet
        chat_history_text = _format_chat_history(state.get("chat_history"))

        # long-term memory recall -- separate from chat_history, keyed by similarity not by session
        recalled_incidents = recall_from_collection(state["incident_query"], "incident_memory")
        relevant_notes = recall_from_collection(state["incident_query"], "agent_notes")

        new_messages = prompt_template.format_messages(
            incident_query = state["incident_query"],
            retrieved_context = retrieved_context,
            chat_history = chat_history_text,
            recalled_incidents = _format_recalled_incidents(recalled_incidents),
            relevant_notes = _format_relevant_notes(relevant_notes),
        )

        # wipe last turn's messages first, messages is only a scratchpad for current turn's tool loop
        return {
            "messages": [RemoveMessage(id=REMOVE_ALL_MESSAGES)] + new_messages,
            "iterations": 0,
            "retrieved_context": retrieved_context,
            "recalled_incidents": recalled_incidents,
            "relevant_notes": relevant_notes,
        }

    return retrieve

def make_llm_call_node(llm):
    """
    LLM call node for the incident-diagnosis agent.

    Args:
        llm: The tool-bound LLM instance to invoke.

    Returns:
        A function that takes an AgentState and returns a dictionary with the new message and updated iteration count.
    """ 

    async def llm_call(state: AgentState):
        """
        Ask the LLM what to do next, given the conversation so far.

        Args:
            state (AgentState): The current state of the agent.

        Returns:
            dict: A dictionary containing the LLM's response and the incremented iteration count.
        """

        response = None

        max_retries = 3
        for attempt in range(1, max_retries + 1):
            try:
                response = llm.invoke(state["messages"])
                break
            except BadRequestError as e:
                print(f"  [llm_call] attempt {attempt} failed (tool-call generation error): {e}")
                if attempt == max_retries:
                    response = AIMessage(content="I ran into a repeated error trying to process this request. Could you rephrase your question?")

        # we dont need to return all messages because langgraph's reducer will do this for us
        update = {"messages": [response], "iterations": state["iterations"] + 1}

        # a real final answer (no tool_calls) means this turn is done, fold it into chat_history
        if not response.tool_calls:
            tool_msgs = [m for m in state["messages"] if isinstance(m, ToolMessage)]
            # rebuild the query fresh from incident_query, not from state["messages"], that copy has retrieved_context/chat_history baked in too
            this_turn = [HumanMessage(content=state["incident_query"])] + tool_msgs + [response]

            update["chat_history"] = (state.get("chat_history") or []) + this_turn
            update["query_count"] = state.get("query_count", 0) + 1

        return update


    return llm_call


def make_tools_node(client):
    """
    Tools node for the incident-diagnosis agent.

    Args:
        client: The MCP client instance used to dispatch tool calls.

    Returns:
        A function that takes an AgentState and returns a dictionary with the tool results as new messages.
    """

    async def tools(state: AgentState):
        """
        Run every tool call the LLM requested in its last message, via MCP.

        Args:
            state (AgentState): The current state of the agent, containing the LLM's last response with its tool_calls.

        Returns:
            dict: A dictionary containing one ToolMessage per tool call made.
        """

        last_message = state["messages"][-1] # the last message is the LLM's response, which may contain tool_calls
        tool_messages = []

        if not last_message.tool_calls:
            return {"messages": []}  # no tool calls to make

        for tool_call in last_message.tool_calls:
            result = await client.call_tool(tool_call["name"], tool_call["args"])
            result_payload = result.data if result.data is not None else result.structured_content

            tool_messages.append(ToolMessage(content=json.dumps(result_payload), tool_call_id=tool_call["id"]))
            
        # only the new tool results are returned -- same reason as llm_call, the reducer appends these for us
        return {"messages": tool_messages}

    return tools        


async def give_up(state: AgentState):
    """
    Graceful fallback when the agent has used up its iteration budget without reaching a final answer.

    Args:
        state (AgentState): The current state of the agent.

    Returns:
        dict: A dictionary containing a fallback AIMessage as the final answer.
    """

    return {"messages": [AIMessage(content="Reached max iterations without a final answer.")]}


def make_router(max_iterations: int):
    """
    Routing function for the incident-diagnosis agent, run after every llm_call.

    Args:
        max_iterations: The maximum number of llm_call iterations allowed before giving up.

    Returns:
        A function that takes an AgentState and returns the name of the next node to run.
    """

    def route_after_llm_call(state: AgentState) -> str:
        """
        Decide what happens after the LLM's latest response.

        Args:
            state (AgentState): The current state of the agent.

        Returns:
            str: "end" if the LLM gave a final answer, "give_up" if the iteration budget is used up, otherwise "tools".
        """

        last_message = state["messages"][-1]

        if not last_message.tool_calls:
            return "end"

        if state["iterations"] >= max_iterations:
            return "give_up"

        return "tools"

    return route_after_llm_call