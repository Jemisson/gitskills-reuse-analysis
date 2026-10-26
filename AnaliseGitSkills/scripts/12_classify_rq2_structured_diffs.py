#!/usr/bin/env python3

"""Classify RQ2 parent-child changes with deterministic Markdown rules."""

from __future__ import annotations

import argparse
import difflib
import hashlib
import importlib
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from _provenance import atomic_json, base_manifest, ensure_new_outputs, file_record


collector = importlib.import_module("09_collect_rq2_histories")
ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = (
    ROOT / "outputs" / "rq2" / "diff_calibration_20261026_v2" / "diff_events.csv"
)
DEFAULT_CACHE = (
    ROOT / "outputs" / "rq2" / "history_calibration_20261026" / "git_cache"
)
DEFAULT_OUTPUT_DIR = ROOT / "outputs" / "rq2" / "structured_diff_calibration_v3"
CLASSIFIER_VERSION = "rq2-structured-diff-v1.0"
URL_RE = re.compile(r"\b(?:https?|ftp)://[^\s<>]+", re.IGNORECASE)
MARKDOWN_LINK_RE = re.compile(r"!?\[[^]]*\]\([^)]+\)")
INLINE_CODE_RE = re.compile(r"(?<!`)`[^`\n]+`(?!`)")
LIST_RE = re.compile(r"^\s*(?:[-+*]|\d+[.)])\s+")
HEADING_RE = re.compile(r"^\s{0,3}(#{1,6})\s+(.+?)\s*$")
FENCE_RE = re.compile(r"^\s*(`{3,}|~{3,})")
HUNK_RE = re.compile(r"^@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@")
TABLE_RE = re.compile(r"^\s*\|.*\|\s*$")
EXAMPLE_HEADING_RE = re.compile(
    r"\b(example|examples|usage|use case|exemplo|exemplos|uso)\b", re.IGNORECASE
)


@dataclass(frozen=True)
class LineInfo:
    line_number: int
    text: str
    structural_region: str
    heading_context: str | None
    semantic_candidates: tuple[str, ...]
    rule_ids: tuple[str, ...]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default=str(DEFAULT_INPUT))
    parser.add_argument("--cache-root", default=str(DEFAULT_CACHE))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--git-timeout-seconds", type=float, default=60.0)
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def markdown_lines(text: str) -> tuple[list[LineInfo], str]:
    lines = text.splitlines()
    frontmatter = bool(lines and lines[0].strip() == "---")
    frontmatter_closed = False
    in_fence = False
    fence_marker = ""
    heading_context: str | None = None
    parsed: list[LineInfo] = []
    for index, line in enumerate(lines, start=1):
        stripped = line.strip()
        rules: list[str] = []
        candidates: list[str] = []
        if frontmatter and not frontmatter_closed:
            region = "front_matter"
            rules.append("MD_FRONT_MATTER")
            if index > 1 and stripped == "---":
                frontmatter_closed = True
            elif ":" in line:
                key = line.split(":", 1)[0].strip().lower()
                if key == "name":
                    candidates.append("name")
                    rules.append("FM_NAME_KEY")
                elif key == "description":
                    candidates.append("description")
                    rules.append("FM_DESCRIPTION_KEY")
                else:
                    candidates.append("front_matter_other")
                    rules.append("FM_OTHER_KEY")
        else:
            fence = FENCE_RE.match(line)
            if fence:
                marker = fence.group(1)[0]
                if not in_fence:
                    in_fence = True
                    fence_marker = marker
                elif marker == fence_marker:
                    in_fence = False
                region = "code_fence"
                candidates.append("command_code_candidate")
                rules.extend(["MD_FENCE", "SCOPE_CODE"])
            elif in_fence:
                region = "code_block"
                candidates.append("command_code_candidate")
                rules.extend(["MD_FENCED_CONTENT", "SCOPE_CODE"])
            else:
                heading = HEADING_RE.match(line)
                if heading:
                    region = "heading"
                    heading_context = heading.group(2).strip()
                    rules.append("MD_HEADING")
                elif not stripped:
                    region = "blank"
                    rules.append("MD_BLANK")
                elif LIST_RE.match(line):
                    region = "list_item"
                    rules.append("MD_LIST")
                elif stripped.startswith(">"):
                    region = "blockquote"
                    rules.append("MD_BLOCKQUOTE")
                elif TABLE_RE.match(line):
                    region = "table"
                    rules.append("MD_TABLE")
                elif line.startswith(("    ", "\t")):
                    region = "indented_code"
                    candidates.append("command_code_candidate")
                    rules.extend(["MD_INDENTED_CODE", "SCOPE_CODE"])
                else:
                    region = "paragraph"
                    rules.append("MD_PARAGRAPH")
                if (
                    region not in {"blank", "code_block", "code_fence", "indented_code"}
                    and heading_context
                    and EXAMPLE_HEADING_RE.search(heading_context)
                ):
                    candidates.append("example_candidate")
                    rules.append("SCOPE_EXAMPLE_HEADING")
                elif region in {"paragraph", "list_item", "blockquote"}:
                    candidates.append("instruction_candidate")
                    rules.append("SCOPE_PROSE")
        if URL_RE.search(line):
            candidates.append("network_url_candidate")
            rules.append("TOKEN_URL_SCHEME")
        if MARKDOWN_LINK_RE.search(line):
            candidates.append("reference_candidate")
            rules.append("TOKEN_MARKDOWN_LINK")
        if INLINE_CODE_RE.search(line):
            candidates.append("command_code_candidate")
            rules.append("TOKEN_INLINE_CODE")
        parsed.append(
            LineInfo(
                line_number=index,
                text=line,
                structural_region=region,
                heading_context=heading_context,
                semantic_candidates=tuple(sorted(set(candidates))),
                rule_ids=tuple(sorted(set(rules))),
            )
        )
    if not frontmatter:
        status = "absent"
    elif frontmatter_closed:
        status = "closed"
    else:
        status = "unclosed"
    return parsed, status


def changed_lines(
    old_lines: list[LineInfo], new_lines: list[LineInfo]
) -> list[tuple[str, LineInfo]]:
    old_text = [line.text for line in old_lines]
    new_text = [line.text for line in new_lines]
    matcher = difflib.SequenceMatcher(a=old_text, b=new_text, autojunk=False)
    changes: list[tuple[str, LineInfo]] = []
    for tag, old_start, old_end, new_start, new_end in matcher.get_opcodes():
        if tag in {"replace", "delete"}:
            changes.extend(("deleted", line) for line in old_lines[old_start:old_end])
        if tag in {"replace", "insert"}:
            changes.extend(("added", line) for line in new_lines[new_start:new_end])
    return changes


def changed_lines_from_unified_diff(
    diff: str, old_lines: list[LineInfo], new_lines: list[LineInfo]
) -> list[tuple[str, LineInfo]]:
    changes: list[tuple[str, LineInfo]] = []
    old_position: int | None = None
    new_position: int | None = None
    for raw_line in diff.splitlines():
        hunk = HUNK_RE.match(raw_line)
        if hunk:
            old_position = int(hunk.group(1))
            new_position = int(hunk.group(2))
            continue
        if old_position is None or new_position is None:
            continue
        if raw_line.startswith("\\ No newline at end of file"):
            continue
        if raw_line.startswith("-"):
            if old_position < 1 or old_position > len(old_lines):
                raise ValueError("Linha removida fora do blob pai")
            changes.append(("deleted", old_lines[old_position - 1]))
            old_position += 1
        elif raw_line.startswith("+"):
            if new_position < 1 or new_position > len(new_lines):
                raise ValueError("Linha adicionada fora do blob filho")
            changes.append(("added", new_lines[new_position - 1]))
            new_position += 1
        elif raw_line.startswith(" "):
            old_position += 1
            new_position += 1
    return changes


def normalized_text(text: str) -> str:
    return " ".join(text.split())


def change_operation(status: str, old_text: str, new_text: str) -> str:
    if status.startswith(("R", "C")) and old_text == new_text:
        return "movement"
    if old_text != new_text and normalized_text(old_text) == normalized_text(new_text):
        return "formatting"
    if status == "A":
        return "addition"
    if status == "D":
        return "removal"
    if status.startswith(("R", "C")):
        return "multiple"
    return "modification"


def optional_sha(value: object) -> str | None:
    if pd.isna(value):
        return None
    text = str(value).strip()
    return text or None


def read_blob(repository: Path, sha: str | None, timeout_seconds: float) -> str:
    if sha is None:
        return ""
    result = collector.run_git(repository, ["cat-file", "blob", sha], timeout_seconds)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"blob indisponível: {sha}")
    return result.stdout


def atomic_csv(frame: pd.DataFrame, path: Path) -> None:
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        frame.to_csv(temporary, index=False)
        temporary.replace(path)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise


def category_counts(events: pd.DataFrame, evidence: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for operation, group in events.groupby("change_operation", sort=True):
        rows.append(
            {
                "dimension": "change_operation",
                "direction": "not_applicable",
                "category": operation,
                "line_count": pd.NA,
                "event_count": group["diff_id"].nunique(),
            }
        )
    for (direction, region), group in evidence.groupby(
        ["direction", "structural_region"], sort=True
    ):
        rows.append(
            {
                "dimension": "structural_region",
                "direction": direction,
                "category": region,
                "line_count": len(group),
                "event_count": group["diff_id"].nunique(),
            }
        )
    exploded = evidence.assign(
        semantic_candidate=evidence["semantic_candidates"].fillna("").str.split(";")
    ).explode("semantic_candidate")
    exploded = exploded.loc[exploded["semantic_candidate"].ne("")]
    for (direction, scope), group in exploded.groupby(
        ["direction", "semantic_candidate"], sort=True
    ):
        rows.append(
            {
                "dimension": "semantic_candidate",
                "direction": direction,
                "category": scope,
                "line_count": len(group),
                "event_count": group["diff_id"].nunique(),
            }
        )
    return pd.DataFrame(rows)


def main() -> None:
    args = parse_args()
    if args.git_timeout_seconds <= 0:
        raise ValueError("--git-timeout-seconds deve ser positivo")
    input_path = Path(args.input).expanduser().resolve()
    cache_root = Path(args.cache_root).expanduser().resolve()
    output_dir = Path(args.output_dir).expanduser().resolve()
    events_path = output_dir / "structured_diff_events.csv"
    evidence_path = output_dir / "structured_diff_evidence.csv"
    counts_path = output_dir / "structured_diff_category_counts.csv"
    manifest_path = output_dir / "structured_diff_manifest.json"
    if not input_path.is_file() or not cache_root.is_dir():
        raise FileNotFoundError("Entrada de diffs ou cache Git não encontrado")
    output_dir.mkdir(parents=True, exist_ok=True)
    ensure_new_outputs(
        [events_path, evidence_path, counts_path, manifest_path], args.overwrite
    )

    source = pd.read_csv(input_path)
    required = {
        "diff_id",
        "repo_full_name",
        "status",
        "is_change_event",
        "old_blob_sha",
        "new_blob_sha",
        "diff_sha256",
        "raw_diff_file",
    }
    if missing := required.difference(source.columns):
        raise ValueError(f"Colunas ausentes: {sorted(missing)}")
    changes = source.loc[source["is_change_event"].eq(True)].copy()
    event_rows: list[dict[str, object]] = []
    evidence_rows: list[dict[str, object]] = []
    failures = 0
    verified_raw_diffs = 0
    for _, event in changes.sort_values("diff_id").iterrows():
        repository = cache_root / collector.cache_name(str(event["repo_full_name"]))
        old_sha = optional_sha(event["old_blob_sha"])
        new_sha = optional_sha(event["new_blob_sha"])
        try:
            old_text = read_blob(repository, old_sha, args.git_timeout_seconds)
            new_text = read_blob(repository, new_sha, args.git_timeout_seconds)
            old_lines, old_frontmatter = markdown_lines(old_text)
            new_lines, new_frontmatter = markdown_lines(new_text)
            raw_diff_path = input_path.parent / str(event["raw_diff_file"])
            raw_diff = raw_diff_path.read_text(encoding="utf-8")
            raw_diff_sha = hashlib.sha256(raw_diff.encode()).hexdigest()
            if raw_diff_sha != str(event["diff_sha256"]):
                raise RuntimeError(f"Checksum divergente: {raw_diff_path}")
            verified_raw_diffs += 1
            line_changes = changed_lines_from_unified_diff(
                raw_diff, old_lines, new_lines
            )
            operation = change_operation(str(event["status"]), old_text, new_text)
            classification_status = "classified"
            error = None
        except (OSError, RuntimeError, ValueError) as exception:
            failures += 1
            old_lines, new_lines, line_changes = [], [], []
            old_frontmatter = new_frontmatter = "unavailable"
            operation = "uncertain"
            classification_status = "failed"
            error = str(exception)[:2000]

        regions: set[str] = set()
        scopes: set[str] = set()
        rules: set[str] = set()
        added_count = 0
        deleted_count = 0
        for direction, line in line_changes:
            added_count += int(direction == "added")
            deleted_count += int(direction == "deleted")
            regions.add(line.structural_region)
            scopes.update(line.semantic_candidates)
            rules.update(line.rule_ids)
            evidence_rows.append(
                {
                    "diff_id": event["diff_id"],
                    "direction": direction,
                    "line_number": line.line_number,
                    "structural_region": line.structural_region,
                    "heading_context": line.heading_context,
                    "semantic_candidates": ";".join(line.semantic_candidates),
                    "rule_ids": ";".join(line.rule_ids),
                    "line_sha256": hashlib.sha256(line.text.encode()).hexdigest(),
                    "evidence_excerpt": line.text[:240],
                    "classifier_version": CLASSIFIER_VERSION,
                }
            )
        behavior_candidate = bool(
            scopes.intersection(
                {"command_code_candidate", "network_url_candidate", "script_candidate"}
            )
        )
        event_rows.append(
            {
                **event.to_dict(),
                "change_operation": operation,
                "structural_regions": ";".join(sorted(regions)),
                "semantic_scope_candidates": ";".join(sorted(scopes)),
                "rule_ids": ";".join(sorted(rules)),
                "structured_added_lines": added_count,
                "structured_deleted_lines": deleted_count,
                "old_frontmatter_status": old_frontmatter,
                "new_frontmatter_status": new_frontmatter,
                "behavior_relevance_candidate": behavior_candidate,
                "revert_candidate": "uncertain",
                "classification_status": classification_status,
                "classification_error": error,
                "alignment_method": "git_unified_diff",
                "classifier_version": CLASSIFIER_VERSION,
            }
        )

    events = pd.DataFrame(event_rows)
    evidence = pd.DataFrame(evidence_rows)
    counts = category_counts(events, evidence)
    atomic_csv(events, events_path)
    atomic_csv(evidence, evidence_path)
    atomic_csv(counts, counts_path)
    manifest = base_manifest(Path(__file__), vars(args))
    manifest["input"] = file_record(input_path)
    manifest["classifier_version"] = CLASSIFIER_VERSION
    manifest["rules"] = {
        "structural": [
            "front_matter",
            "heading",
            "list_item",
            "code_fence",
            "code_block",
            "indented_code",
            "blockquote",
            "table",
            "paragraph",
            "blank",
        ],
        "semantic_candidates": [
            "name",
            "description",
            "front_matter_other",
            "instruction_candidate",
            "example_candidate",
            "command_code_candidate",
            "network_url_candidate",
            "reference_candidate",
        ],
    }
    manifest["results"] = {
        "input_parent_comparisons": len(source),
        "input_change_events": len(changes),
        "classified_events": int(events["classification_status"].eq("classified").sum()),
        "failed_events": failures,
        "verified_raw_diffs": verified_raw_diffs,
        "evidence_rows": len(evidence),
        "behavior_relevance_candidates": int(
            events["behavior_relevance_candidate"].sum()
        ),
        "operation_counts": {
            str(key): int(value)
            for key, value in events["change_operation"].value_counts().sort_index().items()
        },
    }
    manifest["limitations"] = [
        "Semantic scopes are automated candidates, not externally validated meanings.",
        "Line-based matching does not infer moved blocks within edited documents.",
        "Code and URL detection identifies textual evidence, not execution or network access.",
        "No inter-rater agreement or gold-standard performance metric is available.",
    ]
    manifest["outputs"] = [
        file_record(events_path),
        file_record(evidence_path),
        file_record(counts_path),
    ]
    atomic_json(manifest_path, manifest)
    print(manifest["results"])
    print(f"Manifesto: {manifest_path}")


if __name__ == "__main__":
    main()
