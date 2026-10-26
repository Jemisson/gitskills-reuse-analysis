# Resultados associativos exploratórios — RQ3

**Data:** 26 de outubro de 2026  
**Unidade:** comparação pai→filho pós-âncora.  
**Escopo:** 75 eventos, 25 ocorrências, 18 repositórios e 17 famílias-âncora da amostra condicionada de casos completos.  
**Estado científico:** resposta descritiva exploratória; nenhum modelo multivariado foi considerado sustentável.

## O que foi verificado

### Base analítica

- Foi construída uma linha por evento, com `diff_id` único, pesos condicionais e 20 desfechos estritos/amplos.
- As covariáveis pré-evento incluem idade desde a âncora, eventos e divergências anteriores, intensidade de reúso, classe do path e características do blob pai.
- Características concorrentes — merge, operação e churn — permanecem explicitamente separadas das covariáveis pré-evento.
- Quarenta e oito dos 75 eventos possuem blob pai. Exposições derivadas do pai são avaliadas somente nesses 48 eventos; adições de arquivo não são codificadas como ausência da característica.
- Um repositório concentra 29/75 eventos. Nenhum dos 20 desfechos passou o limiar pré-especificado de 30 clusters para regressão multivariada.
- Foram calculadas 280 comparações descritivas não ajustadas, sem valores de `p` e sem FDR, pois nenhuma família de modelos inferenciais foi ajustada.

### Sensibilidade estrita versus ampla

| Desfecho | Estrito | Amplo | Jaccard |
|---|---:|---:|---:|
| comando adicionado | 11 | 40 | 0,275 |
| comando removido | 5 | 16 | 0,313 |
| acesso externo adicionado | 3 | 9 | 0,333 |
| acesso externo removido | 1 | 1 | 1,000 |
| referência a script adicionada | 1 | 21 | 0,048 |
| referência a script removida | 4 | 11 | 0,364 |
| sibling executável adicionado | 1 | 1 | 1,000 |
| sibling executável movido/copiado | 0 | 1 | 0,000 |

As definições amplas alteram materialmente as contagens, especialmente para referências a scripts e comandos. Logo, os resultados dependem fortemente da definição operacional.

### Coocorrência ampla

- Dos 40 eventos com comando adicionado, 16 também adicionaram referência a script e nove também adicionaram candidato a acesso externo.
- Todos os nove eventos com acesso externo adicionado amplo também receberam comando adicionado amplo.
- Sete dos 21 eventos com referência a script adicionada também receberam acesso externo adicionado.

Essas coocorrências não representam mecanismos independentes: uma mesma linha, como um comando de download ou invocação, pode acionar múltiplas regras.

### Padrões descritivos

Alguns contrastes ponderados não ajustados foram grandes, entre eles:

- eventos com 90 dias ou mais desde a âncora apresentaram maior frequência descritiva de remoção ampla de comandos e referências a scripts;
- famílias com `reuse_count >= 11` apresentaram maior frequência descritiva de adição estrita de comandos;
- presença ampla de referência a script no blob pai coincidiu com maior frequência de adição ampla de referências a scripts;
- eventos em diffs grandes ou comparações de merge concentraram adições amplas.

Esses padrões não são resultados confirmatórios. Eles são sensíveis a pesos, concentração por repositório, múltiplas comparações e definições automatizadas. Churn e merge são características do próprio evento e também aumentam mecanicamente a oportunidade de detectar linhas candidatas.

## O que foi apenas documentado

- O limiar para permitir modelos exige pelo menos 50 eventos, dez positivos, cinco repositórios positivos, cinco negativos e 30 clusters de repositório.
- Razões de risco são ponderadas pelo desenho condicionado; intervalos usam bootstrap estratificado por repositório.
- Os intervalos não corrigem multiplicidade e não devem ser interpretados como testes de significância.
- “Associado” significa coexistência estatística descritiva, não causalidade.
- Os desfechos representam texto/estrutura compatível com comportamento, não execução real.

## O que está planejado

1. Usar estes resultados como resposta descritiva da RQ3 caso não seja possível ampliar a amostra.
2. Se houver nova coleta, exigir ao menos 30 clusters e reexecutar o gate antes de qualquer regressão.
3. Reavaliar modelos ajustados somente com desfechos presentes em número suficiente de repositórios.
4. Manter análises estrita e ampla lado a lado no artigo; nenhuma deve ser tratada como verdade semântica.

## O que permanece incerto

- Validade semântica e taxas de falso positivo/negativo dos classificadores.
- Generalização para a população completa ou para o GitHub.
- Estabilidade dos contrastes sob maior número de repositórios.
- Separação entre efeito do tamanho do diff e conteúdo substantivo da mudança.
- Dependência residual por ocorrência, família, merge e regras multirrótulo.

## Resposta sustentada à RQ3

Na amostra observada, não há suporte para identificar características independentemente associadas por meio de regressão multivariada. Descritivamente, idade da linhagem, intensidade de reúso, conteúdo do blob pai, localização e características do evento exibem contrastes com candidatos comportamentais, mas esses contrastes são instáveis, não ajustados e fortemente sensíveis às definições estrita/ampla. A conclusão cientificamente defensável é que a taxonomia operacional e a estrutura dos poucos clusters dominam a evidência disponível.

## Artefatos finais

- base: `AnaliseGitSkills/outputs/rq3/association_dataset_v2/`;
- análise: `AnaliseGitSkills/outputs/rq3/association_results_v4/`;
- tabelas e figuras: `AnaliseGitSkills/outputs/rq3/article_artifacts_v3/`;
- implementação: `AnaliseGitSkills/scripts/21_build_rq3_association_dataset.py`, `22_analyze_rq3_associations.py` e `23_generate_rq3_article_artifacts.py`.

As versões anteriores dessas saídas estão supersedidas e não devem ser usadas.
