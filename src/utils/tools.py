import os
import json
import pandas as pd
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, ToolMessage, SystemMessage
from langchain_core.tools import tool
from fastmcp import FastMCP
from typing import Literal

from src.utils.llm_config import llm_instance, llm_openai_instance
from src.utils.models import ServiceExtraction, GetLogsInput, GetMetricsInput, Timeframe


# Initialize MCP server
mcp = FastMCP("Incident MCP Server")

# -------------------------- Tool to get current time --------------------------
# this function mimics real functionality of getting current time, but for now it just returns a static string "2026-07-11T02:15:00Z"
@mcp.tool
def get_current_time() -> dict:
    """
    Always use this tool to get the current time. This ensures that the LLM doesn't hallucinate on the timeframe.

    Returns:
        dict: A dictionary containing the current time with the key "current_time".
    """
    return {"current_time": "2026-07-11T02:15:00Z"}

# -------------------------- Tool to identify service from incident query --------------------------
@mcp.tool
def identify_service(incident_query: str) -> dict:
    """
    This tool identifies the service mentioned in the incident query to determine for which service the incident is being reported. 
    This helps in identifying the logs/metrics of correct service to be retrieved for further analysis.
    The request could be related to one of the following services: "auth-service", "checkout-service", "payments-service".

    Args:
        incident_query (str): The incident query string.

    Returns:
        dict: A dictionary containing the identified service name and the reason for the identification.
    """

    # llm = llm_instance(api_key=os.getenv("GROQ_API_KEY"))
    llm = llm_openai_instance(api_key=os.getenv("OPENAI_API_KEY"))
    structured_llm = llm.with_structured_output(ServiceExtraction)


    system_message = SystemMessage(
        content="""You are a service identification assistant. You will be given an incident query and your task is to identify the service that the query could be closest related to, based on the content mentioned in the query.
        Pick the closest service from the following list based on the query: ['auth-service', 'checkout-service', 'payments-service'].
        You have to pick one from the list.
        """
    )
    response = structured_llm.invoke([system_message, HumanMessage(content=incident_query)])

    return {"service_name": response.service_name, "reason": response.reason}
    
# -------------------------- Tool to get logs for a given service and timeframe --------------------------
# @tool(args_schema=GetLogsInput)
# def get_logs(service: str, timeframe: dict):
@mcp.tool
def get_logs(service: Literal["auth-service", "checkout-service", "payments-service", "not related to any service"], timeframe: Timeframe) -> dict:
    """
    This tool retrieves logs for a given service within a specified timeframe. 
    Service can be one of the following: "auth-service", "checkout-service", "payments-service". 
    The timeframe is an instance of the Timeframe class containing "start_window" and "end_window" in ISO 8601 UTC format.

    Args:
        service (str): The name of the service.
        timeframe (Timeframe): An instance of the Timeframe class containing the start and end time for the log retrieval.

    Returns:
        dict: A dictionary containing the metadata of the logs requested, including the service name and timeframe, and a list of log entries.
    """

    if service == "not related to any service":
        return {"error": f"Service not related",
                "message": f"The incident query is not related to any service. Therefore, logs cannot be retrieved for the given timeframe."
                }

    # extract the start and end date from the timeframe dictionary
    start_window = timeframe.start_window
    end_window = timeframe.end_window

    start_date = start_window.split("T")[0] if start_window else None
    end_date = end_window.split("T")[0] if end_window else None

    # create the name of log files dynamically based on the service name and the start and end date
    # we might be asked to retrieve logs spanning several days, so enumerate every date in the
    # span rather than just the two endpoints (otherwise days in between get silently skipped)
    dates = [d.strftime("%Y-%m-%d") for d in pd.date_range(start_date, end_date)] if start_date and end_date else [start_date or end_date]

    log_files = [f"{service}_{date}.jsonl" for date in dates if date]

    # getting current directory to read the log files from the data/logs folder
    curr_dir = os.getcwd()

    # we need to handle cases where for a date log files might not exist, so we will check if the log files exist before trying to read them. If not then return an error message to the user indicating that the log files do not exist for the given timeframe.
    try:
        # first check if the service is correct
        if service not in ["auth-service", "checkout-service", "payments-service"]:
            return {"error": f"Invalid service",
                    "message": f"Service '{service}' is not valid. Logs are available only for ['auth-service', 'checkout-service', 'payments-service']. Please confirm the service name and try again."
                    }
    
        # check if the log files exist for the given timeframe, reading and
        # accumulating across all of them before returning, since a timeframe
        # can span more than one day (and therefore more than one file)
        log_rows = []
        source_files = []

        for file in log_files:
            file_path = os.path.join(curr_dir, "src", "data", "logs", file)
            if not os.path.exists(file_path):
                return {"error": f"Log file not found",
                        "message": f"Log file '{file}' does not exist for the given timeframe. Logs exist only for the this period: 2026-07-05 to 2026-07-11. Please get the timeframe within this period and try again."
                        }

            # read the log file and filter it to the timeframe requested by the user
            log_df = pd.read_json(file_path, lines=True)
            log_df = log_df[(log_df["timestamp"] >= start_window) & (log_df["timestamp"] <= end_window)]
            log_df.drop('request_id', axis=1, inplace=True)

            for idx, row in log_df.iterrows():
                log_rows.append(row.to_json())

            source_files.append(file)

        return {
            "service": service,
            "timeframe": timeframe.model_dump(),
            "source_files": source_files,
            "logs": log_rows
        }

    except Exception as e:
        print(f"An error occurred: {e}")
        return {"error": str(e)}

# -------------------------- Tool to get metrics for a given service and timeframe --------------------------
# @tool(args_schema=GetMetricsInput)
# def get_metrics(service: str, timeframe: dict):
@mcp.tool
def get_metrics(service: Literal["auth-service", "checkout-service", "payments-service", "not related to any service"], timeframe: Timeframe) -> dict:

    """
    This tool retrieves metrics for a given service within a specified timeframe.
    Service can be one of the following: "auth-service", "checkout-service", "payments-service".
    The timeframe is an instance of the Timeframe class containing "start_window" and "end_window" in ISO 8601 UTC format.

    Args:
        service (str): The name of the service.
        timeframe (Timeframe): An instance of the Timeframe class containing the start and end time for the metrics retrieval.

    Returns:
        dict: A dictionary containing the metadata of the metrics requested, including the service name and timeframe, and a list of metric entries.
    """

    if service == "not related to any service":
        return {"error": f"Service not related",
                "message": f"The incident query is not related to any service. Therefore, metrics cannot be retrieved for the given timeframe."
                }

    # extract the start and end date from the timeframe dictionary
    start_window = timeframe.start_window
    end_window = timeframe.end_window

    start_date = start_window.split("T")[0] if start_window else None
    end_date = end_window.split("T")[0] if end_window else None

    # create the name of metric files dynamically based on the service name and the start and end date
    # we might be asked to retrieve metrics spanning several days, so enumerate every date in the
    # span rather than just the two endpoints (otherwise days in between get silently skipped)
    dates = [d.strftime("%Y-%m-%d") for d in pd.date_range(start_date, end_date)] if start_date and end_date else [start_date or end_date]

    metric_files = [f"{service}_{date}.csv" for date in dates if date]

    # getting current directory to read the log files from the data/logs folder
    curr_dir = os.getcwd()

    # we need to handle cases where for a date metric files might not exist, so we will check if the metric files exist before trying to read them. If not then return an error message to the user indicating that the metric files do not exist for the given timeframe.
    try:
        # first check if the service is correct
        if service not in ["auth-service", "checkout-service", "payments-service"]:
            return {"error": f"Invalid service",
                    "message": f"Service '{service}' is not valid. Metrics are available only for ['auth-service', 'checkout-service', 'payments-service']. Please confirm the service name and try again."
                    }

        # check if the metric files exist for the given timeframe, reading and
        # accumulating across all of them before returning, since a timeframe
        # can span more than one day (and therefore more than one file)
        metrics_rows = []
        source_files = []

        for file in metric_files:
            file_path = os.path.join(curr_dir, "src", "data", "metrics", file)
            if not os.path.exists(file_path):
                return {"error": f"Metric file not found",
                        "message": f"Metric file '{file}' does not exist for the given timeframe. Metrics exist only for the this period: 2026-07-05 to 2026-07-11. Please get the timeframe within this period and try again."
                        }

            # read the metric file and filter it to the requested timeframe
            metric_df = pd.read_csv(file_path)
            metric_df = metric_df[(metric_df["timestamp"] >= start_window) & (metric_df["timestamp"] <= end_window)]

            for idx, row in metric_df.iterrows():
                metrics_rows.append(row.to_json())

            source_files.append(file)

        return {
            "service": service,
            "timeframe": timeframe.model_dump(),
            "source_files": source_files,
            "metrics": metrics_rows
        }

    except Exception as e:
        print(f"An error occurred: {e}")
        return {"error": str(e)}
