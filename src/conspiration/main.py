import os, hashlib, json
from dotenv import load_dotenv

from .load_emails import load_emails
from .analyse_email import (
    initial_impression_pipeline,
    group_suspicious_with_michael_context
)
from .llm_agent import analyze_cluster_with_agent
from .report_generator import generate_final_report

def hash_file(path: str) -> str:
    """
    Returns SHA256 hash of the file content.
    Used to detect if emails.txt changed.
    """
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()

SCORES_CACHE_PATH = "data/scores_cache.json"


def load_cache(path: str):
    """Load JSON cache file if it exists."""
    if not os.path.exists(path):
        return None

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_cache(path: str, data: dict):
    """Save cache file to 'data/' directory."""
    os.makedirs(os.path.dirname(path), exist_ok=True)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def main():

    print("Carregando variáveis de ambiente...")
    load_dotenv()
    api_key = os.getenv("NVIDIA_API_KEY")
    if not api_key:
        raise ValueError("NVIDIA_API_KEY não encontrada no arquivo .env!")

    # Caminho do arquivo de emails
    emails_path = os.path.join(os.path.dirname(__file__), "../../data/emails.txt")

    print("Carregando emails...")
    emails = load_emails(emails_path)
    print(f"→ {len(emails)} emails carregados.")

    # Hash do arquivo para saber se mudou
    emails_hash = hash_file(emails_path)

    print("\nVerificando cache de classificação...")
    cache = load_cache(SCORES_CACHE_PATH)

    if cache and cache["emails_hash"] == emails_hash:
        print("Cache válido encontrado! Pulando classificação inicial.")
        scores_json = cache["scores"]
    else:
        print("Cache inexistente ou inválido. Recalculando scoring completo...")
        scores_json = initial_impression_pipeline(emails)

        save_cache(SCORES_CACHE_PATH, {
            "emails_hash": emails_hash,
            "scores": scores_json
        })

        print("Scores salvos em cache.")

    print("\nDetectando clusters suspeitos...")
    clusters = group_suspicious_with_michael_context(emails, scores_json)
    print(f"→ {len(clusters)} clusters detectados.")

    if len(clusters) == 0:
        print("\nNenhuma suspeita encontrada. Encerrando.")
        return

    print("\nRodando LLM para cada cluster...")
    cluster_reports = []
    for idx, cluster in enumerate(clusters, start=1):
        print(f"Analisando cluster #{idx}...")
        analysis = analyze_cluster_with_agent(cluster)
        cluster_reports.append(analysis)

    print("\nGerando relatório final...")
    final_report = generate_final_report(cluster_reports)

    print("\n================ RELATÓRIO FINAL =====================\n")
    print(final_report)

    os.makedirs("output", exist_ok=True)
    with open("src/conspiration/output/final_report.txt", "w", encoding="utf-8") as f:
        f.write(final_report)

    print("\nRelatório salvo em output/final_report.txt")
    print("Pipeline concluída com sucesso.")


if __name__ == "__main__":
    main()
