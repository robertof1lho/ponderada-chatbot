from load_emails import load_emails
from analyse_email import (
    initial_impression_pipeline,
    group_suspicious_with_michael_context
)
from llm_agent import analyze_cluster_with_agent
from report_generator import generate_final_report


# 1. Load emails
emails = load_emails("emails.txt")

# 2. Analyse emails
scores_json = initial_impression_pipeline(emails)

# 3. Detect clusters
clusters = group_suspicious_with_michael_context(emails, scores_json)

# 4. Run AI agent on each cluster
cluster_reports = []
for cluster in clusters:
    report = analyze_cluster_with_agent(cluster)
    cluster_reports.append(report)

# 5. Final Investigation Report
final_report = generate_final_report(cluster_reports)

print(final_report)
