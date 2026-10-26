#!/usr/bin/env python3

"""Select a reproducible, stratified RQ2 history-calibration subsample."""

from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path

import pandas as pd

from _provenance import atomic_json, base_manifest, ensure_new_outputs, file_record


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OCCURRENCES = ROOT / "outputs" / "rq2" / "pilot" / "pilot_occurrences.csv"
DEFAULT_ANCHORS = ROOT / "outputs" / "rq2" / "pilot" / "pilot_anchors.csv"
DEFAULT_PROBES = [
    ROOT / "outputs" / "rq2" / "recoverability" / "repository_probe.csv",
    ROOT / "outputs" / "rq2" / "recoverability_v2" / "repository_probe.csv",
]
DEFAULT_OUTPUT_DIR = ROOT / "outputs" / "rq2" / "history_calibration_sample"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--occurrences", default=str(DEFAULT_OCCURRENCES))
    parser.add_argument("--anchors", default=str(DEFAULT_ANCHORS))
    parser.add_argument("--probe-file", action="append")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--per-stratum", type=int, default=1)
    parser.add_argument("--max-repositories", type=int, default=11)
    parser.add_argument("--seed", type=int, default=20261026)
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def stable_accessible(probes: list[pd.DataFrame]) -> set[str]:
    accessible_sets = [
        set(probe.loc[probe["status"].eq("accessible"), "repo_full_name"])
        for probe in probes
    ]
    return set.intersection(*accessible_sets) if accessible_sets else set()


def deterministic_rank(seed: int, stratum: str, repository: str) -> str:
    return hashlib.sha256(
        f"{seed}\0{stratum}\0{repository}".encode("utf-8")
    ).hexdigest()


def select_repositories(
    occurrences: pd.DataFrame,
    anchors: pd.DataFrame,
    accessible: set[str],
    per_stratum: int,
    max_repositories: int,
    seed: int,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    linked = occurrences.merge(
        anchors[["anchor_file_sha", "pilot_stratum"]],
        on="anchor_file_sha",
        how="left",
        validate="many_to_one",
    )
    if linked["pilot_stratum"].isna().any():
        raise ValueError("Ocorrência sem estrato de âncora")
    eligible = linked.loc[linked["repo_full_name"].isin(accessible)].copy()
    pairs = eligible[["pilot_stratum", "repo_full_name"]].drop_duplicates()
    pairs["random_key"] = [
        deterministic_rank(seed, stratum, repository)
        for stratum, repository in zip(pairs["pilot_stratum"], pairs["repo_full_name"])
    ]
    pairs = pairs.sort_values(["pilot_stratum", "random_key", "repo_full_name"])

    selected_repositories: set[str] = set()
    selection_rows: list[dict[str, object]] = []
    achieved: dict[str, int] = {}
    strata = sorted(pairs["pilot_stratum"].unique())
    by_stratum = {
        stratum: group.reset_index(drop=True)
        for stratum, group in pairs.groupby("pilot_stratum", sort=True)
    }
    for round_index in range(per_stratum):
        for stratum in strata:
            if len(selected_repositories) >= max_repositories:
                break
            if achieved.get(stratum, 0) >= per_stratum:
                continue
            candidates = by_stratum[stratum]
            chosen = None
            for rank, row in candidates.iterrows():
                repository = str(row["repo_full_name"])
                if repository not in selected_repositories:
                    chosen = (repository, rank + 1, str(row["random_key"]))
                    break
            if chosen is None:
                continue
            repository, candidate_rank, random_key = chosen
            selected_repositories.add(repository)
            achieved[stratum] = achieved.get(stratum, 0) + 1
            selection_rows.append(
                {
                    "repo_full_name": repository,
                    "selection_stratum": stratum,
                    "selection_round": round_index + 1,
                    "candidate_rank_within_stratum": candidate_rank,
                    "random_key": random_key,
                }
            )
        if len(selected_repositories) >= max_repositories:
            break

    selection = pd.DataFrame(selection_rows)
    selected_occurrences = eligible.loc[
        eligible["repo_full_name"].isin(selected_repositories)
    ].copy()
    selected_occurrences = selected_occurrences.merge(
        selection[["repo_full_name", "selection_stratum"]],
        on="repo_full_name",
        how="left",
        validate="many_to_one",
    ).sort_values(["selection_stratum", "repo_full_name", "anchor_file_sha", "path"])

    candidate_counts = pairs.groupby("pilot_stratum").size()
    coverage = pd.DataFrame({"pilot_stratum": strata})
    coverage["eligible_repositories"] = coverage["pilot_stratum"].map(candidate_counts)
    coverage["target_repositories"] = per_stratum
    coverage["selected_repositories"] = coverage["pilot_stratum"].map(
        achieved
    ).fillna(0).astype(int)
    occurrence_counts = selected_occurrences.groupby("pilot_stratum").size()
    coverage["selected_occurrences"] = coverage["pilot_stratum"].map(
        occurrence_counts
    ).fillna(0).astype(int)
    return selection, selected_occurrences, coverage


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
    if args.per_stratum < 1 or args.max_repositories < 1:
        raise ValueError("Limites de seleção devem ser positivos")
    occurrences_path = Path(args.occurrences).expanduser().resolve()
    anchors_path = Path(args.anchors).expanduser().resolve()
    probe_paths = [
        Path(item).expanduser().resolve()
        for item in (args.probe_file or [str(path) for path in DEFAULT_PROBES])
    ]
    input_paths = [occurrences_path, anchors_path, *probe_paths]
    if any(not path.is_file() for path in input_paths):
        raise FileNotFoundError("Entrada de seleção não encontrada")
    output_dir = Path(args.output_dir).expanduser().resolve()
    repositories_path = output_dir / "selected_repositories.csv"
    selected_occurrences_path = output_dir / "selected_occurrences.csv"
    coverage_path = output_dir / "stratum_coverage.csv"
    manifest_path = output_dir / "selection_manifest.json"
    output_dir.mkdir(parents=True, exist_ok=True)
    ensure_new_outputs(
        [repositories_path, selected_occurrences_path, coverage_path, manifest_path],
        args.overwrite,
    )

    occurrences = pd.read_csv(occurrences_path)
    anchors = pd.read_csv(anchors_path)
    probes = [pd.read_csv(path) for path in probe_paths]
    accessible = stable_accessible(probes)
    selection, selected_occurrences, coverage = select_repositories(
        occurrences,
        anchors,
        accessible,
        args.per_stratum,
        args.max_repositories,
        args.seed,
    )
    atomic_csv(selection, repositories_path)
    atomic_csv(selected_occurrences, selected_occurrences_path)
    atomic_csv(coverage, coverage_path)

    manifest = base_manifest(Path(__file__), vars(args))
    manifest["inputs"] = [file_record(path) for path in input_paths]
    manifest["purpose"] = (
        "Technical calibration of history recovery only; this is not an "
        "inferential or confirmatory sample."
    )
    manifest["selection_rule"] = (
        "Intersection of repositories marked accessible in every supplied probe; "
        "SHA-256 seed ranking within anchor stratum; round-robin allocation; "
        "repository deduplication."
    )
    manifest["limitations"] = [
        "Probe instability makes eligibility conditional and potentially biased.",
        "Repository deduplication makes closed-form inclusion weights unavailable.",
        "No population estimates may be computed from this calibration sample.",
    ]
    manifest["results"] = {
        "stable_accessible_repositories": len(accessible),
        "available_strata": len(coverage),
        "selected_repositories": len(selection),
        "selected_occurrences": len(selected_occurrences),
        "covered_strata": int((coverage["selected_repositories"] > 0).sum()),
        "seed": args.seed,
        "per_stratum": args.per_stratum,
        "max_repositories": args.max_repositories,
    }
    manifest["outputs"] = [
        file_record(repositories_path),
        file_record(selected_occurrences_path),
        file_record(coverage_path),
    ]
    atomic_json(manifest_path, manifest)
    print(manifest["results"])
    print(f"Manifesto: {manifest_path}")


if __name__ == "__main__":
    main()
