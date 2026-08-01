from pathlib import Path

DEFAULT_VERSION = "0.3.4"


def get_version() -> str:
    candidates = [
        Path("/app/VERSION"),
        Path(__file__).resolve().parents[3] / "VERSION",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate.read_text(encoding="utf-8").strip()
    return DEFAULT_VERSION
