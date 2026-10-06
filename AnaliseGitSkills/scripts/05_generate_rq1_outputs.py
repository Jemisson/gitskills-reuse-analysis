#!/usr/bin/env python3

from pathlib import Path

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


BASE = Path("outputs/rq1")

MAIN_FILE = (
    BASE
    / "models_full"
    / "two_part_clustered"
    / "two_part_coefficients_cluster_robust_fdr.csv"
)

NO_MEGA_FILE = (
    BASE
    / "sensitivity"
    / "no_mega_repos"
    / "two_part_coefficients_cluster_robust.csv"
)

TAIL_FILE = (
    BASE
    / "sensitivity"
    / "tail_p99_5"
    / "two_part_coefficients_cluster_robust.csv"
)

OUTPUT_DIR = BASE / "final"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


TERM_ORDER = [
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
]

TERM_LABELS = {
    "z_log_text_length": "Tamanho do texto",
    "z_log_description_length": "Tamanho da descrição",
    "z_readability_flesch_english": "Legibilidade Flesch",
    "z_log_url_count": "Quantidade de URLs",
    "z_log_code_block_count": "Blocos de código",
    "z_log_heading_count": "Cabeçalhos",
    "z_log_list_item_count": "Itens de lista",
    "has_scripts": "Possui scripts",
    "has_references": "Possui referências",
    "z_log_sibling_count": "Arquivos irmãos",
    "z_log_repo_stars": "Estrelas do repositório",
    "z_log_repo_age_days": "Idade do repositório",
    "z_log_repo_inactivity_days": "Inatividade do repositório",
}

COMPONENT_LABELS = {
    "reuse_probability": "Probabilidade de reúso",
    "positive_reuse_intensity": "Intensidade do reúso",
}


def carregar_dados():
    principal = pd.read_csv(MAIN_FILE)
    sem_mega = pd.read_csv(NO_MEGA_FILE)
    cauda = pd.read_csv(TAIL_FILE)
    return principal, sem_mega, cauda


def preparar_efeitos_principais(principal):
    efeitos = principal[
        principal["term"].isin(TERM_ORDER)
    ].copy()

    efeitos["term_label"] = efeitos["term"].map(TERM_LABELS)
    efeitos["component_label"] = efeitos["component"].map(
        COMPONENT_LABELS
    )

    efeitos["term_order"] = efeitos["term"].map(
        {term: i for i, term in enumerate(TERM_ORDER)}
    )

    efeitos = efeitos.sort_values(
        ["component", "term_order"]
    )

    colunas = [
        "component",
        "component_label",
        "term",
        "term_label",
        "coefficient",
        "standard_error",
        "effect_ratio",
        "effect_ratio_low",
        "effect_ratio_high",
        "p_value",
        "q_value_bh",
        "significant_fdr_05",
    ]

    efeitos[colunas].to_csv(
        OUTPUT_DIR / "rq1_main_effects.csv",
        index=False,
    )

    return efeitos


def gerar_grafico(efeitos):
    componentes = [
        "reuse_probability",
        "positive_reuse_intensity",
    ]

    fig, axes = plt.subplots(
        1,
        2,
        figsize=(15, 9),
        sharey=True,
    )

    for ax, componente in zip(axes, componentes):
        dados = efeitos[
            efeitos["component"] == componente
        ].copy()

        dados = (
            dados.set_index("term")
            .reindex(TERM_ORDER)
            .reset_index()
        )

        y = np.arange(len(dados))

        for posicao, linha in dados.iterrows():
            significativo = bool(linha["significant_fdr_05"])
            cor = "#1565C0" if significativo else "#9E9E9E"
            marcador = "o" if significativo else "s"

            erro_inferior = (
                linha["effect_ratio"]
                - linha["effect_ratio_low"]
            )

            erro_superior = (
                linha["effect_ratio_high"]
                - linha["effect_ratio"]
            )

            ax.errorbar(
                linha["effect_ratio"],
                posicao,
                xerr=np.array(
                    [[erro_inferior], [erro_superior]]
                ),
                fmt=marcador,
                color=cor,
                ecolor=cor,
                capsize=4,
                markersize=7,
                linewidth=1.7,
            )

        ax.axvline(
            1,
            color="#424242",
            linestyle="--",
            linewidth=1,
        )

        ax.set_xscale("log")
        ax.set_xlabel("Razão de efeito e IC de 95%")
        ax.set_title(COMPONENT_LABELS[componente])
        ax.grid(
            axis="x",
            linestyle=":",
            alpha=0.35,
        )

        ax.set_yticks(y)
        ax.set_yticklabels(
            [TERM_LABELS[t] for t in TERM_ORDER]
        )
        ax.invert_yaxis()

    fig.suptitle(
        "RQ1 — Características associadas ao reúso de Agent Skills",
        fontsize=16,
        fontweight="bold",
    )

    fig.text(
        0.5,
        0.02,
        (
            "Azul: significativo após correção FDR "
            "(Benjamini–Hochberg); cinza: não significativo. "
            "Erros-padrão agrupados por repositório."
        ),
        ha="center",
        fontsize=10,
    )

    plt.tight_layout(rect=[0, 0.05, 1, 0.95])

    fig.savefig(
        OUTPUT_DIR / "rq1_effects_forest_plot.png",
        dpi=300,
        bbox_inches="tight",
    )

    plt.close(fig)


def gerar_comparacao_sensibilidade(
    principal,
    sem_mega,
    cauda,
):
    colunas_base = [
        "component",
        "term",
        "coefficient",
        "effect_ratio",
        "p_value",
    ]

    principal = principal[colunas_base + ["q_value_bh"]].copy()

    sem_mega = sem_mega[colunas_base].copy().rename(
        columns={
            "coefficient": "coefficient_no_mega",
            "effect_ratio": "effect_ratio_no_mega",
            "p_value": "p_value_no_mega",
        }
    )

    cauda = cauda[colunas_base].copy().rename(
        columns={
            "coefficient": "coefficient_tail",
            "effect_ratio": "effect_ratio_tail",
            "p_value": "p_value_tail",
        }
    )

    comparacao = principal.merge(
        sem_mega,
        on=["component", "term"],
        how="left",
        suffixes=("_main", ""),
    )

    comparacao = comparacao.merge(
        cauda,
        on=["component", "term"],
        how="left",
    )

    comparacao["direction_equal_no_mega"] = (
        np.sign(comparacao["coefficient"])
        == np.sign(comparacao["coefficient_no_mega"])
    )

    comparacao["direction_equal_tail"] = (
        np.sign(comparacao["coefficient"])
        == np.sign(comparacao["coefficient_tail"])
    )

    comparacao[
        comparacao["term"].isin(TERM_ORDER)
    ].to_csv(
        OUTPUT_DIR / "rq1_sensitivity_comparison.csv",
        index=False,
    )


def gerar_tabela_contextual(principal):
    mascara = (
        principal["term"].str.startswith("repo_language_group")
        | principal["term"].str.startswith("location_class")
    )

    principal[mascara].to_csv(
        OUTPUT_DIR / "rq1_contextual_effects.csv",
        index=False,
    )


def main():
    principal, sem_mega, cauda = carregar_dados()

    efeitos = preparar_efeitos_principais(principal)
    gerar_grafico(efeitos)

    gerar_comparacao_sensibilidade(
        principal,
        sem_mega,
        cauda,
    )

    gerar_tabela_contextual(principal)

    print("Arquivos gerados:")
    for arquivo in sorted(OUTPUT_DIR.iterdir()):
        print(f"- {arquivo.resolve()}")


if __name__ == "__main__":
    main()
