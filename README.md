# SGTracer FastAPI — Tournament API

API feita com FastAPI para jogadores e torneios do SGTracer.

Recursos:

- Cadastro de jogadores;
- PlayerID entre 1000 e 9999;
- Nome automático no formato `.gg/sgtracer<sup>1299`;
- Login;
- Criação de torneios;
- Inscrição em torneios;
- Resultados;
- Ranking;
- Banco de dados SQLite;
- Documentação automática em `/docs`.

## Rodar localmente

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload










