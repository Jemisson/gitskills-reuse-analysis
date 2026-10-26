# Busca automatizada de propagação entre repositórios — RQ2

**Data:** 26 de outubro de 2026  
**Universo observado:** 82 ocorrências em 53 repositórios com coleta completa.  
**Estado científico:** busca exploratória de candidatos; não comprova transmissão, ancestralidade ou origem.

## O que foi verificado

- Os 173 eventos de mudança produziram 151 assinaturas elegíveis; movimentos puros e patches sem linhas alteradas foram excluídos.
- A assinatura `exact-normalized-patch-v1.0` preserva direção e ordem das linhas adicionadas/removidas, normalizando Unicode e espaços.
- Dezenove grupos de assinatura aparecem em mais de um repositório quando todo o histórico observado é considerado.
- A busca substantiva foi restringida a divergências pós-âncora, mesma família de conteúdo exato e repositórios distintos.
- Repetições do mesmo patch em paths ou commits de um repositório foram colapsadas na primeira adoção observada por repositório. Antes da correção, uma única relação aparecia artificialmente como quatro pares.
- Após o colapso, restou uma relação candidata dirigida, baseada em uma assinatura, sem empate temporal e sem predecessores concorrentes.
- A relação liga uma remoção observada primeiro em `ForceInjection/domain-driven-design-skills` a uma remoção compatível observada aproximadamente 77,12 dias depois em `MikeCheng1208/BattleTree`.
- A relação recebeu confiança **C**, não B: remover o mesmo conteúdo produz naturalmente um patch idêntico e tem baixa especificidade para inferir transmissão.
- Não foi encontrada relação A ou B. Nenhum repositório foi denominado origem.
- Dez CSVs das quatro etapas foram reproduzidos byte a byte em execução independente.

## O que foi apenas documentado

- “Fonte” nos CSVs significa somente evento observado mais cedo pelo timestamp do commit.
- Confiança A exige proveniência explícita ou ancestralidade Git compartilhada e não é alcançável com os dados atuais.
- Confiança B exige modificação exata, transição idêntica entre blobs não vazios, mesma família-âncora e ordem temporal estrita.
- Confiança C inclui patches exatos temporalmente ordenados com menor especificidade, incluindo adições e remoções.
- Similaridade ou igualdade de patch é mecanismo de recuperação, não prova de cópia.

## O que está planejado

1. Para estimar uma taxa, reconstruir o conteúdo de cada linhagem no instante de cada patch e verificar se o contexto pré-alteração ainda era aplicável.
2. Ampliar o universo histórico além dos 53 repositórios completos para elevar a oportunidade de observar adoções.
3. Incorporar proveniência explícita, relações de fork e commits/objetos compartilhados quando disponíveis.
4. Reexecutar sensibilidades com assinaturas por tokens e estrutura apenas como cenários de recuperação; resultados similares permanecerão nível C sem evidência histórica independente.

## O que permanece incerto

- Se a remoção posterior foi influenciada pela anterior, decidida independentemente ou causada por uma fonte comum não observada.
- A cobertura de adoções fora da amostra e em repositórios indisponíveis.
- A aplicabilidade do patch nas linhagens que não o adotaram.
- A completude dos históricos e a confiabilidade causal dos timestamps.

## Resultado que pode constar no artigo

Na amostra exploratória condicionada, a busca conservadora encontrou somente uma relação inter-repositórios de patch exato, classificada como candidato de confiança C. Por ser uma remoção de baixa especificidade, ela não sustenta alegação de propagação. Não foi possível estimar taxa de propagação porque o denominador de linhagens com contexto elegível não pôde ser estabelecido.

## Artefatos finais

- assinaturas: `AnaliseGitSkills/outputs/rq2/patch_signatures_v1/`;
- candidatos após colapso por repositório: `AnaliseGitSkills/outputs/rq2/adoption_candidates_v3/`;
- relações classificadas: `AnaliseGitSkills/outputs/rq2/genealogical_relations_v4/`;
- síntese: `AnaliseGitSkills/outputs/rq2/propagation_results_v4/`;
- scripts: `AnaliseGitSkills/scripts/17_build_patch_signatures.py` a `20_summarize_rq2_propagation.py`.

As saídas anteriores a `adoption_candidates_v3`, `genealogical_relations_v4` e `propagation_results_v4` estão supersedidas e não devem ser usadas.
