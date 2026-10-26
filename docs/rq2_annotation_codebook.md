# Codebook automatizado de genealogia e mudanças — RQ2

**Versão:** 0.2 — protocolo automatizado congelado  
**Estado:** CONGELADO em 26/10/2026 para implementação; resultados dependem da versão executável e de seu checksum.  
**Unidade:** relação candidata entre versões e evento pai→filho.

> Não haverá anotação humana independente. Este codebook define categorias operacionais do pipeline, conforme a [emenda metodológica](protocol_amendment_automated_validation.md); ele não constitui evidência de validade semântica externa.

## Regra central

O classificador registra a evidência observável segundo regras versionadas, não a história que parece mais plausível. Similaridade não prova ancestralidade; data mais antiga não prova origem; repositório representante não prova autoria.

## Formulário A — relação entre versões/linhagens

| Campo | Valores | Regra |
|---|---|---|
| `relation_present` | sim / não / incerto | Existe relação evolutiva sustentada pelas evidências fornecidas? |
| `direction` | A→B / B→A / comum-indeterminado / não aplicável | Usar direção somente com suporte histórico. |
| `evidence_git_reachability` | sim / não / indisponível | Commit/blob compartilhado e alcançável no grafo. |
| `evidence_explicit_provenance` | sim / não / indisponível | Fork, referência ou mensagem verificável que identifica proveniência. |
| `evidence_exact_content_anchor` | sim / não | Algum estado byte a byte idêntico foi observado. |
| `evidence_chronology` | compatível / contraditória / empatada / ausente | Cronologia auxilia, mas não é suficiente. |
| `evidence_similarity_only` | sim / não | Marcar quando esta é a única base da candidatura. |
| `confidence_level` | A / B / C / D | Aplicar as regras abaixo. |
| `ambiguity_reason` | texto/código | Obrigatório para C, D ou direção indeterminada. |

### Níveis

- **A — sustentada:** direção apoiada por alcançabilidade Git/proveniência explícita e cronologia não contraditória.
- **B — cópia compatível:** âncora exata e cronologia compatível, mas doador direto/direção não comprovados.
- **C — candidata:** similaridade/diff e cronologia compatíveis sem evidência histórica suficiente.
- **D — rejeitada ou ambígua:** contradição, múltiplos pais equivalentes, ausência de suporte ou caso impossível de decidir.

Uma relação B não deve receber direção apenas porque uma ocorrência foi observada antes. Relações C não entram como fatos na análise principal.

## Formulário B — evento de mudança

### Existência e direção

| Campo | Valores |
|---|---|
| `change_present` | sim / não / incerto |
| `change_operation` | adição / remoção / modificação / movimento / formatação / múltipla |
| `semantic_scope` | nome / descrição / instrução / exemplo / comando-código / rede-URL / script / referência / front-matter-outro / múltiplo |
| `behavior_relevance_candidate` | sim / não / incerto |
| `revert_candidate` | sim / não / incerto |

### Regras

- Formatação inclui whitespace, wrapping e movimento sem mudança textual substantiva.
- Movimento deve preservar conteúdo; movimento com edição é `múltipla`.
- Uma mudança pode afetar várias regiões; registrar os rótulos atômicos antes do resumo.
- “Comportamentalmente relevante” é candidatura para RQ3, não afirmação de execução real.
- Mudança em sibling só pode ser anotada se versões pai e filha do sibling estiverem disponíveis.

## Formulário C — propagação de alteração

| Campo | Valores | Regra |
|---|---|---|
| `patch_match` | equivalente / parcialmente equivalente / diferente / incerto | Comparar efeito estruturado e contexto, não somente texto. |
| `adoption_order` | posterior / anterior / empatada / ausente | Derivada das datas observáveis. |
| `eligible_context` | sim / não / incerto | A linhagem possuía o trecho/contexto ao qual o patch se aplicava? |
| `propagation_evidence` | sustentada / compatível / candidata / rejeitada | Combinar patch, ordem e genealogia. |

Uma adoção textual posterior sem relação genealógica suficiente é “candidata”, não propagação comprovada.

## Casos que devem permanecer ambíguos

- dois repositórios exibem o mesmo conteúdo no mesmo intervalo, sem grafo compartilhado;
- timestamps de autor e commit fornecem ordens diferentes;
- merge possui dois pais que contêm partes relevantes;
- repositório foi reescrito ou importado sem história anterior;
- variante tem alta similaridade, mas nenhuma âncora exata/proveniência;
- fonte comum externa é mencionada, mas não observada;
- path foi renomeado e a continuidade não pode ser sustentada.

## Procedimento automatizado

1. Aplicar regras determinísticas na ordem de precedência versionada.
2. Registrar para cada rótulo a regra, evidência, offsets/paths, versão e confiança operacional.
3. Retornar `incerto` quando evidência ou contexto forem insuficientes; nunca completar lacunas por plausibilidade.
4. Executar fixtures positivas, negativas, limítrofes, renames, merges e falhas de parser.
5. Repetir a classificação e comparar checksums antes da análise substantiva.
6. Executar definições estrita e ampla como sensibilidade, preservando ambas as saídas.
7. Alterações no codebook geram nova versão e não reescrevem silenciosamente decisões anteriores.

## Critérios para congelar a versão executável

- exemplos positivos, negativos e limítrofes para cada rótulo;
- schema, ordem de precedência, versão e checksum registrados;
- todos os rótulos possuem regra executável ou são explicitamente marcados como ainda não implementados;
- fixtures e invariantes passam sem consulta aos resultados estatísticos;
- casos residuais recebem `incerto` e sua frequência é reportada;
- não são calculados κ, precisão, recall ou F1 sem referência independente.

