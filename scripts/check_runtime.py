"""Verify the production environment installed from the same manifest as Vercel.

Run with `uv run --locked --no-dev python -m scripts.check_runtime`, never from
the development venv: globally installed test dependencies can hide this failure.
"""

import importlib
import re
import tomllib
from importlib.metadata import version
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
IMPORTS = {
    "fastapi": "fastapi",
    "uvicorn": "uvicorn",
    "sqlalchemy": "sqlalchemy",
    "pydantic": "pydantic",
    "python-dotenv": "dotenv",
    "psycopg2-binary": "psycopg2",
    "httpx": "httpx",
}


def main():
    manifest = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    dependencies = dict(dependency.split("==") for dependency in manifest["project"]["dependencies"])
    requirements = dict(re.findall(r"^([A-Za-z0-9_-]+)==([^\s\\]+)", (ROOT / "requirements.txt").read_text(), re.M))
    for package, module in IMPORTS.items():
        assert dependencies[package] == requirements[package], f"Manifest and requirements disagree: {package}"
        assert version(package) == dependencies[package], f"Wrong production version: {package}"
        importlib.import_module(module)
    # Mirrors Vercel's import step; the engine does not connect until an API request.
    from api.main import app

    assert app.title == "Календарь мероприятий ТПУ"
    print("Production dependencies and api.main:app import OK")


if __name__ == "__main__":
    main()
