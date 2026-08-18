from pathlib import Path


def project_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent


def data_path(*parts: str) -> Path:
    return project_root() / "data" / Path(*parts)
