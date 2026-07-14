# set current directory to the main project directory
import os

curr_dir = os.getcwd()
print("Current directory: ", curr_dir)
root_dir = os.path.dirname(os.path.abspath(__file__))  # resolves to Incident-Copilot/
if os.path.abspath(curr_dir) != root_dir:
    os.chdir(root_dir)
    print("Changed to Root directory: ", os.getcwd())
else:
    print("Already in Root directory: ", curr_dir)


# importing llm related functions
from src.llm_funcs.llm_config import llm_instance

# importing prompt related functions
from src.prompts.system_prompts import incident_system_prompt
from src.prompts.prompt_template import get_incident_prompt_template
from src.data.sample_incident_queries import queries

# importing dotenv to load environment variables
from dotenv import load_dotenv
load_dotenv()

def main():
    # Initialize the LLM instance
    llm = llm_instance(api_key=os.getenv("GROQ_API_KEY"))

    # Get the incident prompt template
    incident_prompt_template = get_incident_prompt_template(incident_system_prompt)

    # Get the sample incident queries for dry run
    incident_queries = queries

    for incident_query in incident_queries:
        print(f"\n{'=' * 50}")
        print("\nIncident Query: ", incident_query)

        # Create a chain of the prompt template and the LLM
        incident_chain = incident_prompt_template | llm

        # Generate a response from the LLM
        incident_response = incident_chain.invoke({"incident_query": incident_query}).content

        # Print the response
        print("\nLLM Response:\n", incident_response)


if __name__ == "__main__":
    main()
