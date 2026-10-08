# BDK Locadora — V1.79.0 / Block 1 Hardening

Sistema full-stack em Python com SQLite. Esta versão fecha o **Bloco 1 — Correção e Confiabilidade** da auditoria.

## Iniciar localmente

```text
python server.py
```

ou:

```text
run.bat
```

Abra `http://127.0.0.1:3000/`.

## Contas de demonstração

- `admin / admin123`
- `operador / op123`
- `crianca / kids123`
- `inativo / inactive123`

Essas credenciais são de laboratório e serão tratadas separadamente na preparação de produção do **Bloco 2**.

## Regras de cadastro

- Usuário: 3–30 caracteres, usando letras, números, `.`, `_` ou `-`.
- Senha: 8–128 caracteres.
- Idade: inteiro entre 0 e 120.
- Perfil infantil é derivado automaticamente da idade (`<13`).
- E-mail não faz parte desta aplicação.

## O que foi fechado no Bloco 1

- Sessões revalidam o usuário no banco a cada requisição protegida.
- Sessões expiram por TTL.
- Usuário desativado perde a sessão ativa.
- OPERACIONAL não pode administrar ADMIN pelo backend.
- ADMIN não pode excluir ADMIN.
- Usuário não pode desativar a própria conta.
- Validação de entrada ocorre no backend.
- Login possui rate limit básico.
- Payload HTTP possui limite de tamanho.
- Erros internos não expõem detalhes Python ao cliente.
- Cookies suportam `Secure` via configuração de ambiente.
- Headers HTTP de segurança foram adicionados.
- Endpoint `/health` foi adicionado.
- Suíte passou de 6 para 19 testes.

## Verificação

- 19/19 testes unitários: PASS
- Typecheck: PASS
- Build: PASS
- Visual smoke: PASS
- HTTP local: PASS

O deploy e a validação de produção ficam para o **Bloco 2**.


## Gestão administrativa do catálogo — V1.79.0

O perfil ADMIN possui CRUD de filmes com validação no backend. OPERACIONAL e CUSTOMER não podem alterar o catálogo.
