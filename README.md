# Backend do Stumble Pool 0.56

Backend de referência em FastAPI para testar a entrada da versão 0.56 no lobby. Ele implementa as rotas informadas, login de convidado, perfil persistente, lobby, servidores, torneios, eventos e respostas compatíveis em JSON.

## Arquivos

- `main.py` — aplicação FastAPI.
- `requirements.txt` — dependências Python.
- `data/users.json` — criado automaticamente na primeira execução para manter os perfis.

## Execução local

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000







