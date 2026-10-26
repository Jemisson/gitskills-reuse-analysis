#!/usr/bin/env python3

"""Build an event-level RQ3 dataset using only pre-event or concurrent covariates."""

from __future__ import annotations

import argparse
import importlib
import math
import os
from pathlib import Path

import pandas as pd

from _provenance import atomic_json, base_manifest, ensure_new_outputs, file_record


collector = importlib.import_module("09_collect_rq2_histories")
structured = importlib.import_module("12_classify_rq2_structured_diffs")
behavioral = importlib.import_module("13_classify_rq3_behavioral_changes")
ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EVENTS = ROOT / "outputs/exploratory_results_v2/post_anchor_events.csv"
DEFAULT_OUTCOMES = ROOT / "outputs/exploratory_results_v2/rq2_occurrence_outcomes.csv"
DEFAULT_FLOW = ROOT / "outputs/rq2/analytic_recovery_v1/analytic_recovery_flow.csv"
DEFAULT_CACHE = ROOT / "outputs/rq2/history_calibration_20261026/git_cache"
DEFAULT_OUTPUT = ROOT / "outputs/rq3/association_dataset_v2"
DATASET_VERSION = "rq3-association-dataset-v1.0"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--events", default=str(DEFAULT_EVENTS))
    parser.add_argument("--outcomes", default=str(DEFAULT_OUTCOMES))
    parser.add_argument("--flow", default=str(DEFAULT_FLOW))
    parser.add_argument("--cache-root", default=str(DEFAULT_CACHE))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--git-timeout-seconds", type=float, default=60.0)
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def parent_text_features(text: str) -> dict[str, object]:
    lines, frontmatter = structured.markdown_lines(text)
    flags = {
        f"parent_has_{target}_{scenario}": False
        for target in ("command", "external_access", "script_reference")
        for scenario in ("strict", "broad")
    }
    for line in lines:
        hits = behavioral.text_rule_hits(
            line.text, line.structural_region, ";".join(line.rule_ids)
        )
        for hit in hits:
            flags[f"parent_has_{hit['target']}_{hit['scenario']}"] = True
    return {
        "parent_line_count": len(lines),
        "parent_character_count": len(text),
        "parent_heading_count": sum(line.structural_region == "heading" for line in lines),
        "parent_code_line_count": sum(
            line.structural_region in behavioral.CODE_REGIONS for line in lines
        ),
        "parent_url_line_count": sum(bool(structured.URL_RE.search(line.text)) for line in lines),
        "parent_frontmatter_status": frontmatter,
        **flags,
    }


def days_between(later: pd.Timestamp, earlier: object) -> float:
    if pd.isna(earlier):
        return math.nan
    value = pd.Timestamp(earlier)
    if value.tzinfo is None:
        value = value.tz_localize("UTC")
    else:
        value = value.tz_convert("UTC")
    return (later - value).total_seconds() / 86400


def atomic_csv(frame: pd.DataFrame, path: Path) -> None:
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    frame.to_csv(temporary, index=False)
    temporary.replace(path)


def main() -> None:
    args = parse_args()
    if args.git_timeout_seconds <= 0:
        raise ValueError("--git-timeout-seconds deve ser positivo")
    events_path = Path(args.events).expanduser().resolve()
    outcomes_path = Path(args.outcomes).expanduser().resolve()
    flow_path = Path(args.flow).expanduser().resolve()
    cache_root = Path(args.cache_root).expanduser().resolve()
    inputs = [events_path, outcomes_path, flow_path]
    if any(not p.is_file() for p in inputs) or not cache_root.is_dir():
        raise FileNotFoundError("Entrada da base associativa não encontrada")
    output_dir = Path(args.output_dir).expanduser().resolve()
    dataset_path = output_dir / "rq3_association_events.csv"
    dictionary_path = output_dir / "rq3_association_dictionary.csv"
    manifest_path = output_dir / "rq3_association_dataset_manifest.json"
    output_dir.mkdir(parents=True, exist_ok=True)
    ensure_new_outputs([dataset_path, dictionary_path, manifest_path], args.overwrite)

    events = pd.read_csv(events_path)
    outcomes = pd.read_csv(outcomes_path)[["occurrence_id", "anchor_file_sha"]]
    flow = pd.read_csv(flow_path)
    flow = flow.loc[flow["analysis_eligible"].eq(True)].drop_duplicates("occurrence_id")
    baseline_columns = [
        "occurrence_id", "occurrence_count", "reuse_count", "location_class",
        "repo_is_fork", "repo_created_at",
    ]
    data = events.merge(outcomes, on="occurrence_id", how="left", validate="many_to_one")
    data = data.merge(flow[baseline_columns], on="occurrence_id", how="left", validate="many_to_one")
    data["committed_at"] = pd.to_datetime(data["committed_at"], utc=True, format="mixed")
    data["anchor_committed_at"] = pd.to_datetime(data["anchor_committed_at"], utc=True, format="mixed")
    data["repo_created_at"] = pd.to_datetime(data["repo_created_at"], utc=True, format="mixed", errors="coerce")
    rows: list[dict[str, object]] = []
    for _, event in data.sort_values(["occurrence_id", "committed_at", "diff_id"]).iterrows():
        repository = cache_root / collector.cache_name(str(event["repo_full_name"]))
        old_sha = structured.optional_sha(event["old_blob_sha"])
        parent_text = structured.read_blob(repository, old_sha, args.git_timeout_seconds)
        features = parent_text_features(parent_text)
        occurrence_history = data.loc[data["occurrence_id"].eq(event["occurrence_id"])]
        prior = occurrence_history.loc[occurrence_history["committed_at"].lt(event["committed_at"])]
        previous_time = prior["committed_at"].max() if len(prior) else pd.NaT
        repository_age = days_between(event["committed_at"], event["repo_created_at"])
        if repository_age < 0:
            repository_age = math.nan
        row = event.to_dict()
        row.update(
            {
                "dataset_version": DATASET_VERSION,
                "parent_blob_present": old_sha is not None,
                "days_since_anchor": days_between(event["committed_at"], event["anchor_committed_at"]),
                "days_since_previous_observed_event": days_between(event["committed_at"], previous_time),
                "prior_observed_events": len(prior),
                "prior_divergence_events": int(prior["is_divergence_from_anchor"].astype(bool).sum()),
                "repository_age_days": repository_age,
                "diff_changed_lines": int(event["added_lines"]) + int(event["deleted_lines"]),
                **features,
            }
        )
        rows.append(row)
    dataset = pd.DataFrame(rows).sort_values("diff_id")
    if dataset["diff_id"].duplicated().any():
        raise ValueError("diff_id duplicado na base associativa")
    dictionary_rows = [
        ("days_since_anchor", "pre-event", "Dias entre a âncora exata e o evento"),
        ("days_since_previous_observed_event", "pre-event", "Dias desde o evento anterior estritamente mais antigo"),
        ("prior_observed_events", "pre-event", "Eventos observados estritamente anteriores na ocorrência"),
        ("prior_divergence_events", "pre-event", "Divergências observadas estritamente anteriores"),
        ("repository_age_days", "pre-event", "Idade observável do repositório no evento"),
        ("reuse_count", "baseline", "Repositórios com o hash-âncora no snapshot"),
        ("occurrence_count", "baseline", "Ocorrências do hash-âncora no snapshot"),
        ("location_class", "baseline", "Classe do path no snapshot"),
        ("repo_is_fork", "baseline", "Indicador de fork disponível no snapshot"),
        ("parent_*", "pre-event", "Características do blob pai, antes da mudança"),
        ("is_merge", "concurrent", "Evento pertence a commit de merge"),
        ("change_operation", "concurrent", "Operação estrutural do evento"),
        ("diff_changed_lines", "concurrent", "Churn do evento; não usar quando for parte da definição do desfecho"),
        ("*_strict/*_broad", "outcome", "Candidato automatizado segundo o cenário indicado"),
    ]
    dictionary = pd.DataFrame(dictionary_rows, columns=["variable", "temporal_role", "definition"])
    atomic_csv(dataset, dataset_path)
    atomic_csv(dictionary, dictionary_path)
    outcome_columns = [
        c for c in dataset
        if (c.endswith("_strict") or c.endswith("_broad"))
        and not c.startswith("parent_has_")
    ]
    manifest = base_manifest(Path(__file__), vars(args))
    manifest["inputs"] = [file_record(p) for p in inputs]
    manifest["dataset_version"] = DATASET_VERSION
    manifest["results"] = {
        "events": len(dataset),
        "repositories": int(dataset["repo_full_name"].nunique()),
        "occurrences": int(dataset["occurrence_id"].nunique()),
        "anchor_families": int(dataset["anchor_file_sha"].nunique()),
        "outcomes": len(outcome_columns),
        "parent_blob_available": int(dataset["parent_blob_present"].sum()),
    }
    manifest["limitations"] = [
        "The dataset contains only post-anchor comparisons in analytic complete cases.",
        "Parent text indicators use the same unvalidated automated rules as the outcomes.",
        "Concurrent event characteristics are separated from genuinely pre-event variables.",
        "Repository metadata is snapshot-derived and may not represent historical state exactly.",
    ]
    manifest["outputs"] = [file_record(dataset_path), file_record(dictionary_path)]
    atomic_json(manifest_path, manifest)
    print(manifest["results"])
    print(f"Manifesto: {manifest_path}")


if __name__ == "__main__":
    main()
