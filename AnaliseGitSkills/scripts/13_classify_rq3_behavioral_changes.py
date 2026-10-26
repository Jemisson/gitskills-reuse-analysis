#!/usr/bin/env python3

"""Detect automated RQ3 behavioral-change candidates in structured RQ2 diffs."""

from __future__ import annotations

import argparse
import hashlib
import importlib
import os
import re
import subprocess
from pathlib import Path, PurePosixPath

import pandas as pd

from _provenance import atomic_json, base_manifest, ensure_new_outputs, file_record


collector = importlib.import_module("09_collect_rq2_histories")
diff_extractor = importlib.import_module("10_extract_rq2_diffs")
structured = importlib.import_module("12_classify_rq2_structured_diffs")
ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EVENTS = (
    ROOT
    / "outputs"
    / "rq2"
    / "structured_diff_calibration_v3"
    / "structured_diff_events.csv"
)
DEFAULT_EVIDENCE = (
    ROOT
    / "outputs"
    / "rq2"
    / "structured_diff_calibration_v3"
    / "structured_diff_evidence.csv"
)
DEFAULT_CACHE = (
    ROOT / "outputs" / "rq2" / "history_calibration_20261026" / "git_cache"
)
DEFAULT_OUTPUT_DIR = ROOT / "outputs" / "rq3" / "behavioral_calibration_v2"
CLASSIFIER_VERSION = "rq3-behavioral-candidates-v1.0"

COMMAND_RE = re.compile(
    r"^\s*(?:(?:\$|>)\s*)?(?:sudo\s+)?"
    r"(curl|wget|git|npm|npx|pnpm|yarn|pip|pip3|python|python3|node|bash|sh|zsh|"
    r"powershell|pwsh|docker|kubectl|helm|terraform|ansible|make|cmake|cargo|go|"
    r"java|mvn|gradle|dotnet|apt|apt-get|brew|chmod|chown|cp|mv|rm|mkdir|"
    r"systemctl|ssh|scp|rsync)\b",
    re.IGNORECASE,
)
BROAD_COMMAND_RE = re.compile(
    r"^\s*(?:(?:\$|>)\s*)?[A-Za-z0-9_./-]+(?:\s+(?:--?\w|[A-Za-z0-9_./${}-]+))"
)
NETWORK_OPERATION_RE = re.compile(
    r"\b(curl|wget|httpie|invoke-webrequest|fetch\s*\(|axios|requests\.(?:get|post|put|delete)|"
    r"download|upload|webhook|api\s+(?:call|request|endpoint)|ssh|scp|rsync)\b",
    re.IGNORECASE,
)
SCRIPT_PATH_RE = re.compile(
    r"(?<![\w.-])(?:[\w.-]+/)*[\w.-]+\.(sh|bash|zsh|py|js|mjs|cjs|ts|ps1|rb|pl|php|"
    r"go|jar|exe|bat|cmd)(?![\w.-])",
    re.IGNORECASE,
)
SCRIPT_INVOKE_RE = re.compile(
    r"(?:^|\s)(?:\./|bash\s+|sh\s+|zsh\s+|python(?:3)?\s+|node\s+|"
    r"powershell\s+|pwsh\s+)[^\s`]+\.(?:sh|bash|zsh|py|js|mjs|cjs|ts|ps1|rb|pl|php|"
    r"go|jar|exe|bat|cmd)\b",
    re.IGNORECASE,
)
EXECUTABLE_EXTENSIONS = {
    ".sh",
    ".bash",
    ".zsh",
    ".py",
    ".js",
    ".mjs",
    ".cjs",
    ".ts",
    ".ps1",
    ".rb",
    ".pl",
    ".php",
    ".go",
    ".jar",
    ".exe",
    ".bat",
    ".cmd",
}
CODE_REGIONS = {"code_block", "code_fence", "indented_code"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--events", default=str(DEFAULT_EVENTS))
    parser.add_argument("--evidence", default=str(DEFAULT_EVIDENCE))
    parser.add_argument("--cache-root", default=str(DEFAULT_CACHE))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--git-timeout-seconds", type=float, default=60.0)
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def text_rule_hits(text: str, region: str, rule_ids: str) -> list[dict[str, str]]:
    code_context = region in CODE_REGIONS or "TOKEN_INLINE_CODE" in str(rule_ids).split(";")
    strict_command = bool(code_context and COMMAND_RE.search(text))
    broad_command = bool(strict_command or (code_context and BROAD_COMMAND_RE.search(text)))
    has_url = bool(structured.URL_RE.search(text))
    strict_external = bool(NETWORK_OPERATION_RE.search(text))
    broad_external = bool(strict_external or has_url)
    has_script_path = bool(SCRIPT_PATH_RE.search(text))
    strict_script = bool(SCRIPT_INVOKE_RE.search(text))
    broad_script = bool(strict_script or has_script_path)
    hits: list[dict[str, str]] = []
    rules = [
        ("command", "strict", strict_command, "CMD_KNOWN_CLI_IN_CODE"),
        ("command", "broad", broad_command, "CMD_CODE_SHAPE_OR_STRICT"),
        ("external_access", "strict", strict_external, "NET_OPERATION_TOKEN"),
        ("external_access", "broad", broad_external, "NET_URL_OR_OPERATION"),
        ("script_reference", "strict", strict_script, "SCRIPT_EXPLICIT_INVOKE"),
        ("script_reference", "broad", broad_script, "SCRIPT_PATH_OR_INVOKE"),
    ]
    for target, scenario, matched, rule_id in rules:
        if matched:
            hits.append({"target": target, "scenario": scenario, "rule_id": rule_id})
    return hits


def parent_value(value: object) -> str | None:
    if pd.isna(value):
        return None
    text = str(value).strip()
    return text or None


def git_mode_and_blob(
    repository: Path, commit: str | None, path: str, timeout_seconds: float
) -> tuple[str | None, str | None]:
    if commit is None:
        return None, None
    result = collector.run_git(
        repository,
        ["ls-tree", commit, "--", collector.safe_git_path(path)],
        timeout_seconds,
    )
    if result.returncode != 0 or not result.stdout.strip():
        return None, None
    metadata = result.stdout.split("\t", 1)[0].split()
    if len(metadata) < 3:
        return None, None
    return metadata[0], metadata[2]


def blob_has_shebang(
    repository: Path, blob_sha: str | None, timeout_seconds: float
) -> bool:
    if blob_sha is None:
        return False
    environment = os.environ.copy()
    environment["GIT_TERMINAL_PROMPT"] = "0"
    result = subprocess.run(
        ["git", "-C", str(repository), "cat-file", "blob", blob_sha],
        capture_output=True,
        timeout=timeout_seconds,
        env=environment,
        check=False,
    )
    return result.returncode == 0 and result.stdout.startswith(b"#!")


def sibling_changes(
    repository: Path,
    parent: str | None,
    commit: str,
    skill_paths: set[str],
    timeout_seconds: float,
) -> list[dict[str, str | None]]:
    directories = sorted(
        {
            PurePosixPath(collector.safe_git_path(path)).parent.as_posix()
            for path in skill_paths
        }
    )
    directories = ["." if directory == "." else directory for directory in directories]
    if parent:
        arguments = ["diff", "-M", "--name-status", parent, commit, "--", *directories]
    else:
        arguments = [
            "diff-tree",
            "--root",
            "-r",
            "-M",
            "--no-commit-id",
            "--name-status",
            commit,
            "--",
            *directories,
        ]
    result = collector.run_git(repository, arguments, timeout_seconds)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "Falha ao obter siblings")
    return [
        change
        for change in diff_extractor.parse_name_status(result.stdout)
        if change["old_path"] not in skill_paths and change["new_path"] not in skill_paths
    ]


def sibling_operation(status: str) -> str:
    if status == "A":
        return "added"
    if status == "D":
        return "removed"
    if status.startswith(("R", "C")):
        return "moved_or_copied"
    return "modified"


def is_broad_executable_candidate(path: str, mode: str | None, shebang: bool) -> bool:
    return bool(
        mode == "100755"
        or shebang
        or PurePosixPath(path).suffix.lower() in EXECUTABLE_EXTENSIONS
    )


def atomic_csv(frame: pd.DataFrame, path: Path) -> None:
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        frame.to_csv(temporary, index=False)
        temporary.replace(path)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise


def main() -> None:
    args = parse_args()
    if args.git_timeout_seconds <= 0:
        raise ValueError("--git-timeout-seconds deve ser positivo")
    events_path = Path(args.events).expanduser().resolve()
    evidence_path = Path(args.evidence).expanduser().resolve()
    cache_root = Path(args.cache_root).expanduser().resolve()
    output_dir = Path(args.output_dir).expanduser().resolve()
    output_events_path = output_dir / "rq3_behavioral_events.csv"
    text_evidence_path = output_dir / "rq3_text_evidence.csv"
    sibling_evidence_path = output_dir / "rq3_sibling_evidence.csv"
    counts_path = output_dir / "rq3_candidate_counts.csv"
    manifest_path = output_dir / "rq3_behavioral_manifest.json"
    if not events_path.is_file() or not evidence_path.is_file() or not cache_root.is_dir():
        raise FileNotFoundError("Eventos, evidências ou cache não encontrados")
    output_dir.mkdir(parents=True, exist_ok=True)
    ensure_new_outputs(
        [
            output_events_path,
            text_evidence_path,
            sibling_evidence_path,
            counts_path,
            manifest_path,
        ],
        args.overwrite,
    )

    events = pd.read_csv(events_path)
    evidence = pd.read_csv(evidence_path)
    event_rows: list[dict[str, object]] = []
    text_rows: list[dict[str, object]] = []
    sibling_rows: list[dict[str, object]] = []
    failures = 0
    for _, event in events.sort_values("diff_id").iterrows():
        repository = cache_root / collector.cache_name(str(event["repo_full_name"]))
        old_sha = structured.optional_sha(event["old_blob_sha"])
        new_sha = structured.optional_sha(event["new_blob_sha"])
        try:
            old_text = structured.read_blob(repository, old_sha, args.git_timeout_seconds)
            new_text = structured.read_blob(repository, new_sha, args.git_timeout_seconds)
            old_lines, _ = structured.markdown_lines(old_text)
            new_lines, _ = structured.markdown_lines(new_text)
            event_evidence = evidence.loc[evidence["diff_id"].eq(event["diff_id"])]
            for _, item in event_evidence.iterrows():
                direction = str(item["direction"])
                line_number = int(item["line_number"])
                lines = new_lines if direction == "added" else old_lines
                if line_number < 1 or line_number > len(lines):
                    raise ValueError("Número de linha fora do blob")
                text = lines[line_number - 1].text
                for hit in text_rule_hits(
                    text, str(item["structural_region"]), str(item["rule_ids"])
                ):
                    text_rows.append(
                        {
                            "diff_id": event["diff_id"],
                            "direction": direction,
                            "line_number": line_number,
                            "target": hit["target"],
                            "scenario": hit["scenario"],
                            "rule_id": hit["rule_id"],
                            "structural_region": item["structural_region"],
                            "line_sha256": hashlib.sha256(text.encode()).hexdigest(),
                            "evidence_excerpt": text[:240],
                            "classifier_version": CLASSIFIER_VERSION,
                        }
                    )

            parent = parent_value(event["parent"])
            commit = str(event["commit"])
            skill_paths = {str(event["old_path"]), str(event["new_path"])}
            for change in sibling_changes(
                repository,
                parent,
                commit,
                skill_paths,
                args.git_timeout_seconds,
            ):
                old_path = str(change["old_path"])
                new_path = str(change["new_path"])
                old_mode, old_blob = git_mode_and_blob(
                    repository, parent, old_path, args.git_timeout_seconds
                )
                new_mode, new_blob = git_mode_and_blob(
                    repository, commit, new_path, args.git_timeout_seconds
                )
                old_shebang = blob_has_shebang(
                    repository, old_blob, args.git_timeout_seconds
                )
                new_shebang = blob_has_shebang(
                    repository, new_blob, args.git_timeout_seconds
                )
                strict = bool(old_mode == "100755" or new_mode == "100755" or old_shebang or new_shebang)
                broad = bool(
                    strict
                    or is_broad_executable_candidate(old_path, old_mode, old_shebang)
                    or is_broad_executable_candidate(new_path, new_mode, new_shebang)
                )
                if not broad:
                    continue
                sibling_rows.append(
                    {
                        "diff_id": event["diff_id"],
                        "operation": sibling_operation(str(change["status"])),
                        "git_status": change["status"],
                        "old_path": old_path,
                        "new_path": new_path,
                        "old_mode": old_mode,
                        "new_mode": new_mode,
                        "old_blob_sha": old_blob,
                        "new_blob_sha": new_blob,
                        "old_shebang": old_shebang,
                        "new_shebang": new_shebang,
                        "strict_candidate": strict,
                        "broad_candidate": broad,
                        "strict_rule_id": "SIBLING_EXEC_MODE_OR_SHEBANG" if strict else None,
                        "broad_rule_id": "SIBLING_MODE_SHEBANG_OR_EXTENSION",
                        "classifier_version": CLASSIFIER_VERSION,
                    }
                )
            classification_status = "classified"
            error = None
        except (OSError, RuntimeError, ValueError) as exception:
            failures += 1
            classification_status = "failed"
            error = str(exception)[:2000]

        event_text = [row for row in text_rows if row["diff_id"] == event["diff_id"]]
        event_siblings = [row for row in sibling_rows if row["diff_id"] == event["diff_id"]]
        summary: dict[str, object] = {
            **event.to_dict(),
            "classification_status_rq3": classification_status,
            "classification_error_rq3": error,
            "classifier_version_rq3": CLASSIFIER_VERSION,
        }
        for scenario in ("strict", "broad"):
            for target in ("command", "external_access", "script_reference"):
                for direction in ("added", "deleted"):
                    summary[f"{target}_{direction}_{scenario}"] = any(
                        row["scenario"] == scenario
                        and row["target"] == target
                        and row["direction"] == direction
                        for row in event_text
                    )
            for operation in ("added", "removed", "modified", "moved_or_copied"):
                summary[f"executable_sibling_{operation}_{scenario}"] = any(
                    row["operation"] == operation
                    and bool(row[f"{scenario}_candidate"])
                    for row in event_siblings
                )
        event_rows.append(summary)

    output_events = pd.DataFrame(event_rows)
    text_evidence = pd.DataFrame(text_rows)
    sibling_evidence = pd.DataFrame(sibling_rows)
    if len(text_evidence):
        evidence_key = ["diff_id", "direction", "line_number", "target"]
        strict_keys = set(
            map(
                tuple,
                text_evidence.loc[
                    text_evidence["scenario"].eq("strict"), evidence_key
                ].itertuples(index=False, name=None),
            )
        )
        broad_keys = set(
            map(
                tuple,
                text_evidence.loc[
                    text_evidence["scenario"].eq("broad"), evidence_key
                ].itertuples(index=False, name=None),
            )
        )
        if not strict_keys.issubset(broad_keys):
            raise ValueError("Cenário estrito não é subconjunto do amplo")
    if len(sibling_evidence) and not (
        ~sibling_evidence["strict_candidate"]
        | sibling_evidence["broad_candidate"]
    ).all():
        raise ValueError("Sibling estrito não é subconjunto do amplo")
    count_rows: list[dict[str, object]] = []
    if len(text_evidence):
        for (scenario, target, direction), group in text_evidence.groupby(
            ["scenario", "target", "direction"], sort=True
        ):
            count_rows.append(
                {
                    "source": "skill_text",
                    "scenario": scenario,
                    "target": target,
                    "direction": direction,
                    "evidence_count": len(group),
                    "event_count": group["diff_id"].nunique(),
                }
            )
    if len(sibling_evidence):
        for scenario in ("strict", "broad"):
            subset = sibling_evidence.loc[sibling_evidence[f"{scenario}_candidate"]]
            for operation, group in subset.groupby("operation", sort=True):
                count_rows.append(
                    {
                        "source": "sibling",
                        "scenario": scenario,
                        "target": "executable_candidate",
                        "direction": operation,
                        "evidence_count": len(group),
                        "event_count": group["diff_id"].nunique(),
                    }
                )
    counts = pd.DataFrame(count_rows)
    atomic_csv(output_events, output_events_path)
    atomic_csv(text_evidence, text_evidence_path)
    atomic_csv(sibling_evidence, sibling_evidence_path)
    atomic_csv(counts, counts_path)

    manifest = base_manifest(Path(__file__), vars(args))
    manifest["inputs"] = [file_record(events_path), file_record(evidence_path)]
    manifest["classifier_version"] = CLASSIFIER_VERSION
    manifest["scenario_definitions"] = {
        "strict": "Operational command/network token or sibling executable mode/shebang.",
        "broad": "Strict evidence plus code-shaped text, explicit URL, script path, or executable extension.",
    }
    manifest["results"] = {
        "input_events": len(events),
        "classified_events": int(
            output_events["classification_status_rq3"].eq("classified").sum()
        ),
        "failed_events": failures,
        "text_evidence_rows": len(text_evidence),
        "sibling_evidence_rows": len(sibling_evidence),
        "events_with_any_strict_text_candidate": int(
            text_evidence.loc[text_evidence["scenario"].eq("strict"), "diff_id"].nunique()
            if len(text_evidence)
            else 0
        ),
        "events_with_any_broad_text_candidate": int(
            text_evidence.loc[text_evidence["scenario"].eq("broad"), "diff_id"].nunique()
            if len(text_evidence)
            else 0
        ),
        "events_with_strict_executable_sibling_candidate": int(
            sibling_evidence.loc[sibling_evidence["strict_candidate"], "diff_id"].nunique()
            if len(sibling_evidence)
            else 0
        ),
        "events_with_broad_executable_sibling_candidate": int(
            sibling_evidence.loc[sibling_evidence["broad_candidate"], "diff_id"].nunique()
            if len(sibling_evidence)
            else 0
        ),
    }
    manifest["limitations"] = [
        "All labels are automated candidates without independent human validation.",
        "Textual commands do not establish execution and URLs do not establish network access.",
        "Sibling executable candidates use Git mode, shebang, or extension; none proves execution.",
        "Calibration counts are not population prevalence estimates.",
    ]
    manifest["outputs"] = [
        file_record(output_events_path),
        file_record(text_evidence_path),
        file_record(sibling_evidence_path),
        file_record(counts_path),
    ]
    atomic_json(manifest_path, manifest)
    print(manifest["results"])
    print(f"Manifesto: {manifest_path}")


if __name__ == "__main__":
    main()
