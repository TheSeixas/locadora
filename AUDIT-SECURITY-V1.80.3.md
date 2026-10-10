# Auditoria pré-deploy — Locadora Fênix V1.80.3

Data: 2026-10-09
Escopo: revisão estática do código, revisão de fluxo de autenticação/autorização, testes de regressão e teste HTTP local. Não equivale a um pentest externo nem certifica conformidade legal.

## Correções nesta versão

- Migração das contas de demonstração executa uma única vez. Antes, a remoção por nome ocorria em todo boot e poderia apagar uma conta real com nome coincidente.
- Em produção, o processo falha fechado se não houver ADMIN e as variáveis `BOOTSTRAP_ADMIN_USERNAME`/`BOOTSTRAP_ADMIN_PASSWORD` estiverem ausentes. Isso ajuda o Render a rejeitar o deploy e manter a versão anterior em vez de publicar uma aplicação sem administrador.
- Mutations verificam `Origin` quando presente.
- Endpoints que leem JSON exigem `Content-Type: application/json` e preservam o limite de tamanho do corpo.
- Chave de rate-limit de login separada por IP encaminhado pelo proxy e nome de usuário; IP de registro usa o endereço encaminhado quando válido.
- SQLite usa timeout e `busy_timeout` para reduzir falhas transitórias sob concorrência.
- `render.yaml` preserva a identidade `bdk-locadora` do Blueprint anterior e usa `data/locadora.sqlite3` no plano Free, sem afirmar persistência.

## Testes executados

- 56/56 testes unitários: PASS.
- `node --check public/app.js`: PASS.
- `python scripts/typecheck.py`: PASS.
- `python scripts/visual_smoke.py`: PASS.
- `python scripts/build.py`: PASS.
- `python scripts/smoke.py`: PASS, incluindo autenticação, CRUD do catálogo, criação/edição de usuários, controle de perfil, cadastro público, proteção contra payload não JSON e logout.
- O teste de navegador Chromium com API simulada passou na V1.80.2; o frontend não mudou na V1.80.3.

## Riscos e limitações restantes

1. **Render Free + SQLite local é efêmero.** Dados podem ser perdidos em deploy, restart ou spin-down. Antes de publicar, confirmar se os dados online são descartáveis ou planejar migração/backup.
2. Sessões e contadores de rate-limit são mantidos em memória e reiniciam junto com o processo.
3. A aplicação usa `http.server` da biblioteca padrão e SQLite; adequada para MVP/uso de baixa escala, não uma arquitetura endurecida para tráfego elevado.
4. Senhas usam PBKDF2-HMAC-SHA256 com 180.000 iterações e salt aleatório. É melhor que texto puro, mas a política pode ser revisada contra as recomendações atuais da OWASP.
5. Cadastro coleta idade para filtragem. Se houver usuários reais, avaliar minimização de dados e requisitos legais aplicáveis, especialmente para menores.
6. Não há pagamentos, e-mail, recuperação de senha por e-mail nem fluxo completo de aluguel/devolução.

## Checklist obrigatório antes do deploy

- Configurar `BOOTSTRAP_ADMIN_USERNAME` e `BOOTSTRAP_ADMIN_PASSWORD` como variáveis secretas no Render antes de publicar.
- Confirmar que o usuário administrativo configurado consegue entrar após o deploy.
- Confirmar se os registros atuais no SQLite podem ser descartados; no plano Free, o deploy pode recriar o banco.
- Após o deploy, verificar `/health`, login ADMIN, cadastro público CUSTOMER, criação de OPERACIONAL e bloqueios de autorização.
