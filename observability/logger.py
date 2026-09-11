import json
from datetime import datetime
from pathlib import Path


def log_event(file_name, event):

    evidence_dir = Path("evidence")

    evidence_dir.mkdir(exist_ok=True)

    log_path = evidence_dir / file_name

    event["timestamp"] = datetime.now().isoformat()

    with open(log_path, "a") as file:
        file.write(json.dumps(event) + "\n")