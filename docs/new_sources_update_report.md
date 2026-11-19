# Relatório de atualização do artigo com novas fontes

## Resultado

O manuscrito foi ampliado de 5 para 6 páginas. A introdução agora explicita o mecanismo de cópia sem registro central, separa identidade, similaridade, evolução, ancestralidade e propagação, e delimita o caráter condicionado da evidência longitudinal. Related Work foi reorganizado em quatro subseções: Agent Skills como artefatos de software; reúso, clones e genealogias; evolução e propagação; e mudanças comportamentais/de segurança.

## Fontes

- Preservadas e recontextualizadas: `gitskills`, `agentskills-spec`, `authoring-skills`, `krinke2007` e `bettenburg2012`.
- Adicionadas: `devgpt2024`, `grewal2024`, `sousa2026genealogy`, `uchoa2026lifecycle`, `ogenrwot2026`, `agarwal2026`, `fu2025security` e `berretta2025`.
- Rejeitadas: nenhuma das fontes fornecidas foi totalmente rejeitada; `berretta2025` foi usada somente como contraste com um ecossistema de dependências explícitas, e `fu2025security` somente como motivação cautelosa.
- Pendências: as versões fornecidas de `fu2025security` e `grewal2024` exibiam DOI placeholder no PDF. Para Grewal et al., o DOI editorial foi confirmado como `10.1145/3643991.3645072`; Fu et al. permaneceu citado pelo identificador arXiv verificável. Os trabalhos de Ogenrwot/Businge e Agarwal et al. também foram citados pelas versões arXiv fornecidas.

A rastreabilidade detalhada está em `docs/new_sources_evidence_matrix.md`.

## Figuras da RQ3

O script `AnaliseGitSkills/scripts/24_generate_boxplots.py` lê 75 observações individuais de `AnaliseGitSkills/outputs/rq3/association_dataset_v2/rq3_association_events.csv` e gera:

- linhas alteradas por operação;
- dias desde a versão de referência por operação.

Ambos usam transformação `log1p`, caixas com mediana e Q1/Q3, whiskers de 1,5 IQR e pontos individuais com jitter determinístico (`seed=20261026`). As contagens são: 27 adições, 24 modificações, 19 movimentos e 5 remoções, em 18 repositórios. As figuras não são ponderadas e não pressupõem independência entre eventos.

Após comparar a relevância das figuras, o artigo passou a apresentar duas visualizações complementares. Na RQ2, o boxplot de linhas alteradas caracteriza magnitude, dispersão e observações individuais por operação. Na RQ3, a figura de sensibilidade responde diretamente à pergunta de pesquisa ao mostrar a sobreposição entre as definições estrita e ampla. O boxplot temporal permanece como artefato suplementar.

Arquivos gerados em `IEEE_Conference_Template/figures/`:

- `boxplot_rq3_changed_lines_by_operation.png` e `.pdf` (inserido na RQ2);
- `boxplot_rq3_days_since_reference_version_by_operation.png` e `.pdf`;
- `rq3_boxplots_manifest.json`.
- `figure_rq3_scenario_sensitivity.png` (figura inserida na RQ3).

## Validação

- Compilação: `latexmk -pdf -interaction=nonstopmode -halt-on-error gitskills_paper.tex`.
- Resultado: PDF IEEE em formato letter, 6 páginas, sem citações ou referências indefinidas.
- Bibliografia: 13 chaves citadas e 13 `\bibitem`; nenhuma chave ausente e nenhuma entrada não citada.
- Figuras: referência e arquivo conferidos; PNGs a 300 dpi e PDFs vetoriais gerados.
- Script: compilação Python e execução adicional em diretório temporário concluídas.
- Testes: 32 testes existentes executados com sucesso.
- Inspeção visual: as seis páginas, a figura de sensibilidade e os dois boxplots suplementares foram renderizados e conferidos.

## Comandos de reprodução

```bash
python AnaliseGitSkills/scripts/24_generate_boxplots.py
python AnaliseGitSkills/scripts/23_generate_rq3_article_artifacts.py

cd IEEE_Conference_Template
latexmk -pdf -interaction=nonstopmode -halt-on-error gitskills_paper.tex
```

O ambiente Python deve conter as dependências registradas em `AnaliseGitSkills/requirements.txt`.

## Limitações preservadas

- RQ1 permanece populacional e associativa; não há inferência causal.
- RQ2/RQ3 permanecem exploratórias e condicionadas a acesso e casos completos.
- A taxa de propagação permanece não estimável.
- Um patch idêntico e precedência temporal não demonstram transmissão.
- Candidatos automatizados não demonstram execução ou validade semântica.
- As figuras da RQ3 descrevem a amostra condicionada e não a população do GitHub.
