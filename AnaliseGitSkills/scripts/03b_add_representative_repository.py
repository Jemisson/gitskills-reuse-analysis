#!/usr/bin/env python3

from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]

MODEL_FILE = (
    ROOT / "outputs" / "rq1" / "rq1_model_data.parquet"
)

REPOSITORY_FILE = (
    ROOT
    / "outputs"
    / "rq1"
    / "representative_repositories.csv"
)

OUTPUT_FILE = (
    ROOT
    / "outputs"
    / "rq1"
    / "rq1_model_data_with_repo.parquet"
)


def main():
    print("Lendo dataset do modelo...")
    model = pd.read_parquet(MODEL_FILE)

    print("Lendo repositórios representantes...")
    repositories = pd.read_csv(
        REPOSITORY_FILE,
        dtype={
            "file_sha": "string",
            "representative_repository": "string",
        },
    )

    if repositories["file_sha"].duplicated().any():
        raise ValueError(
            "Há hashes duplicados no arquivo de repositórios."
        )

    merged = model.merge(
        repositories,
        on="file_sha",
        how="left",
        validate="one_to_one",
    )

    missing = merged[
        "representative_repository"
    ].isna().sum()

    if missing:
        raise ValueError(
            f"Repositórios ausentes após junção: {missing}"
        )

    if len(merged) != len(model):
        raise ValueError(
            "A junção alterou a quantidade de registros."
        )

    merged.to_parquet(
        OUTPUT_FILE,
        index=False,
        compression="zstd",
    )

    print(f"Registros: {len(merged):,}")
    print(
        "Repositórios distintos: "
        f"{merged['representative_repository'].nunique():,}"
    )
    print(f"Arquivo salvo em: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
