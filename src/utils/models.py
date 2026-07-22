from pydantic import BaseModel, Field
from typing import Literal

class ServiceExtraction(BaseModel):
    """
    Type of service extraction from a given incident query to identify which service is being referred to in the query.
    """

    service_name: Literal["auth-service", "checkout-service", "payments-service", "None"] = Field(
        description = "The name of the service extracted from the incident query"
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