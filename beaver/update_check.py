"""Update checking for CONVERTOR-APP (v0.5.1).

Stdlib + git subprocess only, no new dependency, no network
library of its own. Everything is best-effort: a missing git
repository, no internet, a timeout, or any git error returns
an offline/error status — never an exception — so the app can
never fail to start because of an update check.

How it works: the app is run from a git clone, so "is there an
update?" means "does origin/main point somewhere other than
my local HEAD?". A short-timeout ``git fetch origin`` refreshes
the remote refs, then local HEAD and origin/main are compared.
Updating is a plain ``git pull origin main``; the app does NOT
restart itself — after a successful pull it tells the user to
restart, because on Windows the running .py files may be locked.

Display rule (v0.5.1): commit SHAs are used ONLY internally
for the up-to-date/available comparison. Every user-visible
string shows version numbers (parsed from ``beaver/__init__.py``,
locally and from ``origin/main``) and never a SHA. If the
remote version cannot be parsed, the wording falls back to
"novšia verzia" with no SHA and no version number.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

_VERSION_RE = re.compile(r"\bv(\d+(?:\.\d+){1,2})\b")


def parse_version(text: str) -> str | None:
    """Parse a version like ``v0.5.1`` out of file text, or None."""
    if not text:
        return None
    match = _VERSION_RE.search(text)
    return f"v{match.group(1)}" if match else None


def local_version() -> str | None:
    """Version string of this build, from beaver/__init__.py."""
    try:
        return parse_version(
            (Path(__file__).resolve().parent / "__init__.py").read_text(
                encoding="utf-8"
            )
        )
    except OSError:
        return None

FETCH_TIMEOUT = 10
PULL_TIMEOUT = 60


def find_repo_dir(start: Path | None = None) -> Path | None:
    """Walk up from ``start`` (or the app folder) looking for .git."""
    candidates = []
    if start is not None:
        candidates.append(Path(start))
    candidates.append(Path.cwd())
    # App root: parent of the beaver package directory.
    candidates.append(Path(__file__).resolve().parent.parent)
    seen: set[Path] = set()
    for candidate in candidates:
        current = candidate.resolve() if candidate.exists() else candidate
        while current not in seen:
            seen.add(current)
            if (current / ".git").exists():
                return current
            if current.parent == current:
                break
            current = current.parent
    return None


def _git(repo: Path, args: list[str], timeout: int) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(repo)] + args,
        capture_output=True, text=True, timeout=timeout,
    )


def check_update(repo_dir: Path | None = None, timeout: int = FETCH_TIMEOUT) -> dict:
    """Check for an update. Never raises; see module docstring."""
    repo = Path(repo_dir) if repo_dir is not None else find_repo_dir()
    if repo is None or not (repo / ".git").exists():
        return {
            "status": "offline",
            "is_repo": False,
            "local": "",
            "remote": "",
            "local_version": local_version(),
            "remote_version": None,
            "message": "Nie je git repozitár — kontrola aktualizácie nie je možná.",
        }
    try:
        local = _git(repo, ["rev-parse", "HEAD"], timeout).stdout.strip()
        if not local:
            raise ValueError("no local HEAD")
        fetch = _git(repo, ["fetch", "origin"], timeout)
        remote = ""
        for ref in ("origin/main", "origin/HEAD"):
            result = _git(repo, ["rev-parse", ref], timeout)
            if result.returncode == 0 and result.stdout.strip():
                remote = result.stdout.strip()
                break
        if not remote:
            return {
                "status": "offline",
                "is_repo": True,
                "local": local,
                "remote": "",
                "local_version": local_version(),
                "remote_version": None,
                "message": "Kontrola sa nepodarila (offline alebo chyba git fetch).",
            }
        # Remote version for display only; SHAs stay internal.
        # A parse failure is not an error: the GUI falls back to
        # "novšia verzia" with no SHA and no version number.
        remote_version = None
        try:
            shown = _git(
                repo, ["show", "origin/main:beaver/__init__.py"], timeout
            )
            if shown.returncode == 0:
                remote_version = parse_version(shown.stdout)
        except Exception:
            remote_version = None
        if local == remote:
            return {
                "status": "up_to_date",
                "is_repo": True,
                "local": local,
                "remote": remote,
                "local_version": local_version(),
                "remote_version": remote_version,
                "message": "Máš najnovšiu verziu.",
            }
        return {
            "status": "available",
            "is_repo": True,
            "local": local,
            "remote": remote,
            "local_version": local_version(),
            "remote_version": remote_version,
            "message": "K dispozícii je aktualizácia.",
        }
    except Exception as exc:  # timeout, missing git, anything else
        return {
            "status": "offline",
            "is_repo": (repo / ".git").exists(),
            "local": "",
            "remote": "",
            "local_version": local_version(),
            "remote_version": None,
            "message": f"Kontrola sa nepodarila: {exc.__class__.__name__} (offline?).",
        }


def run_update(repo_dir: Path | None = None, timeout: int = PULL_TIMEOUT) -> dict:
    """Run ``git pull origin main``. Never raises."""
    repo = Path(repo_dir) if repo_dir is not None else find_repo_dir()
    if repo is None or not (repo / ".git").exists():
        return {"success": False, "message": "Nie je git repozitár."}
    try:
        result = _git(repo, ["pull", "origin", "main"], timeout)
        output = (result.stdout + "\n" + result.stderr).strip()
        if result.returncode == 0:
            return {
                "success": True,
                "message": "Aktualizované. Reštartuj appku, aby sa nová verzia načítala.",
                "output": output,
            }
        return {"success": False, "message": "Aktualizácia zlyhala.", "output": output}
    except Exception as exc:
        return {"success": False, "message": f"Aktualizácia zlyhala: {exc}"}
