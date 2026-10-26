#!/usr/bin/env python3

import argparse
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


def parse_args():
    parser = argparse.ArgumentParser(
        description="Associa cada conteúdo ao repositório representante."
    )
    parser.add_argument("--model-file", default=str(MODEL_FILE))
    parser.add_argument(
        "--repository-file", default=str(REPOSITORY_FILE)
    )
    parser.add_argument("--output", default=str(OUTPUT_FILE))
    return parser.parse_args()


def main():
    args = parse_args()
    model_file = Path(args.model_file).expanduser().resolve()
    repository_file = Path(args.repository_file).expanduser().resolve()
    output_file = Path(args.output).expanduser().resolve()
    output_file.parent.mkdir(parents=True, exist_ok=True)

    print("Lendo dataset do modelo...")
    model = pd.read_parquet(model_file)

    print("Lendo repositórios representantes...")
    repositories = pd.read_csv(
        repository_file,
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
        output_file,
        index=False,
        compression="zstd",
    )

    print(f"Registros: {len(merged):,}")
    print(
        "Repositórios distintos: "
        f"{merged['representative_repository'].nunique():,}"
    )
    print(f"Arquivo salvo em: {output_file}")


if __name__ == "__main__":
    main()
