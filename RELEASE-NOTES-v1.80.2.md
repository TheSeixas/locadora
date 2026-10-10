# Locadora Fênix — V1.80.2 (candidata para teste local)

## Gestão de usuários
- ADMIN agora pode criar contas de cliente e operador pelo formulário de gestão.
- ADMIN pode editar contas não administrativas: usuário, idade, status, perfil cliente/operador e, opcionalmente, redefinir a senha.
- OPERATIONAL pode cadastrar e editar dados básicos de clientes e ativar/desativar clientes.
- OPERATIONAL não pode criar/promover operadores, redefinir senhas, excluir usuários ou administrar contas ADMIN.
- Contas ADMIN ficam protegidas contra alteração/exclusão pela tela comum de usuários, reduzindo o risco de bloqueio administrativo.
- A autorização de perfil e as alterações são validadas no servidor, não apenas pela interface.

## Formulários
- Layout dos campos de senha, perfil e status ajustado para os estados de criação/edição.
- Mensagem de idade alterada para “Informe uma idade válida em anos completos.”, sem expor ao usuário a faixa técnica 0–120.
- Formulário de usuário reutilizado para criação e edição.
- Campo de senha informa “Nova senha (opcional)” na edição administrativa.
- Campos de perfil e redefinição de senha aparecem conforme o papel do operador autenticado.
- Rótulos dos perfis apresentados em português.

## Verificações executadas
- `node --check public/app.js`: aprovado.
- `python -m unittest discover -s tests -v`: 52 testes aprovados (43 backend + 9 contrato frontend).
- `python scripts/typecheck.py`: aprovado.
- `python scripts/visual_smoke.py`: aprovado.
- `python scripts/build.py`: aprovado.
- `python scripts/smoke.py`: aprovado, incluindo criação de operador pelo ADMIN, edição/promoção de usuário, bloqueio de elevação de privilégio pelo OPERATIONAL e criação de cliente pelo OPERATIONAL.
- Teste de interface em Chromium headless com API simulada: cadastro público, login administrativo, criação de operador, edição de usuário e alteração de perfil passaram sem erros JavaScript.

## Limites
- Esta versão é candidata para validação local e não foi publicada no Render.
- O Render Free continua sem persistência durável para o SQLite local.
- Não foram adicionados pagamentos, e-mail ou fluxo completo de aluguel.
