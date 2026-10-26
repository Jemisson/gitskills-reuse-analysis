# Runbook de reprodutibilidade

**Estado:** IMPLEMENTADO para as quatro transformações que estavam ausentes; validação integral depende da execução controlada descrita abaixo.

## Princípios

- Nunca escrever sobre os resultados científicos originais.
- Usar um diretório novo por execução (`run_id`).
- Manter o SQLite em modo somente leitura.
- Preservar manifestos JSON, checksums, argumentos, commit e invariantes.
- Comparar conteúdos por chaves/valores, não por ordem física de linhas.

## 1. Gerar as entradas da RQ1

```bash
cd AnaliseGitSkills

python scripts/00_build_rq1_inputs.py \
  --db ../Banco/agent_skills_release.db \
  --output-dir outputs/reproduction/<run_id>/inputs \
  --hash-database
```

O comando cria, sem sobrescrever destinos existentes:

- `reuse_by_content.csv`;
- `representative_repositories.csv`;
- `rq1_inputs_manifest.json`.

A consulta conta ocorrências com nome exato `SKILL.md` para cada hash pertencente à população principal. `reuse_count` usa repositórios distintos. O representante é a linha `dedup_primary = 1`, sem interpretação de origem.

## 2. Executar extração e preparação existentes

Os scripts históricos ainda escrevem em paths padrão. Até sua parametrização completa, execute esta fase em uma cópia de trabalho ou passe entradas/saídas onde os argumentos já existem. Não substitua os arquivos originais.

```bash
python scripts/02_extract_features.py \
  --db ../Banco/agent_skills_release.db \
  --reuse-file outputs/reproduction/<run_id>/inputs/reuse_by_content.csv \
  --output outputs/reproduction/<run_id>/rq1_features.parquet
```

As etapas seguintes aceitam paths isolados:

```bash
python scripts/03_prepare_model_data.py \
  --input outputs/reproduction/<run_id>/rq1_features.parquet \
  --output outputs/reproduction/<run_id>/rq1_model_data.parquet \
  --parameters-output outputs/reproduction/<run_id>/transformation_parameters.csv \
  --missingness-output outputs/reproduction/<run_id>/model_missingness.csv

python scripts/03b_add_representative_repository.py \
  --model-file outputs/reproduction/<run_id>/rq1_model_data.parquet \
  --repository-file outputs/reproduction/<run_id>/inputs/representative_repositories.csv \
  --output outputs/reproduction/<run_id>/rq1_model_data_with_repo.parquet
```

## 3. Exportar dados para R e registrar megarepositórios

```bash
python scripts/03c_export_model_data_for_r.py \
  --input outputs/rq1/rq1_model_data_with_repo.parquet \
  --output-dir outputs/reproduction/<run_id>/r_export \
  --mega-threshold 5000
```

São produzidos o CSV completo, o CSV sem repositórios com mais de 5.000 linhas, a lista explícita de exclusões e um manifesto.

## 4. Ajustar o modelo principal

```bash
Rscript scripts/04d_fit_two_part_clustered.R \
  outputs/reproduction/<run_id>/r_export/rq1_model_data_for_r.csv \
  outputs/reproduction/<run_id>/models/two_part_clustered
```

Os scripts R agora registram `session_info.txt`. As versões usadas na análise auditada também foram congeladas em `AnaliseGitSkills/renv.lock`.

## 5. Aplicar FDR

```bash
python scripts/04f_apply_fdr.py \
  --input outputs/reproduction/<run_id>/models/two_part_clustered/two_part_coefficients_cluster_robust.csv \
  --output-dir outputs/reproduction/<run_id>/fdr
```

Benjamini–Hochberg é aplicado separadamente aos componentes `reuse_probability` e `positive_reuse_intensity`.

## 6. Testes rápidos

```bash
cd AnaliseGitSkills
python -m unittest discover -s tests -v
```

## Critérios de equivalência com os resultados existentes

- 1.586.188 hashes na população;
- 3.347.020 ocorrências;
- 2.737.824 presenças conteúdo–repositório;
- 1.584.628 linhas no modelo;
- 253.660 linhas reutilizadas no modelo;
- 218.408 repositórios representantes no modelo;
- 16 repositórios removidos por `model_rows > 5000`;
- 183.623 linhas removidas e 1.401.005 preservadas;
- 74 coeficientes no modelo principal, 37 por componente;
- valores BH numericamente equivalentes aos resultados existentes, dentro de tolerância definida antes da execução.

## Pendências explícitas

1. Adicionar orquestrador que capture comandos, stdout/stderr e código de saída.
2. Definir distribuição/checksum oficial do snapshot SQLite; o checksum local está em `AnaliseGitSkills/data_manifest.json`.
3. Executar novamente os modelos R completos em diretório novo e comparar objetos, coeficientes e figuras.
4. Acrescentar testes de integração do pipeline completo a uma fixture SQLite/Parquet pequena.
