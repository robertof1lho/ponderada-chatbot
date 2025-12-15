# llm_agent.py

import os
import re
from dotenv import load_dotenv

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI


load_dotenv()
API_KEY = os.getenv("NVIDIA_API_KEY")

llm = ChatOpenAI(
    model="nvidia/llama-3.3-nemotron-super-49b-v1.5",
    api_key=API_KEY,
    base_url="https://integrate.api.nvidia.com/v1"
)


AGENT_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        """
        You are an AI Investigation Agent.

        TASK CONTEXT:
        Toby suspects that Michael Scott is conspiring against him.
        Your job is to analyze emails and determine whether this conspiracy is real.

        For each cluster of emails (one suspicious email + contextual emails), you must:

        1. Produce a **narrative explanation** of what seems to be happening.
        2. Extract **evidence**, including quotes, timestamps, tone, and relevance.
        3. Generate **profiles of individuals involved**, focusing on Michael Scott and Toby Flenderson.
        4. Provide a **cluster conclusion** answering:
            “Does this cluster indicate potential conspiracy against Toby?”

        IMPORTANT RULES:
        - Stick ONLY to the content of the emails provided.
        - Do NOT hallucinate nonexistent content.
        - Make the analysis concise but thorough.
        - Assume the reader is a human investigator.

        Return the output in this structure:

        {{
            "narrative": "...",
            "evidence": [
                {{
                    "type": "...",
                    "quote": "...",
                    "reason": "..."
                }}
            ],
            "profiles": {{
                "michael": "...",
                "toby": "...",
                "others": ["..."]
            }},
            "cluster_conclusion": "..."
        }}
        """
    ),
    ("human", "{cluster_text}")
])



def analyze_cluster_with_agent(cluster):
    """
    cluster = {
        "suspect_email": {...},
        "context_emails": [...]
    }
    """

    # format cluster as plain text
    lines = []

    s = cluster["suspect_email"]
    lines.append("=== SUSPICIOUS EMAIL ===")
    lines.append(f"ID: {s['id']}")
    lines.append(f"From: {s['from']}")
    lines.append(f"Date: {s['date']}")
    lines.append(f"Subject: {s['subject']}")
    lines.append(f"Body:\n{s['body']}\n")

    lines.append("=== CONTEXT EMAILS ===")
    for ctx in cluster["context_emails"]:
        lines.append("--------------------------")
        lines.append(f"ID: {ctx['id']}")
        lines.append(f"From: {ctx['from']}")
        lines.append(f"Date: {ctx['date']}")
        lines.append(f"Subject: {ctx['subject']}")
        lines.append(f"Body:\n{ctx['body']}\n")

    cluster_text = "\n".join(lines)

    # call the LLM
    response = llm.invoke(
        AGENT_PROMPT.format(cluster_text=cluster_text)
    )

    cleaned_content = re.sub(
        r"<think>.*?</think>", "", response.content, flags=re.DOTALL
    ).strip()

    return cleaned_content
