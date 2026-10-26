# Resultados exploratórios automatizados — RQ2 e RQ3

**Data:** 26 de outubro de 2026  
**Escopo:** evolução intrarrepositório posterior a uma âncora de conteúdo exato, na amostra condicionada à acessibilidade observada em duas sondagens anteriores.  
**Estado científico:** resultado exploratório e de caso completo; não é estimativa da população integral, genealogia entre repositórios ou evidência causal.

## O que foi verificado

### Fluxo da amostra

- O frame condicionado contém 603 repositórios observados como acessíveis nas duas sondagens.
- Foram sorteados cinco repositórios em cada um de 11 estratos mutuamente exclusivos: 55 repositórios e 122 ocorrências.
- A seleção é determinística, usa seed `20261026` e registra probabilidade e peso condicionais ao frame de 603 repositórios.
- Cinquenta e três repositórios tiveram coleta completa. Dois falharam durante a coleta; todas as suas linhas, inclusive quatro ocorrências parcialmente recuperadas, foram excluídas pela regra conservadora de caso completo.
- Restaram 82 ocorrências elegíveis (67,2% das 122 selecionadas). Em 80 foi localizado no histórico um commit cujo blob da skill coincide com o hash-âncora; duas permaneceram sem âncora temporal resolvida.
- A repetição independente reproduziu byte a byte os quatro CSVs da seleção e os quatro CSVs de síntese.

### RQ2: divergência posterior à âncora

A âncora temporal operacional é o primeiro `commit_time` observado em que o blob da ocorrência coincide com o hash exato do snapshot. Somente comparações com tempo estritamente posterior são tratadas como pós-âncora.

| Medida | Resultado | Intervalo de 95% | Interpretação permitida |
|---|---:|---:|---|
| Ocorrências com divergência pós-âncora, não ponderado | 6/80 = 7,5% | Wilson: 3,5%–15,4% | descrição dos casos completos com âncora resolvida |
| Ocorrências com divergência pós-âncora, ponderado | 1,0% | bootstrap por repositório: 0,3%–1,9% | estimativa condicionada ao frame das sondagens e aos casos completos |
| Comparações pai→filho pós-âncora | 75 | — | eventos dependentes; não são 75 skills independentes |

As 75 comparações foram classificadas em 27 adições, 24 modificações, 19 movimentos e cinco remoções. As proporções ponderadas condicionais foram, respectivamente, 48,7%, 12,7%, 37,3% e 1,3%. Os intervalos bootstrap são amplos para adições (17,2%–81,3%) e movimentos (12,5%–76,6%), evidenciando a concentração dos eventos em poucos repositórios.

Esses resultados demonstram evolução observada depois de uma identidade de conteúdo conhecida. Eles não identificam o criador da skill, não atribuem origem ao repositório representante e não demonstram transmissão entre repositórios.

### RQ3: candidatos automatizados a mudança comportamental

O denominador é formado pelas 75 comparações pai→filho pós-âncora. As categorias são candidatos segundo regras automatizadas; presença textual não prova execução, acesso de rede ou impacto de segurança.

| Alvo e direção | Estrito, n/75 | Estrito ponderado | Amplo, n/75 | Amplo ponderado |
|---|---:|---:|---:|---:|
| comando adicionado | 11 (14,7%) | 39,6% | 40 (53,3%) | 55,6% |
| comando removido | 5 (6,7%) | 1,3% | 16 (21,3%) | 7,0% |
| acesso externo adicionado | 3 (4,0%) | 2,9% | 9 (12,0%) | 39,1% |
| acesso externo removido | 1 (1,3%) | 0,4% | 1 (1,3%) | 0,4% |
| referência a script adicionada | 1 (1,3%) | 2,4% | 21 (28,0%) | 41,2% |
| referência a script removida | 4 (5,3%) | 1,0% | 11 (14,7%) | 4,6% |
| sibling executável adicionado | 1 (1,3%) | 2,4% | 1 (1,3%) | 2,4% |
| sibling executável movido/copiado | 0 | 0 | 1 (1,3%) | 4,0% |

Não foram detectados siblings executáveis removidos ou modificados. As categorias são multirrótulo e não devem ser somadas. A grande distância entre alguns resultados ponderados e não ponderados decorre de pesos desiguais e concentração em poucos clusters; os intervalos completos estão em `rq3_exploratory_summary.csv` e devem acompanhar qualquer uso inferencial.

## O que foi apenas documentado

- A ordem temporal usa timestamps de commit e não autoria ou direção de cópia.
- A classificação estrutural e comportamental segue as definições operacionais congeladas no protocolo automatizado.
- Os pesos corrigem somente a seleção estratificada dentro do frame condicionado; não corrigem falha de coleta, seleção pelas sondagens ou cobertura do GitHub.
- Comparações distintas do mesmo repositório, ocorrência ou merge podem ser dependentes.

## O que está planejado

1. **Executado após este relatório:** construir assinaturas e buscar pares de adoção entre repositórios; o resultado está em `docs/rq2_propagation_candidate_report.md`.
2. Reconstruir a compatibilidade de contexto para definir denominadores elegíveis; oportunidade temporal isolada mostrou-se insuficiente.
3. Ampliar a coleta para além dos 53 repositórios completos; similaridade isolada continuará insuficiente.
4. Produzir métricas de alcance e consistência somente quando houver denominadores contextualmente elegíveis.
5. **Executado após este relatório:** testar associações entre características pré-evento e candidatos comportamentais; nenhum desfecho sustentou o gate para regressão multivariada, conforme `docs/rq3_association_results_report.md`.
6. Gerar tabelas e figuras finais somente após decidir se o artigo reportará esta amostra como estudo exploratório condicionado ou se ampliará a coleta.

## O que permanece incerto

- O motivo das duas falhas de repositório e o viés introduzido pelas 40 ocorrências excluídas.
- A validade semântica, a taxa de falso positivo e a taxa de falso negativo dos classificadores sem referência humana independente.
- A completude dos históricos Git observáveis e a confiabilidade dos timestamps como aproximação temporal.
- A ancestralidade e a direção de transmissão entre repositórios.
- A generalização para os 91.529 repositórios do frame original ou para o GitHub.
- A estabilidade das estimativas ponderadas, dada a concentração de eventos e o pequeno número de repositórios por estrato.

## Artefatos rastreáveis

- seleção: `AnaliseGitSkills/outputs/rq2/analytic_sample_v1/`;
- recuperação e exclusões: `AnaliseGitSkills/outputs/rq2/analytic_recovery_v1/`;
- diffs: `AnaliseGitSkills/outputs/rq2/diff_analytic_v1/`;
- classificação estrutural: `AnaliseGitSkills/outputs/rq2/structured_diff_analytic_v1/`;
- classificação comportamental: `AnaliseGitSkills/outputs/rq3/behavioral_analytic_v2/`;
- síntese: `AnaliseGitSkills/outputs/exploratory_results_v2/`;
- implementação: `AnaliseGitSkills/scripts/14_select_rq2_analytic_sample.py`, `AnaliseGitSkills/scripts/15_prepare_rq2_analytic_recovery.py` e `AnaliseGitSkills/scripts/16_generate_exploratory_rq2_rq3_results.py`.

`behavioral_analytic_v1` está supersedido e não deve ser usado: oito eventos falharam ao tentar interpretar siblings binários como UTF-8. `behavioral_analytic_v2` é a primeira execução analítica completa após a correção, com 173/173 eventos classificados. De modo análogo, `behavioral_calibration_v3` é a calibração ligada ao checksum atual do classificador; seus CSVs são idênticos aos de `v2`.

## Critério de conclusão deste passo

Este passo está concluído porque seleção, perdas, âncoras, eventos, estimativas, intervalos, limitações e repetibilidade estão registrados. A busca inter-repositórios subsequente encontrou somente um candidato C e nenhuma evidência A/B; RQ2 permanece limitada pela ausência de denominador contextual, e RQ3 ainda carece da análise de associações.
