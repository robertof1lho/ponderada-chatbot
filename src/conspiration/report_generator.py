# report_generator.py

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
import os
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("NVIDIA_API_KEY")

llm = ChatOpenAI(
    model="nvidia/llama-3.3-nemotron-super-49b-v1.5",
    api_key=API_KEY,
    base_url="https://integrate.api.nvidia.com/v1"
)


REPORT_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        """
        You are an AI report generator.

        Using the cluster analyses provided, generate a FINAL REPORT including:

        1. Narrative of the full investigation.
        2. Summary of key evidence.
        3. Profiles of individuals involved.
        4. Final conclusion answering:
           "Is Michael Scott conspiring against Toby?"

        Use only provided evidence.
        Be clear, structured, and analytical.
        Answer in Portuguese.
        """
    ),
    ("human", "{cluster_analyses}")
])


def generate_final_report(cluster_analysis_texts):
    joined = "\n\n====== CLUSTER BREAK ======\n\n".join(cluster_analysis_texts)

    response = llm.invoke(
        REPORT_PROMPT.format(cluster_analyses=joined)
    )

    return response.content
