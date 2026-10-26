#!/usr/bin/env python3

"""Export the RQ1 model parquet and the no-megarepository sensitivity CSV."""

from __future__ import annotations

import argparse
import os
import time
from pathlib import Path

import pandas as pd

from _provenance import atomic_json, base_manifest, ensure_new_outputs, file_record


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "outputs" / "rq1" / "rq1_model_data_with_repo.parquet"
DEFAULT_OUTPUT_DIR = ROOT / "outputs" / "rq1" / "reproduced_exports"

MODEL_COLUMNS = [
    "is_reused",
    "extra_reuse",
    "location_class",
    "repo_language_group",
    "z_log_text_length",
    "z_log_description_length",
    "z_readability_flesch_english",
    "z_log_url_count",
    "z_log_code_block_count",
    "z_log_heading_count",
    "z_log_list_item_count",
    "has_scripts",
    "has_references",
    "z_log_sibling_count",
    "z_log_repo_stars",
    "z_log_repo_age_days",
    "z_log_repo_inactivity_days",
    "composition_truncated",
    "representative_repository",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default=str(DEFAULT_INPUT))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--mega-threshold", type=int, default=5_000)
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def atomic_csv(frame: pd.DataFrame, path: Path) -> None:
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        frame.to_csv(temporary, index=False)
        with temporary.open("rb") as source:
            os.fsync(source.fileno())
        temporary.replace(path)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise


def main() -> None:
    args = parse_args()
    if args.mega_threshold < 1:
        raise ValueError("--mega-threshold deve ser positivo")

    input_path = Path(args.input).expanduser().resolve()
    output_dir = Path(args.output_dir).expanduser().resolve()
    full_path = output_dir / "rq1_model_data_for_r.csv"
    no_mega_path = output_dir / "rq1_model_data_for_r_no_mega_repos.csv"
    excluded_path = output_dir / "excluded_mega_repositories.csv"
    manifest_path = output_dir / "rq1_r_export_manifest.json"

    if not input_path.is_file():
        raise FileNotFoundError(input_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    ensure_new_outputs(
        [full_path, no_mega_path, excluded_path, manifest_path], args.overwrite
    )

    started = time.monotonic()
    frame = pd.read_parquet(input_path, columns=MODEL_COLUMNS)
    if frame.isna().any().any():
        raise ValueError("O dataset contém valores ausentes nas colunas exportadas")

    repository_counts = frame["representative_repository"].value_counts()
    mega = repository_counts[repository_counts > args.mega_threshold].rename(
        "model_rows"
    )
    mega_frame = mega.rename_axis("representative_repository").reset_index()
    without_mega = frame.loc[
        ~frame["representative_repository"].isin(mega.index)
    ].copy()

    atomic_csv(frame, full_path)
    atomic_csv(without_mega, no_mega_path)
    atomic_csv(mega_frame, excluded_path)

    manifest = base_manifest(Path(__file__), vars(args))
    manifest["input"] = file_record(input_path)
    manifest["columns"] = MODEL_COLUMNS
    manifest["invariants"] = {
        "full_rows": len(frame),
        "positive_rows": int(frame["is_reused"].sum()),
        "unique_representative_repositories": int(
            frame["representative_repository"].nunique()
        ),
        "mega_threshold_strictly_greater_than": args.mega_threshold,
        "excluded_repositories": len(mega),
        "excluded_rows": int(mega.sum()),
        "no_mega_rows": len(without_mega),
        "partition_rows_equal": len(frame) == len(without_mega) + int(mega.sum()),
    }
    manifest["outputs"] = [
        file_record(full_path),
        file_record(no_mega_path),
        file_record(excluded_path),
    ]
    manifest["elapsed_seconds"] = time.monotonic() - started
    atomic_json(manifest_path, manifest)
    print(manifest["invariants"])
    print(f"Manifesto: {manifest_path}")


if __name__ == "__main__":
    main()

