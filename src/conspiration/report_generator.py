from langchain.prompts import ChatPromptTemplate
from langchain.schema import HumanMessage
from llm_agent import llm


REPORT_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        """
        You are a summarization expert.

        Generate a FINAL REPORT that includes:
        1. Narrative of the full investigation  
        2. Summary of evidence  
        3. Profiles of individuals  
        4. Final conclusion: Is Michael conspiring against Toby?  

        Only use the provided analyses.
        """
    ),
    ("human", "{cluster_analyses}")
])


def generate_final_report(cluster_analysis_texts):
    joined = "\n\n--- CLUSTER BREAK ---\n\n".join(cluster_analysis_texts)

    response = llm([
        HumanMessage(content=REPORT_PROMPT.format(cluster_analyses=joined))
    ])

    return response.content
