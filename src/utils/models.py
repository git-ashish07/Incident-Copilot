from pydantic import BaseModel, Field
from typing import Literal
from langgraph.graph import MessagesState

class ServiceExtraction(BaseModel):
    """
    Type of service extraction from a given incident query to identify which service is being referred to in the query.
    """

    service_name: Literal["auth-service", "checkout-service", "payments-service", "not related to any service"] = Field(
        description = "The name of the service extracted from the incident query"
    )
    reason: str = Field(
        description = "One liner justification for why do you think the query is related to the service you have identified. If the query is not related to any service, then explain why it is not related to any service."
    )

class Timeframe(BaseModel):
    """
    Timeframe for log or metric retrieval, defined by a start and end window.
    """
    start_window: str = Field(description="ISO 8601 UTC timestamp, e.g. '2026-07-11T02:00:00Z'")
    end_window: str = Field(description="ISO 8601 UTC timestamp, e.g. '2026-07-11T02:15:00Z'")

class GetLogsInput(BaseModel):
    """
    Input schema for retrieving logs for a specific service within a given timeframe.
    """
    service: Literal["payments-service", "checkout-service", "auth-service"]
    timeframe: Timeframe

class GetMetricsInput(BaseModel):
    """
    Input schema for retrieving metrics for a specific service within a given timeframe.
    """
    service: Literal["payments-service", "checkout-service", "auth-service"]
    timeframe: Timeframe

class AgentState(MessagesState):
    """
    State of the agent, including the current incident query, the number of iterations performed, chat history and query count.
    """
    incident_query: str
    iterations: int
    chat_history: list 
    query_count: int
    retrieved_context: str
    recalled_incidents: list
    relevant_notes: list


class IncidentRecord(BaseModel):
    """
    A single incident discussed in a session, extracted from the session's transcript.
    """
    service: Literal["auth-service", "checkout-service", "payments-service", "unknown"] = Field(
        description="The service this incident is about, or 'unknown' if not identified in the conversation."
    )
    symptoms: str = Field(
        description="What the user described or what was observed -- the problem being diagnosed."
    )
    steps_taken: str = Field(
        description="A short summary of what was checked/done during diagnosis (tools called, data reviewed)."
    )
    diagnosis: str = Field(
        description="The conclusion or recommendation given for this incident."
    )
    resolution_status: Literal["resolved", "unresolved", "unclear"] = Field(
        description="Whether the incident appeared resolved, unresolved, or unclear by the end of the conversation."
    )

class IncidentExtraction(BaseModel):
    """
    All distinct incidents identified in a session's transcript.
    """
    incidents: list[IncidentRecord] = Field(
        description="One entry per distinct incident actually diagnosed in this session. Exclude generic/policy questions that weren't about diagnosing a specific incident."
    )


class NoteAction(BaseModel):
    """
    One note to add or update in long-term notes memory.
    """
    action: Literal["add", "update"] = Field(
        description="Whether this is a brand-new note or an update to an existing one."
    )
    note_id: str | None = Field(
        default=None,
        description="Required only when action is 'update' -- the id of the existing note being updated, from the list shown to you."
    )
    category: Literal["fact", "preference", "correction", "pattern"] = Field(
        description="Which of the four note categories this is."
    )
    content: str = Field(description="The note itself, one or two sentences.")
    service: Literal["auth-service", "checkout-service", "payments-service", "general"] = Field(
        description="Which service this note is about, or 'general' if it applies broadly."
    )

class NotesExtraction(BaseModel):
    """
    Zero or more notes worth adding or updating based on a session.
    """
    notes: list[NoteAction] = Field(
        description="Empty list if nothing from this session is worth remembering long-term."
    )
