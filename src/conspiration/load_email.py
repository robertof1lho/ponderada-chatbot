SEPARATOR = "-------------------------------------------------------------------------------"


def load_raw_email_file(path: str):
    with open(path, 'r') as file:
        lines = [line.strip() for line in file if line.strip()]
    return lines


def parse_email_blocks(lines):
    header = lines[:4]
    body_lines = lines[4:]
    full_text = "\n".join(body_lines)

    blocks = [b.strip() for b in full_text.split(SEPARATOR) if b.strip()]
    return blocks


def email_to_json(bloco, id):
    linhas = bloco.split("\n")

    return {
        "id": id,
        "from": linhas[0].replace("De: ", "").strip(),
        "to": linhas[1].replace("Para: ", "").strip(),
        "date": linhas[2].replace("Data: ", "").strip(),
        "subject": linhas[3].replace("Assunto: ", "").strip(),
        "body": "\n".join(linhas[5:]).strip()
    }


def load_emails(path: str):
    raw = load_raw_email_file(path)
    blocks = parse_email_blocks(raw)

    emails = []
    for i, b in enumerate(blocks, start=1):
        emails.append(email_to_json(b, i))

    return emails
