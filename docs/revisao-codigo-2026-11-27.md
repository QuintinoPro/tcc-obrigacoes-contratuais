# Revisão de código (skill code-review) · 27/11/2026

Escopo: app/, contracts/, scripts/, tests/ e app/static/ (1.634 linhas), revisados por inteiro (diff contra árvore vazia).

| Categoria | Resultado |
|---|---|
| Segredos no código | nenhum |
| eval / exec / shell | nenhum |
| Blocos except | 3 amplos, todos com tratamento: leitura de PDF (agora registra a causa no log), fallback do LLM (documentado) e conversão numérica |
| TODO / FIXME | nenhum |
| Duplicação | **corrigido**: extractor_v1.py era cópia do módulo inteiro (com prompt e chamada de LLM antigos); ficou só com as regras da v1 e reusa normalize() |
| Impacto | scripts/avaliar_extracao.py passou a usar extractor.normalize; testes e resultados inalterados |
| Desempenho (anotado) | chain.find_evidence percorre todos os eventos StatusChanged; aceitável no protótipo, indexar o hash da evidência no evento em produção |
| Interface (skill web-design-guidelines) | **corrigido**: upload e evidência acessíveis por teclado, rótulos acessíveis, aria-live, aria-pressed, foco visível, estado de carregamento, reduced-motion |
