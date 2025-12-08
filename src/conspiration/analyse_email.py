from transformers import pipeline
from datetime import datetime, timedelta

# ============================================================
# 🔥 LOAD MODELS ONCE (GLOBAL SINGLETONS)
# ============================================================

print("Carregando modelos de NLP...")

SENTIMENT_MODEL = pipeline(
    "sentiment-analysis",
    model="nlptown/bert-base-multilingual-uncased-sentiment",
    tokenizer="nlptown/bert-base-multilingual-uncased-sentiment",
    device=-1
)

ZERO_SHOT_MODEL = pipeline(
    "zero-shot-classification",
    model="MoritzLaurer/mDeBERTa-v3-base-mnli-xnli",
    device=-1
)

print("Modelos carregados com sucesso!\n")


# ============================================================
# 🔥 SENTIMENT ANALYSIS
# ============================================================
def sentiment_pipeline(text: str):
    result = SENTIMENT_MODEL(text)[0]   
    stars = int(result["label"][0])

    if stars <= 2:
        label = "NEG"
    elif stars == 3:
        label = "NEU"
    else:
        label = "POS"

    return {"label": label, "raw_label": result["label"], "score": result["score"]}


# ============================================================
# 🔥 ZERO-SHOT TOPIC CLASSIFICATION
# ============================================================
def zero_shot_pipeline(text: str, labels):
    result = ZERO_SHOT_MODEL(text, candidate_labels=labels, multi_label=True)
    return {"labels": result["labels"], "scores": result["scores"]}


# ============================================================
# 🔥 FULL PIPELINE FOR EACH EMAIL
# ============================================================
def initial_impression_pipeline(emails_json):
    results = []

    for email in emails_json:
        subject = email.get("subject", "")
        body = email.get("body", "")
        sender = email.get("from", "").lower()

        text = subject + "\n" + body

        sentiment = sentiment_pipeline(text)
        topics = zero_shot_pipeline(text, [
            "conspiracy", "suspicious", "complaint",
            "procedural", "work-related", "personal"
        ])

        conspiracy_score = topics["scores"][topics["labels"].index("conspiracy")]
        sentiment_neg = 1 if sentiment["label"] == "NEG" else 0
        sender_flag = 1 if "michael" in sender else 0
        mentions_toby = 1 if "toby" in text.lower() else 0

        suspicion_score = (
            0.45 * sender_flag +
            0.15 * mentions_toby +
            0.25 * conspiracy_score +
            0.15 * sentiment_neg
        )

        results.append({
            "id": email["id"],
            "from": email.get("from", ""),
            "subject": subject,
            "body": body,
            "sentiment": sentiment,
            "topics": topics,
            "suspicion_score": suspicion_score
        })

    return results


# ============================================================
# 🔥 GROUPING LOGIC
# ============================================================
def parse_date(date_str):
    return datetime.strptime(date_str, "%Y-%m-%d %H:%M")


def group_suspicious_with_michael_context(emails_json, scores_json, threshold=0.8):
    email_by_id = {email["id"]: email for email in emails_json}
    suspicious = [s for s in scores_json if s["suspicion_score"] >= threshold]

    groups = []

    for sus in suspicious:
        sus_email = email_by_id[sus["id"]]
        sus_date = parse_date(sus_email["date"])

        lower = sus_date - timedelta(hours=32)
        upper = sus_date + timedelta(hours=32)

        context = []
        for email in emails_json:
            if "michael.scott" in email["from"].lower():
                date = parse_date(email["date"])
                if lower <= date <= upper:
                    context.append(email)

        groups.append({
            "suspect_email": sus_email,
            "context_emails": context
        })

    return groups
