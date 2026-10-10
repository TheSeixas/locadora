# Locadora Fênix — V1.80.3

## Auditoria pré-deploy

- Corrigido: migração das contas de demonstração é executada apenas uma vez; contas criadas depois não são apagadas em reinicializações.
- Reforçado: endpoints JSON rejeitam Content-Type que não seja application/json.
- Reforçado: operações mutáveis validam o cabeçalho Origin quando presente.
- Seguro por padrão: em produção (`HOST=0.0.0.0`), o processo não inicia se não existir ADMIN e as variáveis de bootstrap estiverem ausentes.
- Ajustado: limite de login usa IP encaminhado pelo proxy quando disponível e separa a chave por nome de usuário para reduzir bloqueio global de clientes atrás do proxy.
- Melhorado: timeout/busy_timeout do SQLite para reduzir erros transitórios em acessos concorrentes.
- Mantido: gestão de clientes/operadores, cadastro público CUSTOMER, filtros por idade, administração de catálogo e identidade do serviço no render.yaml.

## Validação

Executar: `python -m unittest discover -s tests -v`, `node --check public/app.js`, `python scripts/typecheck.py`, `python scripts/visual_smoke.py`, `python scripts/build.py` e `python scripts/smoke.py`.

## Limitações operacionais

- Sessões e contadores de limite permanecem em memória e reiniciam com o processo.
- SQLite em armazenamento efêmero do Render Free pode perder dados em reinício, spin-down ou deploy.
- Configure BOOTSTRAP_ADMIN_USERNAME e BOOTSTRAP_ADMIN_PASSWORD no painel do Render antes de publicar.
