# Deploy — BDK Locadora V1.79.1

## Render

Tipo: Web Service
Runtime: Python
Build: `python3 scripts/build.py`
Start: `python3 server.py`
Health: `/health`

### Variáveis

- `HOST=0.0.0.0`
- `COOKIE_SECURE=1`
- `LOCADORA_DB_PATH=/var/data/locadora.sqlite3`

### Persistência

O Blueprint está preparado para usar `/var/data` como local do SQLite. Para persistência entre deploys/restarts, adicionar um Persistent Disk montado em `/var/data`.

Para uma revisão temporária, o serviço pode rodar sem disco persistente; o SQLite será recriado/seedado quando a instância for recriada.

### Credenciais de laboratório

- `admin / admin123`
- `operador / op123`
- `crianca / kids123`

Não usar essas credenciais em um ambiente com usuários reais.
