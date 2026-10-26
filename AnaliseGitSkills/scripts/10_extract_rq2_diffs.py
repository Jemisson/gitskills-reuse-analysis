#!/usr/bin/env python3

"""Extract parent-child Git diffs from a recovered RQ2 history pilot."""

from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import os
from pathlib import Path

import pandas as pd

from _provenance import atomic_json, base_manifest, ensure_new_outputs, file_record


collector = importlib.import_module("09_collect_rq2_histories")
ROOT = Path(__file__).resolve().parents[1]
DEFAULT_HISTORY_DIR = ROOT / "outputs" / "rq2" / "history_pilot_v2"
DEFAULT_CACHE = ROOT / "outputs" / "rq2" / "history_pilot" / "git_cache"
DEFAULT_OUTPUT_DIR = ROOT / "outputs" / "rq2" / "diff_pilot_v2"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--history-dir", default=str(DEFAULT_HISTORY_DIR))
    parser.add_argument(
        "--summary",
        default=None,
        help="Resumo filtrado opcional; por padrão usa <history-dir>/history_recovery_summary.csv.",
    )
    parser.add_argument("--cache-root", default=str(DEFAULT_CACHE))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--git-timeout-seconds", type=float, default=60.0)
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def parse_name_status(text: str) -> list[dict[str, str | None]]:
    changes = []
    for line in text.splitlines():
        fields = line.split("\t")
        if len(fields) == 2:
            changes.append(
                {"status": fields[0], "old_path": fields[1], "new_path": fields[1]}
            )
        elif len(fields) == 3 and fields[0].startswith(("R", "C")):
            changes.append(
                {"status": fields[0], "old_path": fields[1], "new_path": fields[2]}
            )
    return changes


def changes_for_commit(
    repository: Path,
    parent: str | None,
    commit: str,
    timeout_seconds: float,
) -> list[dict[str, str | None]]:
    if parent:
        arguments = [
            "diff",
            "-M",
            "--name-status",
            parent,
            commit,
            "--",
        ]
    else:
        arguments = [
            "diff-tree",
            "--root",
            "-r",
            "-M",
            "--no-commit-id",
            "--name-status",
            commit,
        ]
    result = collector.run_git(
        repository,
        arguments,
        timeout_seconds,
    )
    return parse_name_status(result.stdout) if result.returncode == 0 else []


def blob_at(
    repository: Path, commit: str, path: str, timeout_seconds: float
) -> str | None:
    result = collector.run_git(
        repository,
        ["rev-parse", "--verify", f"{commit}:{collector.safe_git_path(path)}"],
        timeout_seconds,
    )
    return result.stdout.strip() if result.returncode == 0 else None


def select_change(
    changes: list[dict[str, str | None]], tracked_path: str
) -> tuple[dict[str, str | None] | None, bool]:
    matching = [
        item
        for item in changes
        if tracked_path in {item["old_path"], item["new_path"]}
    ]
    if len(matching) == 1:
        return matching[0], False
    if len(matching) > 1:
        return matching[0], True
    skill_changes = [
        item
        for item in changes
        if str(item["old_path"]).endswith("SKILL.md")
        or str(item["new_path"]).endswith("SKILL.md")
    ]
    if len(skill_changes) == 1:
        return skill_changes[0], True
    return None, bool(skill_changes)


def diff_text(
    repository: Path,
    parent: str | None,
    commit: str,
    paths: list[str],
    timeout_seconds: float,
) -> str:
    safe_paths = sorted({collector.safe_git_path(path) for path in paths if path})
    if parent:
        arguments = [
            "diff",
            "--no-ext-diff",
            "--no-color",
            "--unified=3",
            parent,
            commit,
            "--",
            *safe_paths,
        ]
    else:
        arguments = [
            "show",
            "--format=",
            "--no-ext-diff",
            "--no-color",
            "--unified=3",
            commit,
            "--",
            *safe_paths,
        ]
    result = collector.run_git(repository, arguments, timeout_seconds)
    return result.stdout if result.returncode == 0 else ""


def line_counts(diff: str) -> tuple[int, int]:
    added = sum(
        line.startswith("+") and not line.startswith("+++")
        for line in diff.splitlines()
    )
    deleted = sum(
        line.startswith("-") and not line.startswith("---")
        for line in diff.splitlines()
    )
    return int(added), int(deleted)


def classify_unselected_comparison(
    old_blob: str | None, new_blob: str | None
) -> tuple[str, str]:
    if old_blob is not None and old_blob == new_blob:
        return "UNCHANGED", "unchanged_context"
    if old_blob is None and new_blob is None:
        return "PATH_ABSENT", "path_absent_context"
    return "UNRESOLVED", "unresolved"


def main() -> None:
    args = parse_args()
    if args.git_timeout_seconds <= 0:
        raise ValueError("--git-timeout-seconds deve ser positivo")
    history_dir = Path(args.history_dir).expanduser().resolve()
    cache_root = Path(args.cache_root).expanduser().resolve()
    output_dir = Path(args.output_dir).expanduser().resolve()
    diffs_dir = output_dir / "diffs"
    events_path = output_dir / "diff_events.csv"
    manifest_path = output_dir / "diff_manifest.json"
    summary_path = (
        Path(args.summary).expanduser().resolve()
        if args.summary
        else history_dir / "history_recovery_summary.csv"
    )
    if not summary_path.is_file() or not cache_root.is_dir():
        raise FileNotFoundError("Resumo de história ou cache Git não encontrado")
    output_dir.mkdir(parents=True, exist_ok=True)
    diffs_dir.mkdir(parents=True, exist_ok=True)
    ensure_new_outputs([events_path, manifest_path], args.overwrite)

    occurrences = pd.read_csv(summary_path)
    rows = []
    unresolved_comparisons = 0
    unchanged_comparisons = 0
    path_absent_comparisons = 0
    ambiguous_events = 0
    for _, occurrence in occurrences.iterrows():
        repository_name = str(occurrence["repo_full_name"])
        repository = cache_root / collector.cache_name(repository_name)
        history_path = history_dir / str(occurrence["history_jsonl"])
        history = [
            json.loads(line)
            for line in history_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        tracked_path = str(occurrence["path"])
        for event in history:
            commit = str(event["commit"])
            parents = list(event.get("parents", [])) or [None]
            rename_predecessors: set[str] = set()
            for parent_index, parent in enumerate(parents):
                changes = changes_for_commit(
                    repository, parent, commit, args.git_timeout_seconds
                )
                selected, ambiguous = select_change(changes, tracked_path)
                if selected is not None:
                    ambiguous_events += int(ambiguous)
                    old_path = str(selected["old_path"])
                    new_path = str(selected["new_path"])
                    status = str(selected["status"])
                    comparison_class = "change_event"
                    old_blob = (
                        blob_at(repository, parent, old_path, args.git_timeout_seconds)
                        if parent
                        else None
                    )
                    new_blob = blob_at(
                        repository, commit, new_path, args.git_timeout_seconds
                    )
                else:
                    old_path = tracked_path
                    new_path = tracked_path
                    old_blob = (
                        blob_at(repository, parent, old_path, args.git_timeout_seconds)
                        if parent
                        else None
                    )
                    new_blob = blob_at(
                        repository, commit, new_path, args.git_timeout_seconds
                    )
                    status, comparison_class = classify_unselected_comparison(
                        old_blob, new_blob
                    )
                    unresolved_comparisons += int(comparison_class == "unresolved")
                    unchanged_comparisons += int(
                        comparison_class == "unchanged_context"
                    )
                    path_absent_comparisons += int(
                        comparison_class == "path_absent_context"
                    )
                raw_diff = diff_text(
                    repository,
                    parent,
                    commit,
                    [old_path, new_path],
                    args.git_timeout_seconds,
                )
                diff_sha = hashlib.sha256(raw_diff.encode()).hexdigest()
                diff_id = hashlib.sha256(
                    f"{occurrence['occurrence_id']}\0{commit}\0{parent or 'ROOT'}".encode()
                ).hexdigest()
                raw_path = diffs_dir / f"{diff_id}.diff"
                raw_path.write_text(raw_diff, encoding="utf-8")
                added, deleted = line_counts(raw_diff)
                rows.append(
                    {
                        "diff_id": diff_id,
                        "occurrence_id": occurrence["occurrence_id"],
                        "repo_full_name": repository_name,
                        "commit": commit,
                        "parent": parent,
                        "parent_index": parent_index,
                        "is_merge": len(event.get("parents", [])) > 1,
                        "status": status,
                        "comparison_class": comparison_class,
                        "is_change_event": comparison_class == "change_event",
                        "old_path": old_path,
                        "new_path": new_path,
                        "old_blob_sha": old_blob,
                        "new_blob_sha": new_blob,
                        "added_lines": added,
                        "deleted_lines": deleted,
                        "diff_sha256": diff_sha,
                        "raw_diff_file": f"diffs/{raw_path.name}",
                        "path_selection_ambiguous": ambiguous,
                    }
                )
                if (
                    selected is not None
                    and status.startswith(("R", "C"))
                    and new_path == tracked_path
                ):
                    rename_predecessors.add(old_path)
            if len(rename_predecessors) == 1:
                tracked_path = rename_predecessors.pop()

    events = pd.DataFrame(rows)
    events.to_csv(events_path, index=False)
    manifest = base_manifest(Path(__file__), vars(args))
    manifest["input"] = file_record(summary_path)
    manifest["results"] = {
        "occurrences": len(occurrences),
        "parent_comparisons": len(events),
        "change_event_rows": int(events["is_change_event"].sum()) if len(events) else 0,
        "unique_commits": int(events["commit"].nunique()) if len(events) else 0,
        "merge_parent_comparisons": int(events["is_merge"].sum()) if len(events) else 0,
        "unchanged_context_comparisons": unchanged_comparisons,
        "path_absent_context_comparisons": path_absent_comparisons,
        "unresolved_comparisons": unresolved_comparisons,
        "ambiguous_path_events": ambiguous_events,
    }
    manifest["limitations"] = [
        "Path reconstruction is conservative and unresolved events are retained as counts.",
        "Full-history traversal context is retained separately from actual path changes.",
        "A diff is intrarepository evidence only and does not establish cross-repository ancestry.",
        "Raw diffs are local regeneration artifacts and are not tracked by Git.",
    ]
    manifest["outputs"] = [file_record(events_path)]
    atomic_json(manifest_path, manifest)
    print(manifest["results"])
    print(f"Manifesto: {manifest_path}")


if __name__ == "__main__":
    main()
