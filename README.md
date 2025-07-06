# Teste de Especialista Blockchain

Este projeto implementa uma API REST em Python para interagir com a blockchain Ethereum, seguindo as [instruções do desafio](docs/teste-dev-blockchain.pdf).

## Author

Kaique Nunes <anarkrypto@gmail.com>

## Install

1. Estaremos utilizando a ferramenta `uv` para facilitar o desenvolvimento.
   Guia de instalação do `uv`: https://docs.astral.sh/uv/getting-started/installation/

2. Instale a versão do Python utilizada no projeto:

```bash
uv python install 3.10
uv python pin 3.10
```

3. Instale as dependências:

```bash
uv sync
```

## Running

```bash
uv run fastapi dev app/main.py
```

## Test

pytest -s -vv

## Extensions for VSCode (Development only)

- charliermarsh.ruff
- matangover.mypy
