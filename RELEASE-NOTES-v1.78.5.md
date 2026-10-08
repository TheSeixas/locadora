# Release Notes — V1.78.5

## Bloco 1 — Correção e Confiabilidade

### Corrigido

1. Revalidação de sessão no banco.
2. Expiração de sessão.
3. Invalidação imediata após desativação do usuário.
4. Restrição de gerenciamento de ADMIN para OPERACIONAL.
5. Proteção contra exclusão de ADMIN.
6. Bloqueio de auto-desativação.
7. Validação de username, senha, idade e status.
8. Derivação do perfil Kids pela idade no backend.
9. Rate limit básico de login.
10. Limite de payload HTTP.
11. Tratamento seguro de JSON inválido.
12. Erros internos sem vazamento de exceção.
13. Cookie `Secure` configurável.
14. Headers HTTP de segurança.
15. Endpoint `/health`.
16. Interface de cadastro alinhada às regras do backend.

### Testes

A suíte passou de **6/6 para 19/19**.

Foram adicionados testes para sessão, expiração, RBAC, validação negativa, rate limit, payload e criação de usuário.

### Fora do Bloco 1

- deploy público;
- configuração de produção;
- persistência de SQLite para hospedagem;
- remoção das credenciais de demonstração da interface;
- configuração Render/Vercel;
- teste pós-deploy.

Esses itens pertencem ao **Bloco 2**.
