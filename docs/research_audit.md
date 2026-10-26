# Auditoria científica do projeto GitSkills

**Data da auditoria:** 16 de outubro de 2026  
**Escopo:** estado local do repositório `Jemisson/gitskills-reuse-analysis`, branch `master`, commit `a242dde`  
**Regra de leitura:** a existência de um script ou arquivo não foi aceita, isoladamente, como evidência de execução ou de conclusão científica.

> **Atualização posterior à auditoria:** as lacunas de geração das entradas, exportação para R, filtro de megarepositórios e FDR foram implementadas e verificadas em 16/10/2026. Em 26/10/2026, recomendações de dupla anotação, adjudicação e conjunto-ouro foram substituídas pela [emenda de validação automatizada](protocol_amendment_automated_validation.md). O diagnóstico abaixo descreve o baseline encontrado; o estado corrente está em [implementation_progress.md](implementation_progress.md).

## Legenda epistemológica

- **VERIFICADO:** inspecionado diretamente no código, banco, log ou artefato; quando viável, recalculado de forma independente.
- **DOCUMENTADO:** afirmado em documento ou log, mas sem cadeia completa e versionada que permita reproduzi-lo do banco ao resultado.
- **PLANEJADO:** método ou produto proposto, ainda sem evidência de execução.
- **INCERTO:** faltam dados, procedência, decisão metodológica ou validação suficiente.

## Diagnóstico executivo

O projeto contém uma análise de RQ1 substancial e internamente coerente, com dados intermediários locais, logs, modelos serializados, tabelas finais e relatório. Os totais descritivos principais e as relações entre as variáveis de resposta foram verificados. Os modelos finais logístico + PPML foram executados e seus arquivos indicam convergência computacional. Isso sustenta uma resposta observacional à RQ1, mas não uma inferência causal.

O repositório ainda não é reproduzível de ponta a ponta. Quatro transformações essenciais não têm implementação versionada: geração de `reuse_by_content.csv`, geração de `representative_repositories.csv`, exportação/preparação dos CSVs usados pelo R (incluindo a exclusão de megarepositórios) e aplicação de Benjamini–Hochberg. O registro de execução também está desatualizado: encerra a narrativa antes dos modelos finais, embora logs posteriores comprovem que eles foram executados. RQ2 e RQ3 possuem apenas uma proposta de alto nível; diretórios reservados existem, mas estão vazios e não há scripts, amostras, anotações ou resultados.

Assim, o estado recomendado é:

- **RQ1: análise executada, resultados principais verificáveis, reprodução integral pendente e interpretação a ser estreitada em alguns pontos;**
- **RQ2: planejada, não implementada;**
- **RQ3: planejada, não implementada;**
- **validação qualitativa: planejada, não implementada.**

## Materiais examinados

| Material | Estado | Observação |
|---|---|---|
| [`README.md`](../README.md) | VERIFICADO | Descreve RQ1 como concluída e RQ2/RQ3 como planejadas. |
| [`Registro_Execucao_GitSkills_RQ1.md`](../Registro_Execucao_GitSkills_RQ1.md) | VERIFICADO, DESATUALIZADO | Datado de 1º/10/2026; termina com o modelo de contagem ainda pendente. |
| [`RQ1_Resultados.md`](../AnaliseGitSkills/reports/RQ1_Resultados.md) | VERIFICADO | Relata os modelos e sensibilidades executados em 3/10/2026. |
| [`proposta.pdf`](../proposta.pdf) | VERIFICADO | Fonte das formulações de RQ2/RQ3 e do desenho inicialmente proposto. |
| Scripts `01` a `05`, scripts R e `gitskills_phase1_analysis.py` | VERIFICADO | Todos foram lidos; o script na raiz usa um esquema antigo/incompatível com o banco atual. |
| Logs em `AnaliseGitSkills/logs/` | VERIFICADO | Demonstram execuções, mas estão ignorados pelo Git e não registram comandos completos, hashes ou sessão. |
| Resultados leves versionados | VERIFICADO | CSVs e figuras finais presentes no Git. |
| Intermediários, modelos `.rds` e banco local | VERIFICADO LOCALMENTE | Presentes, porém ignorados pelo Git e não distribuídos pelo repositório. |
| Diretórios de RQ2, RQ3, amostras, anotações e validação | VERIFICADO VAZIO | Não há evidência de execução. |

## Cadeia de procedimentos da RQ1

| Etapa | Implementada? | Executada? | Evidência comprovável | Reproduzível a partir do banco? |
|---|---:|---:|---|---:|
| Auditoria do esquema SQLite | Parcial | Sim | esquema versionado e contagens conferidas no banco local | Parcial |
| Definição da população principal | Sim, em `02_extract_features.py` | Sim | 1.586.188 linhas no Parquet e no CSV de reúso | Sim, se o CSV de reúso já existir |
| Cálculo de `reuse_count` por SHA e repositório distinto | **Não versionada** | Sim | `reuse_by_content.csv`, log e totais consistentes | **Não** |
| Estatísticas descritivas e figuras | Sim | Sim | log e saídas de `01_descriptive_reuse.py` | Sim, a partir do CSV ausente da cadeia |
| Extração das 34 características | Sim | Sim | log, Parquet com 1.586.188 × 34 | Sim, condicionada ao CSV de reúso e ao banco |
| Preparação, winsorização e padronização | Sim | Sim | log, parâmetros e Parquet com 1.584.628 linhas | Sim |
| Associação ao repositório representante | Parcial | Sim | junção implementada; CSV de associação não é gerado por script | **Não integralmente** |
| Exportação de Parquet para CSV do R | **Não versionada** | Sim | CSV de 1.584.628 linhas existe localmente | **Não** |
| Diagnóstico hurdle NB em Python | Sim | Sim, amostra | log e artefatos; solução degenerada, corretamente rejeitada | Sim a partir dos intermediários |
| Diagnóstico hurdle NB em R | Sim | Sim, amostra | log, métricas e `.rds`; solução degenerada, corretamente rejeitada | Sim a partir dos intermediários |
| Modelo logístico + PPML HC1 | Sim | Sim | log, coeficientes, métricas e `.rds` | Sim a partir do CSV do R |
| Modelo principal com erros agrupados | Sim | Sim | log e artefatos do modelo | Sim a partir do CSV do R |
| Correção FDR de Benjamini–Hochberg | **Não versionada** | Sim | valores recalculados coincidem numericamente com o CSV | **Não como pipeline** |
| Sensibilidade sem 16 megarepositórios | Modelo sim; seleção não | Sim | log e coeficientes; CSV filtrado existe localmente | **Não integralmente** |
| Sensibilidade à cauda P99,5 | Sim | Sim | log, modelo e coeficientes | Sim a partir do CSV do R |
| Consolidação de tabelas e forest plot | Sim | Sim | log e quatro saídas finais | Sim, se entradas ignoradas estiverem presentes |

## Evidências verificadas da RQ1

Foram recalculados diretamente de `reuse_by_content.csv`:

- 1.586.188 conteúdos SHA distintos, sem SHA ausente ou duplicado;
- 1.332.110 conteúdos em um único repositório e 254.078 em dois ou mais;
- 3.347.020 ocorrências e 2.737.824 pares conteúdo–repositório;
- 1.151.636 presenças adicionais, equivalentes a 42,063916% dos pares conteúdo–repositório;
- média 1,7260, mediana 1, máximo 937 e Gini 0,397779;
- consistência de `is_reused = I(reuse_count > 1)` e `extra_reuse = reuse_count - 1` em todas as 1.584.628 linhas modeladas;
- 253.660 casos positivos no conjunto modelado e 218.408 repositórios representantes;
- 16 repositórios representantes com mais de 5.000 conteúdos, somando 183.623 linhas;
- FDR-BH recalculado separadamente nos dois componentes, com diferença numérica máxima de aproximadamente `1,1e-16` em relação ao arquivo final;
- razão mediana entre os erros-padrão agrupados e HC1 igual a 10,946, consistente com o relatório;
- todos os 37 coeficientes da intensidade mantêm direção e classificação por `p < 0,05` na sensibilidade da cauda; 71 de 74 coeficientes mantêm direção entre a amostra de 100 mil e a população completa.

Essas verificações comprovam coerência interna dos artefatos disponíveis. Elas não substituem a reprodução desde o snapshot bruto nem validam ancestralidade, origem ou mecanismo causal.

## Consistência entre pergunta, métricas, modelos e conclusões

### Pontos consistentes

- A unidade da RQ1 é conteúdo exato, e `reuse_count` mede repositórios distintos, evitando inflar propagação por múltiplos paths no mesmo repositório.
- As duas respostas distinguem ocorrência de reúso e intensidade condicional entre conteúdos reutilizados.
- O relatório abandona explicitamente a binomial negativa truncada degenerada e não interpreta seus coeficientes.
- PPML com covariância robusta é apresentado como modelo de média condicional, sem exigir equidispersão para a inferência robusta.
- As conclusões são descritas como associações e não como efeitos causais.
- A limitação de Flesch para corpus multilíngue e o caráter não originário do repositório representante são declarados.

### Inconsistências ou sobre-extensões

1. **Estado conflitante.** O README declara RQ1 concluída; o registro de execução diz que a segunda parte ainda depende do hurdle. Os logs posteriores resolvem o conflito factual, mas o registro precisa de adendo, não de reescrita retroativa.
2. **Plano versus execução.** A proposta previa binomial negativa truncada, `fork` e idade da skill. O modelo final usa PPML, remove `fork` por quase ausência de variação e não inclui idade da skill pela baixa cobertura histórica. As mudanças são defensáveis, mas precisam ser registradas como desvios do protocolo.
3. **“Propagação” na RQ1.** O desfecho é presença transversal de conteúdo byte a byte em múltiplos repositórios. Ele mede alcance de reúso exato, não fluxo temporal, direção de transmissão ou propagação de uma alteração.
4. **Contexto do representante.** Estrelas, idade, linguagem e atividade pertencem ao repositório representante, que não é origem comprovada. As associações contextuais devem ser descritas como associações com a ocorrência representante escolhida pelo dataset.
5. **Resumo excessivamente amplo.** A frase final que inclui “atividade e popularidade” deve ser lida por componente: inatividade foi significativa apenas para probabilidade; estrelas, apenas para intensidade, com associação negativa. Não há evidência de mecanismo promotor.
6. **PPML condicional.** Os coeficientes são razões da média condicional sob especificação log-linear. A robustez da covariância não corrige especificação incorreta da média. AIC e log-verossimilhança do Poisson não devem ser usados para alegar ajuste distribucional diante da sobredispersão.
7. **Agrupamento.** O cluster por repositório representante é uma escolha pragmática, mas depende de uma ocorrência arbitrária do conteúdo. Faltam sensibilidades com outras estruturas de dependência e justificativa formal da unidade de cluster.
8. **Seleção da população.** A exigência de front matter válido e hash validado pode induzir seleção. Não há análise de sensibilidade com critérios alternativos de inclusão.

## Distinções conceituais obrigatórias

| Conceito | O que os dados atuais permitem | O que não permitem |
|---|---|---|
| Identidade de conteúdo | igualdade do `file_sha` validado, usada para agrupar conteúdo exato | equivalência semântica ou textual após edição |
| Similaridade | ainda não implementada | afirmar que dois textos similares têm relação histórica |
| Ancestralidade | apenas história parcial por ocorrência; não reconstruída | tratar o primeiro timestamp observado ou o representante como origem |
| Evolução | ainda não observada como sequência completa de versões | inferir evolução de uma comparação transversal |
| Propagação de alteração | ainda não medida | equiparar presença do mesmo hash em vários repositórios à transmissão dirigida de um patch |

## Reprodutibilidade e dependências

### Verificado

- Python 3.12.3 local; `pip check` não encontrou dependências quebradas.
- R 4.3.3 local; `data.table 1.14.10`, `sandwich 3.1.0`, `lmtest 0.9-40` e `pscl 1.5.9` disponíveis.
- O banco local tem aproximadamente 44,4 GB; as tabelas têm 3.797.117 `artifacts`, 282.200 `repos` e 7.264.865 `artifact_siblings`.
- O banco é aberto como somente leitura em `02_extract_features.py`.

### Lacunas

- não há script único/orquestrador, Makefile, workflow ou testes automatizados;
- não há SQL versionado para os dois CSVs que iniciam a cadeia;
- não há script para exportação ao R, filtro de megarepositórios ou FDR;
- não há `renv.lock`, `sessionInfo()`, manifesto de sistema ou hashes de entrada/saída;
- logs estão ignorados pelo Git, não incluem comando completo, commit, timestamps de início/fim, seed e checksums;
- arquivos grandes necessários não possuem manifesto de obtenção, checksum e esquema versionado;
- `requirements.txt` fixa versões Python, mas não documenta como reconstruir as dependências R;
- `gitskills_phase1_analysis.py` usa nomes antigos (`content_hash`, `repository`, `text`, `is_representative`) inexistentes no esquema atual e pode induzir execução incorreta;
- o README apresenta uma sequência que começa em `01_descriptive_reuse.py`, embora esse script dependa de um arquivo que nenhum script versionado cria.

## Documentos desatualizados

- **Registro de execução:** desatualizado desde 1º/10/2026; omite as execuções `04b`–`05` de 3/10/2026.
- **Organograma/proposta:** conserva a binomial negativa truncada como modelo final previsto; deve ser marcado como plano original.
- **README:** mais atual que o registro, mas descreve reprodução parcial como se fosse a sequência principal completa.
- **Script da raiz:** protótipo incompatível com o esquema atual; deve ser arquivado ou rotulado como legado em mudança futura separada.

## Pendências por prioridade

1. **P0 — restaurar a cadeia reproduzível da RQ1:** versionar SQL/scripts para todas as etapas ausentes, criar manifesto e executar uma reprodução controlada com checksums.
2. **P0 — congelar o protocolo RQ2/RQ3 antes de coletar:** definições, amostragem, níveis de evidência genealógica, codebook, plano de exclusões e testes de robustez.
3. **P1 — executar um piloto de recuperabilidade do histórico:** amostra pequena e estratificada, sem estimar resultados substantivos, para medir acesso, perdas, renomes e custo.
4. **P1 — calibrar e validar geração de candidatos de variante:** alta revocação, sem converter similaridade em ancestralidade.
5. **P1 — elaborar e pilotar o codebook.** Recomendação histórica substituída por codebook automatizado, fixtures e sensibilidades conforme a emenda de 26/10/2026.
6. **P2 — implementar pipeline RQ2 e somente depois estimar padrões evolutivos.**
7. **P2 — implementar classificadores e modelos RQ3 após congelar regras e fixtures.** Não haverá conjunto-ouro independente nesta execução.
8. **P3 — consolidar tabelas, figuras, pacote de replicação e narrativa do artigo.**

## Primeira tarefa recomendada

Implementar e testar um **manifesto reprodutível da população e do reúso exato da RQ1**: um script somente leitura que gere `reuse_by_content.csv` e `representative_repositories.csv` a partir do SQLite, registre consulta, commit, versão do banco, checksum e contagens invariantes. Essa tarefa fecha a primeira quebra da linhagem de evidência e cria a base confiável para selecionar as famílias de RQ2 sem iniciar prematuramente sua implementação completa.

