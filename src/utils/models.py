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