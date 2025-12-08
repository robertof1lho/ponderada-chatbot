import os
from dotenv import load_dotenv
from langchain.prompts import ChatPromptTemplate
from langchain.chat_models import ChatOpenAI
from langchain.schema import HumanMessage

load_dotenv()
API_KEY = os.getenv("NVIDIA_API_KEY")

llm = ChatOpenAI(
    model="nvidia/llama-3.3-nemotron-super-49b-v1.5",
    openai_api_key=API_KEY,
    openai_api_base="https://integrate.api.nvidia.com/v1"
)


AGENT_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        """
        You are an AI Investigation Agent.

        Toby suspects that Michael Scott is conspiring against him.
        Analyze the provided email cluster and extract:

        1. Narrative summary  
        2. Evidence (quotes, timestamps, behavior)  
        3. Profiles of individuals involved  
        4. Cluster conclusion  

        Stick strictly to the email content. Do not hallucinate.
        """
    ),
    ("human", "{cluster_text}")
])


def analyze_cluster_with_agent(cluster):
    lines = []

    s = cluster["suspect_email"]
    lines.append("=== SUSPICIOUS EMAIL ===")
    lines.append(f"From: {s['from']}")
    lines.append(f"Date: {s['date']}")
    lines.append(f"Subject: {s['subject']}")
    lines.append(f"Body:\n{s['body']}")

    lines.append("\n=== CONTEXT EMAILS ===")
    for ctx in cluster["context_emails"]:
        lines.append("-----------------------")
        lines.append(f"From: {ctx['from']}")
        lines.append(f"Date: {ctx['date']}")
        lines.append(f"Subject: {ctx['subject']}")
        lines.append(f"Body:\n{ctx['body']}")

    cluster_text = "\n".join(lines)

    response = llm([
        HumanMessage(
            content=AGENT_PROMPT.format(cluster_text=cluster_text)
        )
    ])

    return response.content
