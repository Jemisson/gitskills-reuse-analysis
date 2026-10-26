#!/usr/bin/env python3

"""Select a weighted exploratory RQ2/RQ3 sample from the accessible pilot frame."""

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
DEFAULT_OUTPUT_DIR = ROOT / "outputs" / "rq2" / "analytic_sample_v1"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--occurrences", default=str(DEFAULT_OCCURRENCES))
    parser.add_argument("--anchors", default=str(DEFAULT_ANCHORS))
    parser.add_argument("--probe-file", action="append")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--per-stratum", type=int, default=5)
    parser.add_argument("--seed", type=int, default=20261026)
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def accessible_in_all(probes: list[pd.DataFrame]) -> set[str]:
    sets = [
        set(probe.loc[probe["status"].eq("accessible"), "repo_full_name"])
        for probe in probes
    ]
    return set.intersection(*sets) if sets else set()


def random_key(seed: int, stratum: str, repository: str) -> str:
    return hashlib.sha256(
        f"{seed}\0{stratum}\0{repository}".encode("utf-8")
    ).hexdigest()


def build_repository_frame(
    occurrences: pd.DataFrame,
    anchors: pd.DataFrame,
    accessible: set[str],
    seed: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    linked = occurrences.merge(
        anchors[["anchor_file_sha", "pilot_stratum"]],
        on="anchor_file_sha",
        how="left",
        validate="many_to_one",
    )
    if linked["pilot_stratum"].isna().any():
        raise ValueError("Ocorrência sem estrato")
    eligible = linked.loc[linked["repo_full_name"].isin(accessible)].copy()
    pairs = eligible[["repo_full_name", "pilot_stratum"]].drop_duplicates()
    original_sizes = pairs.groupby("pilot_stratum").size().rename("candidate_repositories")
    pairs = pairs.merge(original_sizes, on="pilot_stratum", validate="many_to_one")
    primary = (
        pairs.sort_values(
            ["repo_full_name", "candidate_repositories", "pilot_stratum"]
        )
        .drop_duplicates("repo_full_name")
        .rename(columns={"pilot_stratum": "selection_stratum"})
    )
    primary["random_key"] = [
        random_key(seed, stratum, repository)
        for stratum, repository in zip(
            primary["selection_stratum"], primary["repo_full_name"]
        )
    ]
    primary = primary.sort_values(
        ["selection_stratum", "random_key", "repo_full_name"]
    ).reset_index(drop=True)
    primary["rank_within_stratum"] = (
        primary.groupby("selection_stratum", sort=True).cumcount() + 1
    )
    frame_sizes = primary.groupby("selection_stratum").size().rename("frame_repositories")
    primary = primary.merge(frame_sizes, on="selection_stratum", validate="many_to_one")
    return primary, eligible


def draw_sample(
    repository_frame: pd.DataFrame,
    eligible_occurrences: pd.DataFrame,
    per_stratum: int,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    selected = repository_frame.loc[
        repository_frame["rank_within_stratum"] <= per_stratum
    ].copy()
    selected["sampled_repositories_in_stratum"] = selected.groupby(
        "selection_stratum", sort=True
    )["repo_full_name"].transform("size")
    selected["selection_probability_conditional"] = (
        selected["sampled_repositories_in_stratum"] / selected["frame_repositories"]
    )
    selected["sampling_weight_conditional"] = (
        1.0 / selected["selection_probability_conditional"]
    )
    selected_repositories = set(selected["repo_full_name"])
    selected_occurrences = eligible_occurrences.loc[
        eligible_occurrences["repo_full_name"].isin(selected_repositories)
    ].merge(
        selected[
            [
                "repo_full_name",
                "selection_stratum",
                "selection_probability_conditional",
                "sampling_weight_conditional",
            ]
        ],
        on="repo_full_name",
        how="left",
        validate="many_to_one",
    )
    selected_occurrences = selected_occurrences.sort_values(
        ["selection_stratum", "repo_full_name", "anchor_file_sha", "path"]
    )
    strata = (
        repository_frame.groupby("selection_stratum", sort=True)
        .agg(frame_repositories=("repo_full_name", "size"))
        .reset_index()
    )
    sampled_counts = selected.groupby("selection_stratum").size()
    occurrence_counts = selected_occurrences.groupby("selection_stratum").size()
    strata["sampled_repositories"] = strata["selection_stratum"].map(
        sampled_counts
    ).fillna(0).astype(int)
    strata["selected_occurrences"] = strata["selection_stratum"].map(
        occurrence_counts
    ).fillna(0).astype(int)
    strata["selection_probability_conditional"] = (
        strata["sampled_repositories"] / strata["frame_repositories"]
    )
    return selected, selected_occurrences, strata


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
    if args.per_stratum < 1:
        raise ValueError("--per-stratum deve ser positivo")
    occurrences_path = Path(args.occurrences).expanduser().resolve()
    anchors_path = Path(args.anchors).expanduser().resolve()
    probe_paths = [
        Path(item).expanduser().resolve()
        for item in (args.probe_file or [str(path) for path in DEFAULT_PROBES])
    ]
    inputs = [occurrences_path, anchors_path, *probe_paths]
    if any(not path.is_file() for path in inputs):
        raise FileNotFoundError("Entrada da amostra não encontrada")
    output_dir = Path(args.output_dir).expanduser().resolve()
    frame_path = output_dir / "repository_sampling_frame.csv"
    repositories_path = output_dir / "selected_repositories.csv"
    selected_occurrences_path = output_dir / "selected_occurrences.csv"
    strata_path = output_dir / "sampling_strata.csv"
    manifest_path = output_dir / "sampling_manifest.json"
    output_dir.mkdir(parents=True, exist_ok=True)
    ensure_new_outputs(
        [frame_path, repositories_path, selected_occurrences_path, strata_path, manifest_path],
        args.overwrite,
    )

    occurrences = pd.read_csv(occurrences_path)
    anchors = pd.read_csv(anchors_path)
    probes = [pd.read_csv(path) for path in probe_paths]
    accessible = accessible_in_all(probes)
    repository_frame, eligible = build_repository_frame(
        occurrences, anchors, accessible, args.seed
    )
    selected, selected_occurrences, strata = draw_sample(
        repository_frame, eligible, args.per_stratum
    )
    atomic_csv(repository_frame, frame_path)
    atomic_csv(selected, repositories_path)
    atomic_csv(selected_occurrences, selected_occurrences_path)
    atomic_csv(strata, strata_path)

    manifest = base_manifest(Path(__file__), vars(args))
    manifest["inputs"] = [file_record(path) for path in inputs]
    manifest["estimand_scope"] = (
        "Repositories in the 55-anchor RQ2 pilot that were marked accessible in both "
        "historical anonymous probes, under deterministic primary-stratum assignment."
    )
    manifest["selection_rule"] = (
        "Assign each repository to its rarest eligible anchor stratum, breaking ties "
        "lexicographically; rank by SHA-256(seed, stratum, repository); select the "
        "first n without replacement within each assigned stratum."
    )
    manifest["results"] = {
        "stable_accessible_repositories": len(accessible),
        "repository_frame_size": len(repository_frame),
        "strata": len(strata),
        "selected_repositories": len(selected),
        "selected_occurrences": len(selected_occurrences),
        "per_stratum": args.per_stratum,
        "seed": args.seed,
    }
    manifest["limitations"] = [
        "Probabilities and weights apply only to the conditioned 603-repository frame.",
        "Historical probe instability can induce selection bias relative to GitSkills.",
        "Primary-stratum assignment is deterministic but changes the stratum estimand.",
        "This is an exploratory analytic sample, not a population-representative sample.",
    ]
    manifest["outputs"] = [
        file_record(frame_path),
        file_record(repositories_path),
        file_record(selected_occurrences_path),
        file_record(strata_path),
    ]
    atomic_json(manifest_path, manifest)
    print(manifest["results"])
    print(f"Manifesto: {manifest_path}")


if __name__ == "__main__":
    main()
