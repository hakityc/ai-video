"""Centralized path configuration for AI Video Control Plane.

All business directory paths are defined here.
Override ``AIVIDEO_DATA_DIR`` to decouple the data directory from the
repository root (useful for production deployments or large dataset mounts).
"""
from __future__ import annotations

import os
from pathlib import Path


def _resolve_env(name: str) -> Path | None:
    raw = os.getenv(name, "").strip()
    return Path(raw).resolve() if raw else None


# Root of the repository (where pyproject.toml lives).
# Can be overridden via AIVIDEO_REPO_ROOT for edge-case deployments.
REPO_ROOT: Path = _resolve_env("AIVIDEO_REPO_ROOT") or Path.cwd().resolve()

# Root of the data directory.  Defaults to REPO_ROOT so existing
# on-disk layouts need no changes.  Set AIVIDEO_DATA_DIR to a different
# path to store data outside the source tree.
DATA_ROOT: Path = _resolve_env("AIVIDEO_DATA_DIR") or REPO_ROOT

# ---------------------------------------------------------------------------
# Content / template directories (read-mostly)
# ---------------------------------------------------------------------------

CHARACTERS_DIR: Path = DATA_ROOT / "examples" / "characters"
SCENES_DIR: Path = DATA_ROOT / "examples" / "scenes"
PROPS_DIR: Path = DATA_ROOT / "examples" / "props"
SHOT_TEMPLATES_DIR: Path = DATA_ROOT / "examples" / "shot-templates"
EPISODES_DIR: Path = DATA_ROOT / "examples" / "episodes"
JOBS_DIR: Path = DATA_ROOT / "examples" / "jobs"
WORKFLOWS_DIR: Path = DATA_ROOT / "examples" / "workflows"

# ---------------------------------------------------------------------------
# Document / script directories
# ---------------------------------------------------------------------------

STORIES_DIR: Path = DATA_ROOT / "docs" / "stories"
EPISODE_NOTES_DIR: Path = DATA_ROOT / "docs" / "episodes"

# ---------------------------------------------------------------------------
# Static asset directories
# ---------------------------------------------------------------------------

ASSETS_CHARACTERS_DIR: Path = DATA_ROOT / "assets" / "characters"

# ---------------------------------------------------------------------------
# Runtime artifact directories (write-heavy; excluded from git)
# ---------------------------------------------------------------------------

ARTIFACTS_DIR: Path = DATA_ROOT / "artifacts"
ARTIFACTS_VIDEO_DIR: Path = ARTIFACTS_DIR / "video"
ARTIFACTS_OUTPUT_DIR: Path = ARTIFACTS_DIR / "output"
ARTIFACTS_BRIDGE_FRAMES_DIR: Path = ARTIFACTS_DIR / "bridge-frames"

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

DB_DIR: Path = ARTIFACTS_DIR / "web"
DB_PATH: Path = DB_DIR / "control-plane.db"
