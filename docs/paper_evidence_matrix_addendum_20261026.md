# Adendo à matriz de evidências — 26 de outubro de 2026

Este adendo preserva o checksum da matriz congelada no protocolo v1.0 e registra as novas evidências técnicas. Ele não promove resultados da calibração a estimativas populacionais.

| ID | Evidência nova | Entrada | Transformação | Saída | Estado |
|---|---|---|---|---|---|
| RQ2-E05-A1 | Regiões e escopos candidatos foram extraídos dos 26 eventos de calibração | `diff_calibration_20261026_v2/diff_events.csv` + blobs/diffs | `12_classify_rq2_structured_diffs.py`, versão `rq2-structured-diff-v1.0` | `structured_diff_calibration_v3/` | VERIFICADO computacionalmente; não inferencial e sem validade semântica externa |
| RQ2-E08-A1 | Classificação determinística e churn reconciliado | mesmas entradas | fixtures, checksum de 26 diffs e repetição independente | três CSVs com hashes idênticos entre execuções | VERIFICADO computacionalmente |
| RQ3-E01-A1 | Candidatos a adição/remoção de comandos na calibração | evidências estruturadas de 26 eventos | regras estritas/amplas `rq3-behavioral-candidates-v1.0` | `behavioral_calibration_v3/` | VERIFICADO computacionalmente; não é prevalência populacional |
| RQ3-E02-A1 | Candidatos a acesso externo na calibração | mesmas entradas | tokens operacionais e URLs explícitas | evidência textual + contagens | VERIFICADO computacionalmente; presença textual não prova acesso |
| RQ3-E03-A1 | Candidatos a scripts/siblings executáveis na calibração | texto + árvores Git pai/filho | invocação/path, modo Git, shebang e extensão | evidência textual e de siblings | VERIFICADO computacionalmente; não prova execução |
| RQ3-E08-A1 | Sensibilidade estrita/ampla e determinismo | mesmas entradas | invariante estrito ⊆ amplo + repetição | quatro CSVs idênticos | VERIFICADO computacionalmente |
| RQ2-E09-A1 | Amostra analítica condicionada | 603 repositórios acessíveis nas duas sondagens | amostragem aleatória simples dentro de 11 estratos primários mutuamente exclusivos, seed `20261026` | 55 repositórios e 122 ocorrências em `analytic_sample_v1/` | VERIFICADO; pesos válidos apenas dentro do frame condicionado |
| RQ2-E10-A1 | Fluxo de recuperação analítica | amostra de 122 ocorrências | exclusão integral de repositórios com coleta incompleta | 53 repositórios completos e 82 ocorrências elegíveis em `analytic_recovery_v1/` | VERIFICADO; 40 ocorrências excluídas e não resposta não corrigida pelos pesos |
| RQ2-E11-A1 | Evolução posterior à âncora exata | históricos, diffs e classificações estruturais | primeira igualdade de blob como âncora; tempo estritamente posterior; Wilson e bootstrap estratificado por repositório | `exploratory_results_v2/rq2_exploratory_summary.csv` | VERIFICADO como resultado exploratório de caso completo; não demonstra ancestralidade ou propagação |
| RQ3-E09-A1 | Candidatos comportamentais pós-âncora | 75 comparações pai→filho pós-âncora | cenários estrito/amplo, ponderação condicional e bootstrap por repositório | `exploratory_results_v2/rq3_exploratory_summary.csv` | VERIFICADO como resultado exploratório; sem validação semântica externa |
| REP-E02-A1 | Repetibilidade da amostra, calibração RQ3 corrigida e síntese | mesmas entradas e seeds | reexecuções em diretório temporário | 12 CSVs byte a byte idênticos | VERIFICADO em 26/10/2026 |
| RQ2-E12-A1 | Assinaturas de patches observados | 173 eventos estruturados e diffs brutos | normalização versionada, hash direcional e exclusão de movimentos/patches vazios | 151 assinaturas elegíveis em `patch_signatures_v1/` | VERIFICADO como mecanismo de recuperação; identidade de patch não prova transmissão |
| RQ2-E13-A1 | Busca de adoções inter-repositórios | divergências pós-âncora da mesma família exata | ordem temporal estrita e colapso da primeira adoção por repositório | um candidato em `adoption_candidates_v3/` | VERIFICADO; universo limitado a 53 repositórios completos |
| RQ2-E14-A1 | Confiança genealógica | candidato exato temporalmente ordenado | regras A–D `genealogical-candidate-confidence-v1.0` | zero A/B e um C em `genealogical_relations_v4/` | VERIFICADO; remoção de baixa especificidade, sem atribuição de origem |
| RQ2-E15-A1 | Estimabilidade da propagação | cobertura temporal e candidato C | auditoria do denominador | taxa marcada `not_estimable` em `propagation_results_v4/` | VERIFICADO; contexto elegível não estabelecido |
| REP-E03-A1 | Repetibilidade da busca de propagação | mesmas entradas e regras | reexecução das etapas 17–20 | dez CSVs byte a byte idênticos | VERIFICADO em 26/10/2026 |
| RQ3-E10-A1 | Base associativa temporalmente classificada | 75 comparações pós-âncora + blobs pai + covariáveis do snapshot | `21_build_rq3_association_dataset.py` | 75 linhas únicas em `association_dataset_v2/` | VERIFICADO; 48 eventos possuem blob pai |
| RQ3-E11-A1 | Gate de viabilidade dos modelos | 20 desfechos e 18 clusters de repositório | limiares pré-especificados antes da interpretação | zero desfechos elegíveis em `association_results_v4/` | VERIFICADO; regressão multivariada não ajustada |
| RQ3-E12-A1 | Associações descritivas | 14 exposições e 20 desfechos | razões de risco ponderadas e bootstrap por repositório | 280 contrastes em `rq3_descriptive_associations.csv` | VERIFICADO; não ajustado, sem causalidade, `p` ou FDR |
| RQ3-E13-A1 | Sensibilidade da taxonomia | pares estrito/amplo | contagens, inclusão de conjuntos e Jaccard | `rq3_scenario_sensitivity.csv` | VERIFICADO; forte dependência da definição operacional |
| RQ3-E14-A1 | Artefatos do artigo | resultados descritivos finais | geração determinística | três tabelas e duas figuras em `article_artifacts_v3/` | VERIFICADO visualmente e por checksum |
| REP-E04-A1 | Repetibilidade da análise RQ3 | mesmas entradas, seed e 2.000 réplicas | reexecução das etapas 21–23 | 12 artefatos idênticos byte a byte | VERIFICADO em 26/10/2026 |
| PAPER-E01-A1 | Consolidação do manuscrito empírico | relatórios finais e artefatos rastreados de RQ1--RQ3 | seleção conservadora de alegações e referências internas em comentários LaTeX | `IEEE_Conference_Template/gitskills_paper.tex` | VERIFICADO quanto à correspondência com as evidências listadas; não é versão final de submissão |
| PAPER-E02-A1 | Integridade da compilação | fonte LaTeX e figuras finais | duas passagens de compilação e inspeção do log | `IEEE_Conference_Template/gitskills_paper.pdf`, quatro páginas | VERIFICADO; sem avisos de caixa, referências internas indefinidas ou cortes visuais observados |

## Limite de uso no artigo

Os números 18/7/1, 4.252/231 e 22/26 podem ser usados apenas para descrever a calibração técnica. Não podem ser apresentados como prevalências da população de Agent Skills. As categorias semânticas devem conservar o sufixo ou a formulação “candidato segundo regra automatizada”.

As estimativas de `exploratory_results_v2` podem ser usadas somente como resultados exploratórios condicionados ao frame das duas sondagens e aos casos completos. Os pesos não autorizam generalização à população integral. Comparações pós-âncora mostram evolução intrarrepositório; não são prova de ancestralidade ou propagação entre repositórios.
