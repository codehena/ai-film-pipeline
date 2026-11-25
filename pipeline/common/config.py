"""Paths, folders and secrets. Every other module asks this file where things live."""
from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STORYBOARD = ROOT / "storyboard.json"
SCHEMA = ROOT / "schema" / "storyboard.schema.json"
RUNS_LOG = ROOT / "runs.jsonl"
OUTPUTS = ROOT / "outputs"
CACHE = ROOT / "cache"

# One output folder per stage, e.g. outputs/keyframes/
STAGES = ("narration", "keyframes", "shots", "music", "cuts")


class MissingSecret(Exception):
    """A key is missing from .env (or still has its placeholder value)."""


def load_env() -> None:
    """Read .env into environment variables. Real keys live only in .env (git-ignored)."""
    try:
        from dotenv import load_dotenv
    except ImportError:  # dotenv not installed: rely on real environment variables
        return
    load_dotenv(ROOT / ".env")


def get_secret(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value or value.startswith("your-"):
        raise MissingSecret(
            f"{name} is not set. Copy .env.example to .env and fill in {name}."
        )
    return value


class MissingTool(Exception):
    """A required program (e.g. FFmpeg) could not be found."""


def find_tool(name: str) -> str:
    """Locate ffmpeg / ffprobe. Order: <NAME>_PATH env var, PATH, then winget's install folders
    (a terminal opened before `winget install` has a stale PATH - see FAILURES.md F-05)."""
    import shutil

    override = os.environ.get(f"{name.upper()}_PATH", "").strip()
    if override:
        if Path(override).is_file():
            return override
        raise MissingTool(f"{name.upper()}_PATH points to {override}, which does not exist")
    found = shutil.which(name)
    if found:
        return found
    local = os.environ.get("LOCALAPPDATA")
    if local:
        winget = Path(local) / "Microsoft" / "WinGet"
        candidates = [winget / "Links" / f"{name}.exe",
                      *sorted((winget / "Packages").glob(f"*FFmpeg*/*/bin/{name}.exe"))]
        for c in candidates:
            if c.is_file():
                return str(c)
    raise MissingTool(
        f"{name} not found. Install FFmpeg (Windows: winget install --id Gyan.FFmpeg -e), "
        f"open a NEW terminal, or set {name.upper()}_PATH in .env."
    )


def output_dir(stage: str, base: Path | None = None) -> Path:
    """Folder for one stage's outputs, created if needed."""
    folder = (base or OUTPUTS) / stage
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def rel(path: Path) -> str:
    """Path relative to the repo, with forward slashes, for logs (works on every OS)."""
    path = Path(path).resolve()
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()
