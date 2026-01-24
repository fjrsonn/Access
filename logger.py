from datetime import datetime
from pathlib import Path

LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

LOG_FILE = LOG_DIR / "forense.log"


def log_forense(id_registro, texto, status, origem):
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(
            f"[{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}] "
            f"ID:{id_registro} | "
            f"STATUS:{status} | "
            f"ORIGEM:{origem} | "
            f"TEXTO:{texto}\n"
        )

