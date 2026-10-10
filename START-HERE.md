# Locadora Fênix — início rápido

No Windows CMD, defina as variáveis de administrador conforme o README e execute `python server.py`. Depois entre usando exatamente o usuário e a senha configurados nas variáveis. No exemplo, o usuário é `fenixadmin`, não `admin`. A senha precisa ter pelo menos 12 caracteres. Não há contas de demonstração nem senha administrativa embutida. Em produção (`HOST=0.0.0.0`), o servidor não inicia sem um ADMIN existente ou sem as variáveis de bootstrap configuradas.

Na gestão de usuários, ADMIN pode criar clientes e operadores e editar contas não administrativas. OPERATIONAL pode gerenciar dados básicos de clientes, mas não pode promover contas nem redefinir senhas. O cadastro público sempre cria cliente.
