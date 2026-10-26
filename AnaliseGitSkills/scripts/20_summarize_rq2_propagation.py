#!/usr/bin/env python3

"""Summarize cross-repository patch candidates with explicit evidential limits."""

from __future__ import annotations

import argparse
import math
import os
from pathlib import Path

import pandas as pd

from _provenance import atomic_json, base_manifest, ensure_new_outputs, file_record


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RELATIONS = ROOT / "outputs/rq2/genealogical_relations_v4/genealogical_relations.csv"
DEFAULT_REJECTED = ROOT / "outputs/rq2/genealogical_relations_v4/rejected_relations.csv"
DEFAULT_COVERAGE = ROOT / "outputs/rq2/adoption_candidates_v3/search_coverage.csv"
DEFAULT_OUTPUT = ROOT / "outputs/rq2/propagation_results_v4"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--relations", default=str(DEFAULT_RELATIONS))
    parser.add_argument("--rejected", default=str(DEFAULT_REJECTED))
    parser.add_argument("--coverage", default=str(DEFAULT_COVERAGE))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def atomic_csv(frame: pd.DataFrame, path: Path) -> None:
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    frame.to_csv(temporary, index=False)
    temporary.replace(path)


def safe_stat(series: pd.Series, statistic: str) -> float:
    if series.empty:
        return math.nan
    return float(getattr(series.astype(float), statistic)())


def main() -> None:
    args = parse_args()
    relations_path = Path(args.relations).expanduser().resolve()
    rejected_path = Path(args.rejected).expanduser().resolve()
    coverage_path = Path(args.coverage).expanduser().resolve()
    inputs = [relations_path, rejected_path, coverage_path]
    if any(not path.is_file() for path in inputs):
        raise FileNotFoundError("Entrada de síntese de propagação não encontrada")
    output_dir = Path(args.output_dir).expanduser().resolve()
    events_path = output_dir / "propagation_candidates.csv"
    summary_path = output_dir / "propagation_summary.csv"
    confidence_path = output_dir / "propagation_by_confidence.csv"
    manifest_path = output_dir / "propagation_manifest.json"
    output_dir.mkdir(parents=True, exist_ok=True)
    ensure_new_outputs([events_path, summary_path, confidence_path, manifest_path], args.overwrite)
    relations = pd.read_csv(relations_path)
    rejected = pd.read_csv(rejected_path)
    coverage = pd.read_csv(coverage_path)
    if relations.empty:
        confidence = pd.DataFrame(columns=["confidence_level", "candidate_relations", "patch_signatures", "source_repositories", "target_repositories", "median_delay_days"])
    else:
        confidence = (
            relations.groupby("confidence_level", sort=True)
            .agg(
                candidate_relations=("target_diff_id", "size"),
                patch_signatures=("patch_signature", "nunique"),
                source_repositories=("source_repo", "nunique"),
                target_repositories=("target_repo", "nunique"),
                median_delay_days=("delay_days", "median"),
            )
            .reset_index()
        )
    delays = relations.get("delay_days", pd.Series(dtype=float)).dropna()
    summary = pd.DataFrame(
        [
            ["directed_candidate_relations", len(relations), "count", "B+C candidates; not proven propagation"],
            ["confidence_B_relations", int(relations.get("confidence_level", pd.Series(dtype=str)).eq("B").sum()), "count", "strong operational candidates"],
            ["confidence_C_relations", int(relations.get("confidence_level", pd.Series(dtype=str)).eq("C").sum()), "count", "weaker operational candidates"],
            ["distinct_patch_signatures", int(relations.get("patch_signature", pd.Series(dtype=str)).nunique()), "count", "among directed candidates"],
            ["direction_indeterminate_pairs", len(rejected), "count", "timestamp ties excluded from directed relations"],
            ["median_delay_days", safe_stat(delays, "median"), "days", "descriptive among directed candidates"],
            ["minimum_delay_days", safe_stat(delays, "min"), "days", "descriptive among directed candidates"],
            ["maximum_delay_days", safe_stat(delays, "max"), "days", "descriptive among directed candidates"],
            ["sources_with_temporal_opportunity", int((coverage["temporally_observable_repositories"] > 0).sum()), "count", "context eligibility remains unknown"],
            ["propagation_rate", math.nan, "not_estimable", "no context-eligible denominator"],
        ],
        columns=["metric", "value", "unit", "interpretation"],
    )
    atomic_csv(relations, events_path)
    atomic_csv(summary, summary_path)
    atomic_csv(confidence, confidence_path)
    manifest = base_manifest(Path(__file__), vars(args))
    manifest["inputs"] = [file_record(path) for path in inputs]
    manifest["results"] = {
        "directed_candidate_relations": len(relations),
        "distinct_patch_signatures": int(relations.get("patch_signature", pd.Series(dtype=str)).nunique()),
        "direction_indeterminate_pairs": len(rejected),
        "propagation_rate_estimable": False,
    }
    manifest["non_estimability_reason"] = (
        "Observation windows provide temporal opportunity only. The pipeline cannot establish that each "
        "non-adopting lineage retained the patch's applicable pre-change context at the source time."
    )
    manifest["limitations"] = [
        "Outputs are candidate relations within 53 complete repositories, not a GitHub-wide genealogy.",
        "No origin is assigned and no B/C relation is called causal transmission.",
        "No confidence interval or propagation rate is produced without a valid eligible denominator.",
    ]
    manifest["outputs"] = [file_record(p) for p in [events_path, summary_path, confidence_path]]
    atomic_json(manifest_path, manifest)
    print(manifest["results"])
    print(f"Manifesto: {manifest_path}")


if __name__ == "__main__":
    main()
