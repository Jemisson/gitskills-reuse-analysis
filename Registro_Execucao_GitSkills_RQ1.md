# Registro de execução da pesquisa GitSkills

## Da cópia à divergência: reutilização, propagação e evolução de Agent Skills no GitHub

**Projeto:** Tópicos em Engenharia de Sistemas de Software II  
**Pesquisador:** Jemison dos Santos  
**Dataset:** GitSkills - `agent_skills_release.db`  
**Snapshot dos dados:** julho de 2026  
**Data deste registro:** 1º de outubro de 2026

---

## 1. Objetivo desta etapa

O trabalho foi iniciado pela Fase 1 do projeto, correspondente à preparação do dataset e à caracterização populacional necessária para responder à RQ1:

> Como a reutilização está distribuída e quais características textuais, estruturais e contextuais estão associadas à ampla propagação?

Nesta etapa, foram executadas as seguintes atividades:

1. auditoria estrutural do banco SQLite;
2. definição da população principal;
3. medição da distribuição do reúso;
4. geração de estatísticas descritivas e gráficos;
5. extração de métricas textuais, estruturais e contextuais;
6. preparação do dataset estatístico;
7. diagnóstico de multicolinearidade;
8. implementação e teste inicial do hurdle model;
9. identificação de um problema numérico na binomial negativa truncada.

---

## 2. Ambiente utilizado

- Sistema operacional: Ubuntu 24.04
- SQLite: 3.45.1, 64 bits
- Python: 3.12.3
- Banco original: `agent_skills_release.db`
- Tamanho do banco: 42 GB
- Espaço livre verificado antes das extrações: 502 GB
- Memória RAM: 31 GiB
- Memória disponível no momento da verificação: 22 GiB
- Swap: 8 GiB

O banco original permaneceu em modo somente leitura durante as consultas.

---

## 3. Organização dos diretórios

Foi criado o diretório:

```text
/home/james/Documents/Doutorado/TESSII/Trabalho/AnaliseGitSkills
```

Com a seguinte estrutura:

```text
AnaliseGitSkills/
├── .venv/
├── annotations/
├── logs/
├── outputs/
│   ├── audit/
│   ├── rq1/
│   ├── rq2/
│   ├── rq3/
│   └── validation/
├── reports/
├── samples/
├── scripts/
└── requirements.txt
```

O esquema do banco foi preservado em:

```text
outputs/audit/database_schema.sql
```

---

## 4. Auditoria estrutural do banco

### 4.1 Tabelas encontradas

O comando de listagem confirmou quatro tabelas:

```text
artifact_siblings
artifacts
mining_runs
repos
```

### 4.2 Tabela `artifacts`

A tabela possui uma linha por ocorrência descoberta, com chave primária composta por:

```text
(repo_full_name, path)
```

As colunas relevantes incluem:

- `repo_full_name`;
- `path`;
- `filename`;
- `location_class`;
- `file_sha`;
- `content`;
- `content_fetched`;
- `frontmatter_valid`;
- `name`;
- `description`;
- `body_chars`;
- `history_fetched`;
- `composition_fetched`;
- `dedup_primary`;
- `first_commit_at`;
- `last_commit_at`;
- `commit_count`;
- `sibling_count`;
- `sibling_bytes`;
- `has_scripts`;
- `has_references`;
- `content_sha_ok`;
- `composition_truncated`.

Existem índices para `file_sha` e `repo_full_name`.

### 4.3 Tabela `repos`

A tabela possui metadados dos repositórios:

- `full_name`;
- `owner`;
- `stars`;
- `forks`;
- `is_fork`;
- `language`;
- `license`;
- `description`;
- `created_at`;
- `pushed_at`;
- `metadata_fetched`.

A junção correta é:

```text
artifacts.repo_full_name = repos.full_name
```

### 4.4 Tabela `artifact_siblings`

Registra arquivos e diretórios associados a cada skill, incluindo nome, tipo, tamanho, hash e conteúdo, quando coletado.

### 4.5 Tabela `mining_runs`

Registra as execuções de descoberta realizadas em julho de 2026. Algumas execuções foram interrompidas e encerradas posteriormente pelo processo `repair-runs`. Como a coleta utilizava checkpoints, esse fato não invalida automaticamente os dados, mas deve ser documentado como aspecto de procedência e possível ameaça à validade.

---

## 5. Auditoria da qualidade dos registros

### 5.1 Resultados gerais de `artifacts`

| Indicador | Quantidade |
|---|---:|
| Ocorrências totais | 3.797.117 |
| Nome exatamente igual a `SKILL.md` | 3.742.828 |
| Conteúdo obtido | 1.880.348 |
| Hash do conteúdo validado | 1.853.479 |
| Front matter válido | 1.627.753 |
| Representantes (`dedup_primary = 1`) | 1.877.981 |

### 5.2 Representantes de conteúdos distintos

| Indicador | Quantidade |
|---|---:|
| Total de representantes | 1.877.981 |
| Representantes com nome exato `SKILL.md` | 1.842.600 |
| Representantes com conteúdo obtido | 1.877.981 |
| Representantes com hash validado | 1.851.135 |
| Representantes com front matter válido | 1.625.701 |
| População principal | 1.586.188 |

### 5.3 Definição da população principal

A população principal da RQ1 foi definida por conteúdos que atendem simultaneamente aos critérios:

```sql
dedup_primary = 1
AND filename = 'SKILL.md'
AND content_fetched = 1
AND content_sha_ok = 1
AND frontmatter_valid = 1
```

Resultado:

```text
1.586.188 conteúdos distintos
```

Os registros excluídos não foram apagados. Eles poderão ser utilizados em testes de sensibilidade com critérios menos restritivos.

### 5.4 Consistência da deduplicação

Foi verificado se cada `file_sha` possuía exatamente um representante.

| Resultado | Quantidade |
|---|---:|
| Hashes distintos | 1.877.981 |
| Hashes com exatamente um representante | 1.877.981 |
| Hashes sem representante | 0 |
| Hashes com múltiplos representantes | 0 |

Conclusão: o mecanismo de deduplicação está consistente.

---

## 6. Cobertura dos metadados dos repositórios

| Indicador | Quantidade |
|---|---:|
| Repositórios | 282.200 |
| Metadados coletados | 282.200 |
| Com estrelas | 281.685 |
| Com linguagem principal | 252.084 |
| Com data de criação | 281.685 |
| Com data do último push | 281.685 |

Na população principal:

| Indicador | Quantidade |
|---|---:|
| Conteúdos | 1.586.188 |
| Com repositório correspondente | 1.586.188 |
| Com estrelas | 1.585.497 |
| Com linguagem | 1.453.179 |
| Com data de criação | 1.585.497 |

A ausência de linguagem foi convertida em categoria `Unknown`, em vez de causar exclusão automática.

---

## 7. Cobertura de composição e histórico

Na população principal:

| Indicador | Quantidade | Percentual aproximado |
|---|---:|---:|
| Com histórico resumido | 390.702 | 24,64% |
| Com contagem de commits | 390.702 | 24,64% |
| Com composição coletada | 1.584.858 | 99,92% |
| Com scripts | 189.260 | 11,93% |
| Com referências | 423.026 | 26,67% |
| Com composição truncada | 160.767 | 10,14% |

Decisão metodológica:

- a composição possui cobertura suficiente para a RQ1;
- o histórico resumido não será usado como requisito do modelo principal;
- RQ2 e RQ3 exigirão amostragem e recuperação do histórico Git completo, conforme previsto na proposta.

---

## 8. Definição e medição do reúso

A unidade de análise é um conteúdo distinto, identificado por `file_sha`.

A variável de reúso foi definida como:

```text
reuse_count = número de repositórios distintos que contêm o mesmo file_sha
```

Foram consideradas somente ocorrências cujo nome é exatamente `SKILL.md`.

Também foram derivadas:

```text
is_reused = 1 quando reuse_count > 1
extra_reuse = reuse_count - 1
```

Foi gerado o arquivo:

```text
outputs/rq1/reuse_by_content.csv
```

Ele contém 1.586.188 registros, além do cabeçalho, com as colunas:

```text
file_sha, occurrence_count, reuse_count
```

Tamanho aproximado: 70 MB.

---

## 9. Resultados descritivos preliminares da RQ1

### 9.1 Distribuição geral

| Métrica | Resultado |
|---|---:|
| Conteúdos analisados | 1.586.188 |
| Conteúdos presentes em somente um repositório | 1.332.110 |
| Conteúdos reutilizados | 254.078 |
| Percentual de conteúdos reutilizados | 16,0182% |
| Total de ocorrências | 3.347.020 |
| Presenças conteúdo-repositório | 2.737.824 |
| Reúsos além da primeira presença | 1.151.636 |
| Percentual de presenças adicionais | 42,0639% |
| Média de repositórios por conteúdo | 1,7260 |
| Mediana | 1 |
| Desvio-padrão | 5,2402 |
| Máximo de repositórios | 937 |
| Coeficiente de Gini | 0,3978 |

### 9.2 Faixas de reúso

| Repositórios | Conteúdos | Percentual |
|---|---:|---:|
| 1 | 1.332.110 | 83,9818% |
| 2 | 130.297 | 8,2145% |
| 3 a 5 | 79.500 | 5,0120% |
| 6 a 10 | 22.187 | 1,3988% |
| 11 a 50 | 18.281 | 1,1525% |
| 51 a 100 | 3.347 | 0,2110% |
| Mais de 100 | 466 | 0,0294% |

### 9.3 Percentis

| Percentil | `reuse_count` |
|---|---:|
| P50 | 1 |
| P75 | 1 |
| P90 | 2 |
| P95 | 3 |
| P99 | 15 |
| P99,5 | 29 |
| P99,9 | 65 |

### 9.4 Concentração

| Grupo | Participação nas presenças | Participação no reúso adicional |
|---|---:|---:|
| 10 conteúdos mais reutilizados | 0,2476% | 0,5877% |
| 100 conteúdos mais reutilizados | 1,1520% | 2,7300% |
| 1.000 conteúdos mais reutilizados | 4,6032% | 10,8565% |

Interpretação preliminar: o reúso é minoritário quando observado por conteúdo distinto, mas representa parcela substancial das presenças em repositórios. A distribuição é assimétrica e apresenta cauda longa. Existe concentração no topo, mas ela se distribui por centenas ou milhares de conteúdos, não apenas por poucos casos extremos.

---

## 10. Conteúdos mais reutilizados

Foi gerado:

```text
outputs/rq1/top_100_reused_detailed.csv
```

Os dez primeiros incluem:

| `reuse_count` | Ocorrências | Nome |
|---:|---:|---|
| 937 | 1.231 | `frontend-design` |
| 912 | 1.248 | `verification-before-completion` |
| 777 | 1.172 | `webapp-testing` |
| 658 | 1.406 | `pdf` |
| 655 | 884 | `systematic-debugging` |
| 583 | 794 | `receiving-code-review` |
| 573 | 617 | `fastapi` |
| 570 | 771 | `test-driven-development` |
| 560 | 715 | `pptx` |
| 553 | 743 | `mcp-builder` |

Alguns conteúdos possuem mais ocorrências do que repositórios, indicando cópias repetidas dentro do mesmo repositório.

O repositório representante foi selecionado pelo pipeline do dataset e não pode ser interpretado como autor ou origem comprovada da skill.

---

## 11. Ambiente Python e dependências

Foi criado e ativado o ambiente virtual:

```text
.venv
```

As dependências foram instaladas e registradas em:

```text
requirements.txt
```

Principais bibliotecas:

- pandas;
- numpy;
- scipy;
- matplotlib;
- seaborn;
- pyarrow;
- statsmodels;
- pyyaml.

---

## 12. Scripts produzidos

### 12.1 `scripts/01_descriptive_reuse.py`

Responsável por:

- validar `reuse_by_content.csv`;
- calcular estatísticas descritivas;
- calcular percentis;
- calcular o coeficiente de Gini;
- medir concentração no top 10, top 100 e top 1.000;
- gerar tabela de faixas;
- gerar ranking dos 100 conteúdos mais reutilizados;
- gerar gráficos.

Arquivos produzidos:

```text
outputs/rq1/descriptive_summary.csv
outputs/rq1/descriptive_summary.json
outputs/rq1/reuse_percentiles.csv
outputs/rq1/reuse_ranges.csv
outputs/rq1/reuse_concentration.csv
outputs/rq1/top_100_reused.csv
outputs/rq1/reuse_ranges.png
outputs/rq1/reuse_ccdf_loglog.png
```

### 12.2 `scripts/02_extract_features.py`

Responsável pela extração em lotes de métricas textuais, estruturais e contextuais.

Foram extraídas 34 variáveis, incluindo:

- tamanho do texto;
- número de palavras e linhas;
- tamanho da descrição e do nome;
- URLs;
- blocos de código;
- código inline;
- títulos;
- itens de lista;
- legibilidade Flesch exploratória;
- localização;
- siblings;
- scripts e referências;
- histórico resumido;
- estrelas, forks, linguagem e datas do repositório.

O teste inicial com `LIMIT 1000` mostrou textos pequenos porque os primeiros registros físicos do banco não eram uma amostra aleatória. Na população completa:

| Métrica de `body_chars` | Resultado |
|---|---:|
| Mínimo | 0 |
| Média | 7.119,59 |
| Máximo | 344.218 |
| Corpo vazio | 46 |
| Pelo menos 1.000 caracteres | 1.424.429 |

A extração completa processou 1.586.188 conteúdos em aproximadamente 54 minutos e 50 segundos.

Arquivo produzido:

```text
outputs/rq1/rq1_features.parquet
```

Validação:

- 1.586.188 linhas;
- 34 colunas;
- 318 row groups;
- nenhum hash duplicado;
- nenhuma inconsistência entre `reuse_count`, `is_reused` e `extra_reuse`;
- nenhum `reuse_count` maior que `occurrence_count`;
- nenhum texto menor que `body_chars`.

### 12.3 `scripts/03_prepare_model_data.py`

Responsável por:

- selecionar as variáveis do modelo;
- calcular idade e inatividade do repositório;
- usar 22 de julho de 2026 como data de referência;
- agrupar linguagens menos frequentes em `Other`;
- preservar `Unknown`;
- aplicar `log1p` a contagens e tamanhos;
- limitar valores extremos nos percentis 0,5% e 99,5%;
- padronizar variáveis contínuas;
- gerar relatório de valores ausentes.

Foram removidos apenas 1.560 registros incompletos.

Resultado:

```text
1.584.628 registros no modelo principal
```

Arquivos produzidos:

```text
outputs/rq1/rq1_model_data.parquet
outputs/rq1/transformation_parameters.csv
outputs/rq1/model_missingness.csv
```

### 12.4 `scripts/03b_add_representative_repository.py`

Foi criado o arquivo:

```text
outputs/rq1/representative_repositories.csv
```

Depois, o identificador do repositório representante foi incorporado ao dataset estatístico.

Resultado:

- 1.584.628 registros;
- 218.408 repositórios representantes distintos.

Arquivo produzido:

```text
outputs/rq1/rq1_model_data_with_repo.parquet
```

### 12.5 `scripts/04_fit_hurdle_model.py`

Implementa:

1. regressão logística para `P(extra_reuse > 0)`;
2. binomial negativa truncada em zero para `extra_reuse`, entre conteúdos reutilizados;
3. erros-padrão robustos HC1;
4. odds ratios e incidence rate ratios;
5. intervalos de confiança de 95%;
6. arquivos de coeficientes, resumos e metadados.

---

## 13. Valores ausentes no dataset de métricas

| Variável ou grupo | Ausentes | Percentual |
|---|---:|---:|
| Métricas textuais principais | 0 | 0% |
| Métricas de composição | 1.330 | 0,0838% |
| Histórico e datas de commit | 1.195.486 | 75,3685% |
| Metadados contextuais do repositório | 691 | 0,0436% |

Decisão:

- histórico não entra no modelo principal;
- será analisado em modelo secundário restrito ao subconjunto com histórico;
- ausências residuais de composição e repositório foram removidas do dataset principal.

---

## 14. Categorias contextuais

### 14.1 Localização

| Categoria | Quantidade |
|---|---:|
| `skills-dir` | 884.381 |
| `other` | 463.556 |
| `canonical` | 238.251 |

### 14.2 Linguagens mais frequentes

Foram identificadas 279 linguagens. As principais incluem:

| Linguagem | Quantidade |
|---|---:|
| Python | 611.471 |
| TypeScript | 276.343 |
| Unknown | 133.009 |
| JavaScript | 132.355 |
| Shell | 117.257 |
| HTML | 95.998 |
| Rust | 30.884 |
| Go | 29.066 |
| C# | 21.960 |

As 20 linguagens mais frequentes foram preservadas; as demais foram agrupadas em `Other`.

---

## 15. Outliers e transformações

Foram detectadas caudas extremas, por exemplo:

| Variável | Mediana | P99,5 | Máximo |
|---|---:|---:|---:|
| `text_length` | 5.316 | 53.879 | 344.762 |
| `url_count` | 0 | 26 | 2.242 |
| `code_block_count` | 2 | 44 | 831 |
| `sibling_count` | 0 | 82 | 41.130 |
| `sibling_bytes` | 0 | 1.730.527 | 2.059.840.648 |
| `repo_stars` | 1 | 2.866 | 383.040 |

Decisões:

- aplicação de `log1p` a tamanhos e contagens;
- winsorização entre P0,5 e P99,5;
- padronização das variáveis transformadas;
- preservação dos dados originais;
- futuras análises de robustez sem outliers extremos.

A legibilidade Flesch é considerada exploratória, pois a fórmula utilizada é orientada ao inglês e o corpus pode ser multilíngue.

---

## 16. Diagnóstico de multicolinearidade

Foram encontradas correlações fortes:

| Par | Correlação |
|---|---:|
| `text_length` × `word_count` | 0,992 |
| `sibling_count` × `sibling_bytes` | 0,889 |
| `repo_stars` × `repo_forks` | 0,913 |

Para evitar redundância, o modelo principal manteve:

- `text_length`;
- `sibling_count`;
- `repo_stars`.

Os VIFs das variáveis contínuas ficaram abaixo de 5. O maior valor foi 4,197 para `z_log_text_length`, considerado aceitável.

---

## 17. Distribuição da variável dependente após preparação

| Classe | Quantidade | Percentual |
|---|---:|---:|
| Não reutilizado | 1.330.968 | 83,9925% |
| Reutilizado | 253.660 | 16,0075% |

O máximo de `reuse_count` permaneceu igual a 937.

---

## 18. Testes do hurdle model

### 18.1 Primeiro teste

Foi utilizada uma amostra aleatória de 100.000 registros.

O primeiro ajuste falhou na regressão logística porque `repo_is_fork` não apresentava variação suficiente.

Na população do modelo:

```text
repo_is_fork = 0: 1.584.624 registros
repo_is_fork = 1: 4 registros
```

Decisão: retirar `repo_is_fork` do modelo principal e registrar a limitação. A análise sem forks deverá ser definida posteriormente a partir de todas as ocorrências, não apenas do representante.

### 18.2 Segundo teste

Após a retirada de `repo_is_fork`:

- a regressão logística convergiu;
- a binomial negativa truncada inicialmente não convergiu após 200 iterações.

Na amostra positiva:

| Métrica de `extra_reuse` | Resultado |
|---|---:|
| Observações positivas | 15.876 |
| Média | 4,5675 |
| Variância | 139,8596 |
| Mediana | 1 |
| P95 | 18 |
| P99 | 56 |
| Máximo | 295 |

A variância muito superior à média confirma sobredispersão forte.

### 18.3 Ajuste dos parâmetros iniciais

Foi adicionada uma binomial negativa não truncada para estimar parâmetros iniciais, seguida por `L-BFGS` com até 1.000 iterações.

Resultado do novo teste:

- regressão logística: convergiu;
- binomial negativa inicial: convergiu;
- binomial negativa truncada: informou convergência;
- erros-padrão foram produzidos para todos os coeficientes.

Entretanto, o parâmetro de dispersão da versão truncada foi:

```text
alpha ≈ 36.808,59
```

Além disso:

- `LL-Null` ficou indefinido;
- pseudo-R² ficou indefinido;
- foram emitidos avisos numéricos relacionados a Hessiana, logaritmos e overflow.

Uma binomial negativa não truncada na mesma amostra estimou:

```text
alpha ≈ 0,84135
AIC ≈ 75.451,78
log-likelihood ≈ -37.687,89
```

Conclusão: o ajuste truncado do `statsmodels` encontrou uma solução numérica inadequada. Seus coeficientes não devem ser interpretados nem utilizados na versão final.

---

## 19. Estado atual e decisão pendente

O componente logístico está funcional. O componente de contagem truncada precisa ser reestimado com implementação mais estável.

A documentação metodológica consultada confirma que o hurdle model deve conter:

1. componente binário para zero versus contagem positiva;
2. componente de contagem truncado em zero para as observações positivas.

A próxima alternativa selecionada é verificar a disponibilidade do R para utilizar uma implementação consolidada, como `pscl::hurdle`, mantendo:

- componente binário logit;
- componente binomial negativo truncado;
- a mesma fórmula de covariáveis;
- intervalos de confiança e razões de efeito.

O próximo comando pendente é:

```bash
R --version
```

Se o R não estiver instalado, será avaliada a instalação ou outra implementação compatível.

---

## 20. Arquivos produzidos até o momento

### Auditoria

```text
outputs/audit/database_schema.sql
```

### RQ1 - dados e resultados

```text
outputs/rq1/reuse_by_content.csv
outputs/rq1/descriptive_summary.csv
outputs/rq1/descriptive_summary.json
outputs/rq1/reuse_percentiles.csv
outputs/rq1/reuse_ranges.csv
outputs/rq1/reuse_concentration.csv
outputs/rq1/top_100_reused.csv
outputs/rq1/top_100_reused_detailed.csv
outputs/rq1/reuse_ranges.png
outputs/rq1/reuse_ccdf_loglog.png
outputs/rq1/rq1_features_sample.parquet
outputs/rq1/rq1_features.parquet
outputs/rq1/model_missingness.csv
outputs/rq1/transformation_parameters.csv
outputs/rq1/rq1_model_data.parquet
outputs/rq1/representative_repositories.csv
outputs/rq1/rq1_model_data_with_repo.parquet
outputs/rq1/models_test/logistic_coefficients.csv
outputs/rq1/models_test/logistic_summary.txt
outputs/rq1/models_test/truncated_nb_coefficients.csv
outputs/rq1/models_test/truncated_nb_summary.txt
outputs/rq1/models_test/model_metadata.json
```

### Scripts

```text
scripts/01_descriptive_reuse.py
scripts/02_extract_features.py
scripts/03_prepare_model_data.py
scripts/03b_add_representative_repository.py
scripts/04_fit_hurdle_model.py
```

### Logs

```text
logs/01_descriptive_reuse.log
logs/02_extract_features_sample.log
logs/02_extract_features_full.log
logs/03_prepare_model_data.log
logs/03b_add_representative_repository.log
logs/04_fit_hurdle_model_test.log
```

---

## 21. Conclusão parcial

Já existe evidência quantitativa para responder à primeira parte da RQ1:

- o reúso está presente em 16,02% dos conteúdos distintos;
- 42,06% das presenças conteúdo-repositório são reutilizações além da primeira presença;
- a distribuição é fortemente assimétrica e apresenta cauda longa;
- somente 0,0294% dos conteúdos aparecem em mais de 100 repositórios;
- o máximo observado é 937 repositórios;
- o coeficiente de Gini do reúso é aproximadamente 0,398.

A segunda parte da RQ1, referente às características associadas à propagação, ainda depende da conclusão e validação do hurdle model. Nenhuma relação causal será alegada, pois o desenho é observacional.
