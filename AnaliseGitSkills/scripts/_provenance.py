#!/usr/bin/env python3

"""Small provenance helpers shared by the reproducibility scripts."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


def sha256_file(path: Path, chunk_size: int = 16 * 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def file_record(path: Path, *, include_hash: bool = True) -> dict[str, Any]:
    resolved = path.resolve()
    stat = resolved.stat()
    record: dict[str, Any] = {
        "path": str(resolved),
        "size_bytes": stat.st_size,
        "mtime_ns": stat.st_mtime_ns,
    }
    if include_hash:
        record["sha256"] = sha256_file(resolved)
    return record


def git_commit(worktree: Path) -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=worktree,
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return result.stdout.strip()


def base_manifest(script: Path, arguments: dict[str, Any]) -> dict[str, Any]:
    root = script.resolve().parents[2]
    return {
        "manifest_version": 1,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "script": file_record(script),
        "git_commit": git_commit(root),
        "arguments": arguments,
        "environment": {
            "python": sys.version,
            "platform": platform.platform(),
        },
    }


def ensure_new_outputs(paths: Iterable[Path], overwrite: bool) -> None:
    existing = [path for path in paths if path.exists()]
    if existing and not overwrite:
        joined = ", ".join(str(path) for path in existing)
        raise FileExistsError(
            "Saída(s) já existe(m); use outro diretório. "
            f"Nenhum arquivo foi sobrescrito: {joined}"
        )


def atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    with temporary.open("w", encoding="utf-8") as output:
        json.dump(payload, output, ensure_ascii=False, indent=2, sort_keys=True)
        output.write("\n")
        output.flush()
        os.fsync(output.fileno())
    temporary.replace(path)

