# Locadora Fênix — versão candidata 1.80.3

Aplicação web de catálogo de filmes com contas, regras de visibilidade por idade e administração do catálogo.

## Executar localmente (Windows CMD)

1. Instale Python 3.10 ou superior.
2. Defina um administrador inicial no terminal antes de iniciar:

```bat
set BOOTSTRAP_ADMIN_USERNAME=fenixadmin
set BOOTSTRAP_ADMIN_PASSWORD=TroqueEstaSenhaPorUmaForte123!
set HOST=127.0.0.1
set COOKIE_SECURE=0
python server.py
```

Use uma senha exclusiva, com pelo menos 12 caracteres. O administrador só é criado se ainda não houver uma conta ADMIN. As variáveis não são gravadas no repositório. Em outro terminal, abra http://127.0.0.1:3000/.

## Deploy no Render

Configure `BOOTSTRAP_ADMIN_USERNAME` e `BOOTSTRAP_ADMIN_PASSWORD` em Environment antes do deploy. Defina uma senha forte e exclusiva. Configure `HOST=0.0.0.0`, `COOKIE_SECURE=1` e `LOCADORA_DB_PATH` conforme o armazenamento escolhido. Não publique enquanto as variáveis de bootstrap não estiverem configuradas e o login administrativo não tiver sido testado. Em produção, o servidor agora se recusa a iniciar sem um ADMIN existente ou sem as variáveis de bootstrap.

**Persistência:** o disco local do plano Free do Render é efêmero. Alterações no catálogo e usuários podem ser perdidas após reinício, spin-down ou novo deploy. Para dados duráveis, use armazenamento persistente ou banco gerenciado.

## Cadastro e permissões

- Cadastro público solicita usuário, senha e idade; não solicita e-mail.
- O cadastro público sempre cria `CUSTOMER`, ignora tentativas de escolher `ADMIN`/`OPERATIONAL` e ativa a conta.
- Na gestão interna, ADMIN pode criar clientes e operadores, editar contas não administrativas, alterar o perfil entre cliente/operador e redefinir senhas dessas contas.
- OPERATIONAL pode cadastrar e editar clientes e alterar seu status; não pode promover perfis, redefinir senhas, excluir usuários nem administrar contas administrativas.
- Usuário: 3–30 caracteres alfanuméricos, ponto, hífen ou sublinhado.
- Senha: 8–128 caracteres; senha do primeiro administrador: mínimo de 12 caracteres no bootstrap.
- Idade: informada em anos completos; o servidor valida o valor e calcula o perfil infantil. A interface não expõe a faixa técnica de validação na mensagem de erro.
- Cadastro público: limite de 5 tentativas por IP por hora (em memória; reinícios limpam o contador).
- Não há pagamentos, e-mail nem fluxo completo de aluguel nesta versão.

## Testes

```bat
node --check public/app.js
python -m unittest discover -s tests -v
python scripts/typecheck.py
python scripts/visual_smoke.py
python scripts/build.py
python scripts/smoke.py
```

A versão 1.80.3 é candidata para validação local; a versão congelada 1.79.1 não deve ser sobrescrita.

Após iniciar o servidor pela primeira vez, entre com o usuário definido em `BOOTSTRAP_ADMIN_USERNAME` (no exemplo, `fenixadmin`) e exatamente a senha definida em `BOOTSTRAP_ADMIN_PASSWORD`. Não use `admin` nem as credenciais antigas de demonstração. Se já existir uma conta ADMIN no banco, o bootstrap não troca a senha existente.
