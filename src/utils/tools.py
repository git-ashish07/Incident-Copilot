import os
import json
import pandas as pd
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, ToolMessage, SystemMessage
from langchain_core.tools import tool

from src.utils.llm_config import llm_instance
from src.utils.models import ServiceExtraction, GetLogsInput, GetMetricsInput

# -------------------------- Tool to get current time --------------------------
# this function mimics real functionality of getting current time, but for now it just returns a static string "2026-07-11T02:15:00Z"
@tool
def get_current_time() -> dict:
    """
    This tool returns the current time in a dictionary format with the key "current_time".

    Returns:
        dict: A dictionary containing the current time with the key "current_time".
    """
    return {"current_time": "2026-07-11T02:15:00Z"}


# -------------------------- Tool to identify service from incident query --------------------------
@tool
def identify_service(incident_query: str) -> str:
    """
    This tool identifies the service mentioned in the incident query to determine for which service the incident is being reported. This helps in identifying the logs/metrics of correct service to be retrieved for further analysis.

    Args:
        incident_query (str): The incident query string.

    Returns:
        str: The name of the identified service.
    """

    llm = llm_instance(api_key=os.getenv("GROQ_API_KEY"))
    structured_llm = llm.with_structured_output(ServiceExtraction)


    system_message = SystemMessage(
        content="You are a service identification assistant. You will be given an incident query and your task is to identify the service mentioned in the query."
    )
    response = structured_llm.invoke([system_message, HumanMessage(content=incident_query)])

    return response.service_name
    
# -------------------------- Tool to get logs for a given service and timeframe --------------------------
@tool(args_schema=GetLogsInput)
def get_logs(service: str, timeframe: dict):
    """
    This tool retrieves logs for a given service within a specified timeframe. 
    Service can be one of the following: "auth-service", "checkout-service", "payments-service". 
    The timeframe is a dictionary containing key value pairs for "start_window" and "end_window" in ISO 8601 UTC format.

    Args:
        service (str): The name of the service.
        timeframe (dict): A dictionary containing the start and end time for the log retrieval.

    Returns:
        dict: A dictionary containing the metadata of the logs requested, including the service name and timeframe, and a list of log entries.
    """

    # extract the start and end date from the timeframe dictionary
    start_window = timeframe.start_window
    end_window = timeframe.end_window

    start_date = start_window.split("T")[0] if start_window else None
    end_date = end_window.split("T")[0] if end_window else None

    # create the name of log files dynamically based on the service name and the start and end date
    # we might be asked to retrieve logs for a single day or multiple days, so we need to handle both cases
    dates = [start_date] if start_date == end_date else [start_date, end_date]

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
    
        # check if the log files exist for the given timeframe
        for file in log_files:
            file_path = os.path.join(curr_dir, "src", "data", "logs", file)
            if not os.path.exists(file_path):
                return {"error": f"Log file not found",
                        "message": f"Log file '{file}' does not exist for the given timeframe. Logs exist only for the this period: 2026-07-05 to 2026-07-11. Please get the timeframe within this period and try again."
                        }
            
            else:
                # read the log file and return the logs in a dictionary format
                with open(file_path, "r") as f:
                    log_df = pd.read_json(file_path, lines=True)

                    # filter it to the timeframe requested by the user
                    log_df = log_df[(log_df["timestamp"] >= start_window) & (log_df["timestamp"] <= end_window)]

                    log_df.drop('request_id', axis=1, inplace=True)

                    log_rows = []

                    for idx, row in log_df.iterrows():
                        json_string = row.to_json()
                        log_rows.append(json_string)
                    
                return {
                    "service": service,
                    "timeframe": timeframe.model_dump(),
                    "logs": log_rows
                }

    except Exception as e:
        print(f"An error occurred: {e}")
        return {"error": str(e)}


# -------------------------- Tool to get metrics for a given service and timeframe --------------------------
@tool(args_schema=GetMetricsInput)
def get_metrics(service: str, timeframe: dict):
    """
    This tool retrieves metrics for a given service within a specified timeframe.
    Service can be one of the following: "auth-service", "checkout-service", "payments-service".
    The timeframe is a dictionary containing key value pairs for "start_window" and "end_window" in ISO 8601 UTC format.

    Args:
        service (str): The name of the service.
        timeframe (dict): A dictionary containing the start and end time for the metrics retrieval.

    Returns:
        dict: A dictionary containing the metadata of the metrics requested, including the service name and timeframe, and a list of metric entries.
    """

    # extract the start and end date from the timeframe dictionary
    start_window = timeframe.start_window
    end_window = timeframe.end_window

    start_date = start_window.split("T")[0] if start_window else None
    end_date = end_window.split("T")[0] if end_window else None

    # create the name of metric files dynamically based on the service name and the start and end date
    # we might be asked to retrieve metrics for a single day or multiple days, so we need to handle both cases
    dates = [start_date] if start_date == end_date else [start_date, end_date]

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

        # check if the metric files exist for the given timeframe
        for file in metric_files:
            file_path = os.path.join(curr_dir, "src", "data", "metrics", file)
            if not os.path.exists(file_path):
                return {"error": f"Metric file not found",
                        "message": f"Metric file '{file}' does not exist for the given timeframe. Metrics exist only for the this period: 2026-07-05 to 2026-07-11. Please get the timeframe within this period and try again."
                        }

            else:
                # read the metric file and filter it to the requested timeframe
                metric_df = pd.read_csv(file_path)

                metric_df = metric_df[(metric_df["timestamp"] >= start_window) & (metric_df["timestamp"] <= end_window)]

                metrics_rows = []

                for idx, row in metric_df.iterrows():
                    json_string = row.to_json()
                    metrics_rows.append(json_string)

                return {
                    "service": service,
                    "timeframe": timeframe.model_dump(),
                    "metrics": metrics_rows
                }

    except Exception as e:
        print(f"An error occurred: {e}")
        return {"error": str(e)}
