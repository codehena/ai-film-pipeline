"""Guard rails so real keys never end up in the repository."""
import re

from pipeline.common import config

SKIP_DIRS = {".git", ".venv", "outputs", "cache", "__pycache__", ".pytest_cache"}
TEXT_SUFFIXES = {".py", ".json", ".jsonl", ".md", ".toml", ".txt", ".example", ".ipynb", ""}

# Shapes of real keys: Google API keys, Kaggle keys (32 hex), long Cloudflare-style tokens
KEY_PATTERNS = [
    re.compile(r"AIza[0-9A-Za-z_\-]{35}"),
    re.compile(r"KAGGLE_KEY\s*=\s*[0-9a-f]{32}"),
    re.compile(r"CLOUDFLARE_API_TOKEN\s*=\s*[A-Za-z0-9_\-]{30,}"),
]


def test_gitignore_protects_secrets_and_outputs():
    lines = {line.strip() for line in (config.ROOT / ".gitignore").read_text().splitlines()}
    for required in (".env", ".venv/", "__pycache__/", "cache/", "outputs/"):
        assert required in lines, f"{required} missing from .gitignore"


def test_env_example_has_placeholders_only():
    for line in (config.ROOT / ".env.example").read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        name, _, value = line.partition("=")
        assert value.startswith("your-"), f"{name} in .env.example must be a placeholder"


def test_no_real_keys_in_repository_files():
    for path in config.ROOT.rglob("*"):
        if any(part in SKIP_DIRS for part in path.parts) or not path.is_file():
            continue
        if path.name == ".env" or path.suffix not in TEXT_SUFFIXES:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pattern in KEY_PATTERNS:
            assert not pattern.search(text), f"possible secret in {path.relative_to(config.ROOT)}"
