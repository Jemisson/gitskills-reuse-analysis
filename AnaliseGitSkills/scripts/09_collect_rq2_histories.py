#!/usr/bin/env python3

"""Collect Git history for a small, explicitly selected RQ2 pilot subset."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import time
from pathlib import Path, PurePosixPath

import pandas as pd

from _provenance import atomic_json, base_manifest, ensure_new_outputs, file_record


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "outputs" / "rq2" / "pilot" / "pilot_occurrences.csv"
DEFAULT_OUTPUT_DIR = ROOT / "outputs" / "rq2" / "history_pilot"
REPOSITORY_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
HEX_SHA_RE = re.compile(r"^[0-9a-f]{40}$")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default=str(DEFAULT_INPUT))
    parser.add_argument(
        "--probe-file",
        action="append",
        required=True,
        help="Pode ser repetido; somente repositórios acessíveis em todos entram.",
    )
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument(
        "--cache-root",
        default=None,
        help="Cache Git compartilhado; por padrão usa <output-dir>/git_cache.",
    )
    parser.add_argument("--limit-repositories", type=int, default=3)
    parser.add_argument("--clone-timeout-seconds", type=float, default=180.0)
    parser.add_argument("--git-timeout-seconds", type=float, default=60.0)
    parser.add_argument("--max-cache-bytes", type=int, default=1_000_000_000)
    parser.add_argument("--max-total-cache-bytes", type=int, default=2_000_000_000)
    parser.add_argument("--max-elapsed-seconds", type=float, default=1800.0)
    parser.add_argument("--overwrite-summary", action="store_true")
    return parser.parse_args()


def safe_repository(repository: str) -> str:
    if not REPOSITORY_RE.fullmatch(repository):
        raise ValueError(f"Nome de repositório inválido: {repository!r}")
    return repository


def safe_git_path(value: str) -> str:
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or not path.parts:
        raise ValueError(f"Path Git inválido: {value!r}")
    return path.as_posix()


def run_git(
    repository: Path,
    arguments: list[str],
    timeout_seconds: float,
    check: bool = False,
) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["GIT_TERMINAL_PROMPT"] = "0"
    result = subprocess.run(
        ["git", "-C", str(repository), *arguments],
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
        env=environment,
        check=False,
    )
    if check and result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip())
    return result


def directory_size(path: Path) -> int:
    return sum(item.stat().st_size for item in path.rglob("*") if item.is_file())


def cache_name(repository: str) -> str:
    safe_repository(repository)
    digest = hashlib.sha256(repository.encode()).hexdigest()[:12]
    return f"{repository.replace('/', '__')}__{digest}.git"


def ensure_bare_clone(
    repository: str,
    cache_root: Path,
    timeout_seconds: float,
) -> tuple[Path, str]:
    target = cache_root / cache_name(repository)
    if target.exists():
        probe = run_git(target, ["rev-parse", "--is-bare-repository"], 15)
        if probe.returncode == 0 and probe.stdout.strip() == "true":
            return target, "cache"
        raise ValueError(f"Cache existente não é repositório bare válido: {target}")

    temporary = target.with_name(f".{target.name}.{os.getpid()}.partial")
    if temporary.exists():
        raise FileExistsError(
            f"Clone parcial anterior existe e exige inspeção manual: {temporary}"
        )
    url = f"https://github.com/{safe_repository(repository)}.git"
    environment = os.environ.copy()
    environment["GIT_TERMINAL_PROMPT"] = "0"
    result = subprocess.run(
        [
            "git",
            "clone",
            "--bare",
            "--filter=blob:none",
            "--no-tags",
            url,
            str(temporary),
        ],
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
        env=environment,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "git clone falhou")
    temporary.replace(target)
    return target, "network"


def history_for_path(
    repository: Path,
    path: str,
    timeout_seconds: float,
) -> list[dict[str, object]]:
    safe_path = safe_git_path(path)
    separator = "\x1f"
    format_argument = f"--format=%H%x1f%P%x1f%aI%x1f%cI"
    commands = {
        "follow_rename": ["log", "--follow", format_argument, "--", safe_path],
        "full_history_merges": [
            "log",
            "--full-history",
            format_argument,
            "--",
            safe_path,
        ],
    }
    by_commit: dict[str, dict[str, object]] = {}
    for evidence_mode, arguments in commands.items():
        result = run_git(repository, arguments, timeout_seconds)
        if result.returncode != 0:
            continue
        for line in result.stdout.splitlines():
            fields = line.split(separator)
            if len(fields) != 4:
                continue
            commit, parents, author_at, committed_at = fields
            if commit not in by_commit:
                by_commit[commit] = {
                    "commit": commit,
                    "parents": parents.split() if parents else [],
                    "author_at": author_at,
                    "committed_at": committed_at,
                    "evidence_modes": [],
                }
            by_commit[commit]["evidence_modes"].append(evidence_mode)
    return sorted(
        by_commit.values(),
        key=lambda item: (str(item["committed_at"]), str(item["commit"])),
        reverse=True,
    )


def inspect_occurrence(
    repository: Path,
    row: pd.Series,
    histories_dir: Path,
    timeout_seconds: float,
) -> dict[str, object]:
    repo_name = safe_repository(str(row["repo_full_name"]))
    path = safe_git_path(str(row["path"]))
    anchor_sha = str(row["anchor_file_sha"])
    if not HEX_SHA_RE.fullmatch(anchor_sha):
        raise ValueError(f"SHA inválido: {anchor_sha!r}")

    occurrence_id = hashlib.sha256(
        f"{repo_name}\0{path}\0{anchor_sha}".encode()
    ).hexdigest()
    history = history_for_path(repository, path, timeout_seconds)
    history_path = histories_dir / f"{occurrence_id}.jsonl"
    temporary = history_path.with_name(f".{history_path.name}.{os.getpid()}.tmp")
    with temporary.open("w", encoding="utf-8") as output:
        for event in history:
            output.write(json.dumps(event, sort_keys=True) + "\n")
    temporary.replace(history_path)

    blob = run_git(
        repository, ["cat-file", "-e", f"{anchor_sha}^{{blob}}"], timeout_seconds
    )
    head_path = run_git(
        repository, ["rev-parse", "--verify", f"HEAD:{path}"], timeout_seconds
    )
    head_blob = head_path.stdout.strip() if head_path.returncode == 0 else None
    if head_blob == anchor_sha:
        head_path_status = "matches_anchor"
    elif head_blob:
        head_path_status = "different_blob"
    else:
        head_path_status = "missing"

    return {
        "occurrence_id": occurrence_id,
        "anchor_file_sha": anchor_sha,
        "repo_full_name": repo_name,
        "path": path,
        "anchor_blob_available": blob.returncode == 0,
        "head_path_status": head_path_status,
        "head_blob_sha": head_blob,
        "history_commit_count": len(history),
        "newest_history_commit": history[0]["commit"] if history else None,
        "oldest_history_commit": history[-1]["commit"] if history else None,
        "history_jsonl": f"histories/{history_path.name}",
    }


def accessible_in_all(probe_files: list[Path]) -> set[str]:
    sets = []
    for path in probe_files:
        probe = pd.read_csv(path, usecols=["repo_full_name", "status"])
        sets.append(set(probe.loc[probe["status"] == "accessible", "repo_full_name"]))
    return set.intersection(*sets) if sets else set()


def main() -> None:
    args = parse_args()
    if (
        args.limit_repositories < 1
        or args.clone_timeout_seconds <= 0
        or args.git_timeout_seconds <= 0
        or args.max_cache_bytes < 1
        or args.max_total_cache_bytes < 1
        or args.max_elapsed_seconds <= 0
    ):
        raise ValueError("Limites devem ser positivos")
    input_path = Path(args.input).expanduser().resolve()
    probe_paths = [Path(item).expanduser().resolve() for item in args.probe_file]
    output_dir = Path(args.output_dir).expanduser().resolve()
    cache_root = (
        Path(args.cache_root).expanduser().resolve()
        if args.cache_root
        else output_dir / "git_cache"
    )
    histories_dir = output_dir / "histories"
    summary_path = output_dir / "history_recovery_summary.csv"
    repo_status_path = output_dir / "repository_collection_status.csv"
    manifest_path = output_dir / "history_recovery_manifest.json"
    if not input_path.is_file() or any(not path.is_file() for path in probe_paths):
        raise FileNotFoundError("Entrada ou probe não encontrado")
    output_dir.mkdir(parents=True, exist_ok=True)
    cache_root.mkdir(parents=True, exist_ok=True)
    histories_dir.mkdir(parents=True, exist_ok=True)
    ensure_new_outputs(
        [summary_path, repo_status_path, manifest_path],
        overwrite=args.overwrite_summary,
    )

    occurrences = pd.read_csv(input_path)
    stable_accessible = accessible_in_all(probe_paths)
    candidates = sorted(
        set(occurrences["repo_full_name"]).intersection(stable_accessible)
    )[: args.limit_repositories]
    selected = occurrences.loc[
        occurrences["repo_full_name"].isin(candidates)
    ].copy()

    rows = []
    repository_status = []
    started = time.monotonic()
    stopped_by_budget = None
    for candidate_index, repository_name in enumerate(candidates):
        elapsed_seconds = time.monotonic() - started
        total_cache_bytes = directory_size(cache_root)
        if elapsed_seconds >= args.max_elapsed_seconds:
            stopped_by_budget = "elapsed_time"
        elif total_cache_bytes >= args.max_total_cache_bytes:
            stopped_by_budget = "total_cache_size"
        if stopped_by_budget:
            for unattempted in candidates[candidate_index:]:
                repository_status.append(
                    {
                        "repo_full_name": unattempted,
                        "status": f"not_attempted_{stopped_by_budget}_budget",
                        "source": None,
                        "cache_size_bytes": None,
                        "error": None,
                    }
                )
            break
        repository_rows = selected.loc[
            selected["repo_full_name"] == repository_name
        ]
        try:
            repository, source = ensure_bare_clone(
                repository_name, cache_root, args.clone_timeout_seconds
            )
            size_bytes = directory_size(repository)
            if size_bytes > args.max_cache_bytes:
                repository_status.append(
                    {
                        "repo_full_name": repository_name,
                        "status": "cache_size_limit_exceeded",
                        "source": source,
                        "cache_size_bytes": size_bytes,
                        "error": None,
                    }
                )
                continue
            for _, occurrence in repository_rows.iterrows():
                rows.append(
                    inspect_occurrence(
                        repository,
                        occurrence,
                        histories_dir,
                        args.git_timeout_seconds,
                    )
                )
            final_size_bytes = directory_size(repository)
            total_cache_bytes = directory_size(cache_root)
            repository_status.append(
                {
                    "repo_full_name": repository_name,
                    "status": (
                        "collected"
                        if final_size_bytes <= args.max_cache_bytes
                        else "collected_cache_size_limit_exceeded"
                    ),
                    "source": source,
                    "cache_size_bytes": final_size_bytes,
                    "error": None,
                }
            )
            if total_cache_bytes >= args.max_total_cache_bytes:
                stopped_by_budget = "total_cache_size"
        except (OSError, RuntimeError, ValueError, subprocess.TimeoutExpired) as error:
            repository_status.append(
                {
                    "repo_full_name": repository_name,
                    "status": "collection_failed",
                    "source": None,
                    "cache_size_bytes": None,
                    "error": str(error)[:2000],
                }
            )

    summary = pd.DataFrame(rows)
    summary.to_csv(summary_path, index=False)
    pd.DataFrame(repository_status).to_csv(repo_status_path, index=False)

    manifest = base_manifest(Path(__file__), vars(args))
    manifest["inputs"] = [file_record(input_path)] + [
        file_record(path) for path in probe_paths
    ]
    manifest["selection"] = {
        "rule": (
            "preselected input filtered to repositories accessible in every supplied "
            "probe; sorted repository name defines execution order"
            if "selection_stratum" in occurrences.columns
            else "accessible in every supplied probe, sorted repository name"
        ),
        "stable_accessible_repositories": len(stable_accessible),
        "selected_repositories": candidates,
        "selected_occurrences": len(selected),
        "limit_repositories": args.limit_repositories,
    }
    if "selection_stratum" in occurrences.columns:
        manifest["selection"]["input_selection_strata"] = {
            str(key): int(value)
            for key, value in occurrences[["repo_full_name", "selection_stratum"]]
            .drop_duplicates()
            .groupby("selection_stratum")
            .size()
            .sort_index()
            .items()
        }
    manifest["results"] = {
        "repository_status_counts": {
            str(key): int(value)
            for key, value in pd.DataFrame(repository_status)["status"]
            .value_counts()
            .sort_index()
            .items()
        },
        "occurrences_with_history": int(
            (summary.get("history_commit_count", pd.Series(dtype=int)) > 0).sum()
        ),
        "occurrences_processed": len(summary),
        "stopped_by_budget": stopped_by_budget,
        "final_total_cache_bytes": directory_size(cache_root),
    }
    manifest["limitations"] = [
        "The pilot uses repositories accessible in two rapid anonymous probes and is not representative.",
        "git log --follow is path-oriented and has known limitations across merges.",
        "Current HEAD can differ from the July 2026 dataset snapshot.",
        "A locally available blob does not establish cross-repository ancestry.",
    ]
    manifest["outputs"] = [file_record(summary_path), file_record(repo_status_path)]
    manifest["elapsed_seconds"] = time.monotonic() - started
    atomic_json(manifest_path, manifest)
    print(manifest["selection"])
    print(manifest["results"])
    print(f"Manifesto: {manifest_path}")


if __name__ == "__main__":
    main()
