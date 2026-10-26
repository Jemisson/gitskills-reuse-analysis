# Emenda metodológica — validação exclusivamente automatizada

**Versão:** 1.0  
**Data de congelamento:** 26 de outubro de 2026  
**Estado:** CONGELADO para a continuidade desta pesquisa.

## Decisão e alcance

Por restrição de tempo, RQ2 e RQ3 não terão anotação humana independente, dupla codificação, adjudicação ou conjunto-ouro. Toda extração, classificação, auditoria interna e análise será realizada pelo pipeline versionado neste repositório e pelas interações registradas neste ambiente.

Esta emenda substitui disposições incompatíveis em versões anteriores do protocolo, planos de RQ2/RQ3, codebook, README e matriz de evidências. Resultados científicos já existentes não são alterados.

## Consequência inferencial

As categorias produzidas para mudanças, regiões Markdown, comandos, acesso externo, executáveis, genealogia e propagação são **classificações operacionais automatizadas**. Elas não possuem estimativa independente de validade semântica. Portanto:

- análises RQ2/RQ3 serão rotuladas como exploratórias;
- não serão reportados κ, concordância entre avaliadores, precisão, recall ou F1 contra padrão-ouro;
- exemplos inspecionados durante o desenvolvimento não serão chamados de validação humana;
- similaridade continuará sendo apenas mecanismo de candidatura, nunca prova de ancestralidade;
- direção genealógica continuará exigindo evidência Git/proveniência; na ausência dela, permanecerá indeterminada;
- nenhuma associação será descrita como causal.

## Protocolo substituto de confiabilidade

Cada classificador deverá fornecer:

1. regra e versão que produziram o rótulo;
2. evidência observável — texto, offsets, path, commit, blobs e/ou status Git;
3. categoria `incerto` ou falha explícita quando a regra não puder decidir;
4. fixtures positivas, negativas, limítrofes e de erro;
5. testes unitários, integração e invariantes de schema;
6. reexecução determinística com checksums;
7. sensibilidades com definições estrita e ampla;
8. relatório da proporção de casos incertos, falhas e mudanças de rótulo entre cenários.

Revisões de regras após contato com resultados exigem nova versão, justificativa e reexecução separada. Resultados anteriores não serão sobrescritos.

## Afirmações permitidas

- “A regra automatizada X classificou N eventos como categoria Y.”
- “O resultado permaneceu/mudou nos cenários automatizados especificados.”
- “O diff contém o padrão observável Z.”
- “A relação possui nível de evidência A/B/C/D segundo regras versionadas.”

## Afirmações não sustentadas

- “A classificação foi validada por especialistas/humanos.”
- “O classificador possui acurácia, precisão ou recall conhecidos.”
- “A categoria automatizada representa necessariamente mudança comportamental real.”
- “Similaridade ou anterioridade observada prova origem, autoria ou transmissão.”
- “Ausência de detecção significa ausência da mudança.”

## Critérios de conclusão revisados

O bloco automatizado de cada RQ estará tecnicamente concluído quando código, configuração, fixtures, entradas, saídas, checksums e sensibilidades estiverem ligados na matriz de evidências. A conclusão científica deverá declarar a ausência de validação humana independente como ameaça à validade de construto e limitar as conclusões às definições operacionais executadas.

## Controle da decisão

Esta versão é a referência metodológica para os próximos passos. Mudanças futuras deverão criar uma nova versão desta emenda e um novo manifesto de congelamento; não poderão editar silenciosamente as regras usadas em resultados já gerados.
