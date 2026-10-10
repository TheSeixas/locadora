# Deploy no Render — Locadora Fênix

- Build Command: `python3 scripts/build.py`
- Start Command: `python3 server.py`
- Health Check Path: `/health`
- `HOST=0.0.0.0`
- `COOKIE_SECURE=1`
- `BOOTSTRAP_ADMIN_USERNAME`: usuário inicial escolhido por você
- `BOOTSTRAP_ADMIN_PASSWORD`: senha exclusiva com no mínimo 12 caracteres
- `LOCADORA_DB_PATH`: caminho conforme o armazenamento. `/var/data/locadora.sqlite3` exige disco persistente montado em `/var/data`.

Antes de publicar: defina as duas variáveis de bootstrap, faça deploy, entre como administrador, teste cadastro público e confirme que cadastro não consegue criar privilégios. Depois de o administrador ser criado, alterar variáveis de bootstrap não redefine a senha existente.

Atenção: no Render Free o sistema de arquivos é efêmero. Não use para dados de clientes que precisam persistir.


## Permissões da V1.80.3

- ADMIN pode criar e editar contas de cliente e operador, alterar o perfil dessas contas e redefinir suas senhas. Contas ADMIN não podem ser alteradas ou excluídas pela gestão comum de usuários.
- OPERATIONAL pode criar/editar clientes e alterar seu status; não pode promover perfis, redefinir senhas ou excluir contas.
- O cadastro público sempre cria uma conta CUSTOMER. A autorização é validada no backend.
