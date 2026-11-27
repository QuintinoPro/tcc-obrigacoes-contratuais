# Obrigações contratuais com IA, blockchain e smart contracts

Protótipo e materiais de avaliação da monografia **"Sistema inteligente baseado em Inteligência Artificial e blockchain para gestão e rastreabilidade de obrigações contratuais"**, de Lucas Quintino Gomes Araújo, apresentada ao curso de Sistemas de Informação da Universidade Veiga de Almeida (UVA), 2026, sob orientação do Prof. Claudio José Marques de Souza.

Demonstração: https://tcc.agenciastocks.com (rede EVM local em memória; os dados são apagados quando a aplicação reinicia).

## O que é

Um contrato em PDF é processado. Um extrator (regras ou LLM) sugere as obrigações, com responsável, entregável, prazo e evidência esperada. Uma pessoa revisa e confirma. Cada obrigação segue uma máquina de estados validada por um smart contract Solidity genérico. Documentos e dados ficam fora da cadeia; na cadeia ficam só hashes, estados e eventos. Se alguém alterar o banco de dados por fora do sistema, a aplicação detecta comparando com o hash registrado on-chain.

## Executar

Requer [uv](https://docs.astral.sh/uv/). O primeiro start cria o ambiente e baixa o compilador Solidity.

```bash
./run.sh                 # http://localhost:8000
.venv/bin/pytest -s      # cenários C1–C12
```

Ou com Docker: `docker build -t tcc . && docker run -p 8000:8000 tcc` (a construção da imagem executa os testes).

## Reproduzir a avaliação

```bash
.venv/bin/python -m scripts.avaliar_extracao              # extrator por regras v1 e v2
.venv/bin/python -m scripts.avaliar_llm --repeticoes 3    # LLM via Claude Code CLI (CLAUDE_BIN=caminho)
```

- `samples/corpus.py`: os 8 contratos fictícios (5 de desenvolvimento, 3 de validação), o gabarito manual, 3 casos aplicados (patrocínio de evento, produção audiovisual e tráfego pago) e 1 contrato com injeção de prompt para o teste de robustez.
- `docs/resultados-extracao.md` e `docs/resultados-llm.md`: resultados usados na monografia.
- `docs/llm-runs/`: resposta bruta de cada chamada ao LLM, com modelo, data, versão da ferramenta e hash do prompt.

Resultado no conjunto de validação (14 obrigações):

| Extrator | Revocação | Precisão |
|---|---|---|
| Regras v1 | 79% (11 de 14) | 100% |
| Regras v2 | 79% (11 de 14) | 100% |
| LLM (claude-sonnet-5-5, 3 repetições) | 100% (14 de 14) | 100% |

Com 14 obrigações, a diferença entre regras v2 e LLM na validação não é significativa (McNemar exato, p = 0,25); nas 35 obrigações nunca vistas pela v1, é (p = 0,002). No contrato com injeção de prompt, o LLM ignorou a instrução nas 3 repetições. Nos 3 casos aplicados (21 obrigações), regras v2 e LLM acertaram todas.

## Estrutura

```
contracts/ObligationRegistry.sol   smart contract (hashes, estados, eventos)
app/chain.py                       adaptador blockchain (web3.py; CHAIN_RPC_URL para rede externa)
app/extractor.py                   extração: regras v2, LLM opcional (ANTHROPIC_API_KEY) e normalização
app/extractor_v1.py                primeira versão do extrator, mantida para comparação
app/main.py                        API FastAPI + SQLite + trilha de auditoria
app/static/                        interface web
samples/                           contrato de exemplo, corpus e gabarito
scripts/                           avaliação da extração
tests/test_cenarios.py             cenários C1–C12
```

Todos os contratos do repositório são fictícios.
