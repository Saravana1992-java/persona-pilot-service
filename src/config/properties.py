import logging
import os

from google.cloud import secretmanager
from google.cloud.sql.connector import IPTypes

from src.config import ic_logging
from src.constants.envs import Env

# Environment Properties
env = os.environ['ENV']

# PGSQL Properties
pgsql_ip_type = IPTypes.PRIVATE
pgsql_driver = "asyncpg"
get_resume_pages_by_user_permission_query = ("SELECT * FROM TABLE_NAME")

# Ford LLM Summarizer
insufficient_information_reply = "I'm sorry, but I couldn't answer your query due to Insufficient information."
summary_context = (f"You will be provided with some set of information such as title, description, authors & regions "
                   f"(in json format) about the same topic. "
                   f"Your knowledge consists of proprietary sources and publicly available information, but you always "
                   f"prioritize internal sources. "
                   f"Your purview includes internal assets, such as connected vehicle data (usage/diagnostics/ "
                   f"telematics),business operations data, manufacturing data, diagnostic data, purchased data. "
                   f"When replying to a basic search term or phrase, by default provide high-level summary information"
                   f" about that topic. Your goal is to help users quickly understand the main points. "
                   f"In the case of more complex requests, break things down into smaller, discrete points and refer"
                   f" to the sources of information. "
                   f"Always take extra steps to deeply consider responses prior to sending for veracity. If there is "
                   f"missing information in your knowledge recognize the lack of information and provide transparency. "
                   f"You’re keenly aware of security and can refuse to answer questions that would violate policy, "
                   f"are too invasive, or otherwise may breach code of conduct. "
                   f"Finally, you produce correct outputs that provide the right balance between solving the "
                   f"immediate problem and remaining generic and flexible.")

keyword_extraction_context = ("You are a proficient AI with a specialty in distilling information into key points "
                              "and extract keywords from the text. Based on the following text, identify and "
                              "extract the main words from it reply as a list of words in json format. Use following "
                              "format for output ({\"keywords\": []]}).")

analyse_user_query_prompt = ("You are an expert in language comprehension and analysis. Based on the following two "
                             "topics or queries, determine if these topics or queries are the same. Respond with "
                             "'yes' if they are the same, 'no' if they are different, and 'unsure' if you cannot "
                             "determine. ")


class LocalProperties:
    def __init__(self, bean_id):
        self.bean_id = bean_id

        # Elasticsearch Constants
        self.es_url = "https://bd91b923e53a4fc5ade3c27a06d7173a.psc.us-central1.gcp.cloud.es.io:9243/"

        # CSV file
        self.data_file = "../data/InsightsDataProd.csv"

        # Logging
        self.log_level = logging.INFO


def prop(bean_id):
    """
    Retrieves the appropriate properties object based on the current GCP environment.

    This function uses a factory method to fetch the properties object associated with the current GCP environment.
    The properties objects are defined in a dictionary with their corresponding class constructors.

    Returns:
    LocalProperties or DevProperties or QaProperties or ProdProperties: An instance of the corresponding properties
    class, representing the fetched properties object.
    """
    props = {
        Env.LOCAL.name: lambda: LocalProperties(bean_id)
    }
    ic_logging.get_logger(__name__).debug("env::" + env)
    return props[env]()
