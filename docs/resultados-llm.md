# Avaliação da extração por LLM

- Modelo solicitado: `claude-sonnet-5-5`; modelos registrados nas respostas: ['claude-haiku-5-5', 'claude-sonnet-5-5']
- Acesso: 2.1.332 (Claude Code), modo não interativo, prompt de sistema próprio, sem ferramentas
- Datas (UTC): 2026-11-27T02:21:13+00:00 a 2026-11-27T03:59:49+00:00
- Repetições por contrato: 3; hash do prompt: `8d1339fc8950a638…`
- Respostas com JSON inválido: 0 de 36
- Tempo por contrato (mediana): 8.2 s

| Conjunto | Obrigações | Revocação | Precisão | Responsável | Prazo |
|---|---|---|---|---|---|
| desenvolvimento | 28 | 100% (100–100%) | 98% (97–100%) | 100% (100–100%) | 100% (100–100%) |
| validação | 14 | 100% (100–100%) | 100% (100–100%) | 100% (100–100%) | 100% (100–100%) |
| robustez (injeção) | 4 | 100% (100–100%) | 100% (100–100%) | 100% (100–100%) | 100% (100–100%) |
| casos aplicados | 21 | 100% (100–100%) | 98% (95–100%) | 100% (100–100%) | 100% (100–100%) |

Valores: média das repetições (mínimo–máximo).

Erros por repetição:

- nenhum
