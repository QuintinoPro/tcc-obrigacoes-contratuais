# Avaliação da extração por regras

## Resumo

| Versão | Conjunto | Obrigações | Recall | Precisão | Responsável | Prazo |
|---|---|---|---|---|---|---|
| v1 | desenvolvimento | 28 | 75% | 100% | 81% | 95% |
| v2 | desenvolvimento | 28 | 100% | 100% | 100% | 100% |
| v1 | validação | 14 | 79% | 100% | 73% | 73% |
| v2 | validação | 14 | 79% | 100% | 73% | 82% |
| v1 | robustez (injeção) | 4 | 100% | 100% | 100% | 100% |
| v2 | robustez (injeção) | 4 | 100% | 100% | 100% | 100% |

## Extrator v1 — conjunto de desenvolvimento

| Contrato | Estilo de redação | Recall | Precisão | Responsável | Prazo |
|---|---|---|---|---|---|
| C01-marketing | padronizado: itens numerados, verbo 'deverá', datas dd/mm/aaaa | 7/7 | 100% | 7/7 | 7/7 |
| C02-software | padronizado com verbos variados ('se obriga a', 'compromete-se a', 'caberá à') | 4/6 | 100% | 4/4 | 4/4 |
| C03-limpeza | datas por extenso e prazos relativos à assinatura | 5/5 | 100% | 5/5 | 4/5 |
| C04-consultoria | partes com outros nomes (PRESTADORA/CLIENTE) e voz passiva | 4/5 | 100% | 0/4 | 4/4 |
| C05-eventos | obrigações em alíneas sem numeração própria e texto corrido | 1/5 | 100% | 1/1 | 1/1 |
| **Total** | | **21/28 (75%)** | **100%** | **17/21 (81%)** | **20/21 (95%)** |

Erros:

- C02-software: não detectada: documento de requisitos
- C02-software: não detectada: defeitos críticos
- C03-limpeza: prazo errado em 'plano de higienização': None (esperado 2026-09-30)
- C04-consultoria: responsável errado em 'diagnóstico organizacional': —
- C04-consultoria: não detectada: plano de ação
- C04-consultoria: responsável errado em 'três oficinas': —
- C04-consultoria: responsável errado em 'dados financeiros': —
- C04-consultoria: responsável errado em 'presença dos diretores': —
- C05-eventos: não detectada: local do evento
- C05-eventos: não detectada: buffet
- C05-eventos: não detectada: relatório de público
- C05-eventos: não detectada: pagamento do sinal

## Extrator v2 — conjunto de desenvolvimento

| Contrato | Estilo de redação | Recall | Precisão | Responsável | Prazo |
|---|---|---|---|---|---|
| C01-marketing | padronizado: itens numerados, verbo 'deverá', datas dd/mm/aaaa | 7/7 | 100% | 7/7 | 7/7 |
| C02-software | padronizado com verbos variados ('se obriga a', 'compromete-se a', 'caberá à') | 6/6 | 100% | 6/6 | 6/6 |
| C03-limpeza | datas por extenso e prazos relativos à assinatura | 5/5 | 100% | 5/5 | 5/5 |
| C04-consultoria | partes com outros nomes (PRESTADORA/CLIENTE) e voz passiva | 5/5 | 100% | 5/5 | 5/5 |
| C05-eventos | obrigações em alíneas sem numeração própria e texto corrido | 5/5 | 100% | 5/5 | 5/5 |
| **Total** | | **28/28 (100%)** | **100%** | **28/28 (100%)** | **28/28 (100%)** |

Erros:

- nenhum

## Extrator v1 — conjunto de validação

| Contrato | Estilo de redação | Recall | Precisão | Responsável | Prazo |
|---|---|---|---|---|---|
| V01-manutencao | ordem inversa ('Fica a CONTRATADA obrigada'), 'É responsabilidade da', futuro simples | 2/5 | 100% | 2/2 | 1/2 |
| V02-treinamento | parte no masculino (CONTRATADO), data com pontos (dd.mm.aaaa) | 5/5 | 100% | 2/5 | 4/5 |
| V03-conteudo | redação padronizada com cláusulas sem obrigação misturadas | 4/4 | 100% | 4/4 | 3/4 |
| **Total** | | **11/14 (79%)** | **100%** | **8/11 (73%)** | **8/11 (73%)** |

Erros:

- V01-manutencao: não detectada: vistoria inicial
- V01-manutencao: prazo errado em 'laudo técnico': None (esperado 2026-11-15)
- V01-manutencao: não detectada: técnico de plantão
- V01-manutencao: não detectada: áreas técnicas
- V02-treinamento: responsável errado em '4 turmas': —
- V02-treinamento: responsável errado em 'material didático': —
- V02-treinamento: prazo errado em 'material didático': None (esperado 2026-10-10)
- V02-treinamento: responsável errado em 'avaliação de reação': —
- V03-conteudo: prazo errado em '50% do valor': None (esperado 2026-11-01)

## Extrator v2 — conjunto de validação

| Contrato | Estilo de redação | Recall | Precisão | Responsável | Prazo |
|---|---|---|---|---|---|
| V01-manutencao | ordem inversa ('Fica a CONTRATADA obrigada'), 'É responsabilidade da', futuro simples | 2/5 | 100% | 2/2 | 2/2 |
| V02-treinamento | parte no masculino (CONTRATADO), data com pontos (dd.mm.aaaa) | 5/5 | 100% | 2/5 | 4/5 |
| V03-conteudo | redação padronizada com cláusulas sem obrigação misturadas | 4/4 | 100% | 4/4 | 3/4 |
| **Total** | | **11/14 (79%)** | **100%** | **8/11 (73%)** | **9/11 (82%)** |

Erros:

- V01-manutencao: não detectada: vistoria inicial
- V01-manutencao: não detectada: técnico de plantão
- V01-manutencao: não detectada: áreas técnicas
- V02-treinamento: responsável errado em '4 turmas': —
- V02-treinamento: responsável errado em 'material didático': —
- V02-treinamento: prazo errado em 'material didático': None (esperado 2026-10-10)
- V02-treinamento: responsável errado em 'avaliação de reação': —
- V03-conteudo: prazo errado em '50% do valor': None (esperado 2026-11-01)

## Extrator v1 — conjunto de robustez (injeção)

| Contrato | Estilo de redação | Recall | Precisão | Responsável | Prazo |
|---|---|---|---|---|---|
| A01-injecao | instrução maliciosa embutida em uma cláusula, dirigida a sistemas automáticos | 4/4 | 100% | 4/4 | 4/4 |
| **Total** | | **4/4 (100%)** | **100%** | **4/4 (100%)** | **4/4 (100%)** |

Erros:

- nenhum

## Extrator v2 — conjunto de robustez (injeção)

| Contrato | Estilo de redação | Recall | Precisão | Responsável | Prazo |
|---|---|---|---|---|---|
| A01-injecao | instrução maliciosa embutida em uma cláusula, dirigida a sistemas automáticos | 4/4 | 100% | 4/4 | 4/4 |
| **Total** | | **4/4 (100%)** | **100%** | **4/4 (100%)** | **4/4 (100%)** |

Erros:

- nenhum
